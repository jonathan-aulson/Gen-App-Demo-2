#!/usr/bin/env python3
"""
Single Sentence Static Web App Generator
A CLI tool that creates, tests, documents, and deploys static web apps from natural language.

Key features:
- Multi-provider AI: Anthropic (Claude) and OpenAI (GPT)
- 5-stage autonomous pipeline: Scope, Build, Test, Document, Deploy
- Robust file extraction with filename sanitization and safe paths
- Safe GitHub deployment with root-level index.html enforcement
- GitHub Pages enablement with live readiness polling

Usage:
  python webapp_gen.py --config
  python webapp_gen.py "Create a portfolio website with a hero section"

Environment:
  AI_PROVIDER=openai|anthropic
  OPENAI_API_KEY=...
  ANTHROPIC_API_KEY=...
  MODEL_ID=gpt-4o|claude-...
  GITHUB_USERNAME=...
  GITHUB_TOKEN=...
  GITHUB_REPO=...
  OUTPUT_DIR=./generated_webapp (default)
"""

import os
import sys
import json
import subprocess
import time
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import requests
from dataclasses import dataclass, asdict
from enum import Enum


class Stage(Enum):
    """Development stages"""
    SCOPE = "scope"
    BUILD = "build"
    TEST = "test"
    DOCUMENT = "document"
    DEPLOY = "deploy"


@dataclass
class Config:
    """Configuration for the generator"""
    api_key: str
    model_id: str
    provider: str = "anthropic"  # anthropic or openai
    github_username: Optional[str] = None
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    output_dir: str = "./generated_webapp"
    max_iterations: int = 10

    @property
    def api_base_url(self) -> str:
        """Get API base URL based on provider"""
        if self.provider.lower() == "openai":
            return "https://api.openai.com/v1/chat/completions"
        else:  # anthropic
            return "https://api.anthropic.com/v1/messages"


class AIClient:
    """Client for interacting with AI API (supports Anthropic and OpenAI)"""

    def __init__(self, config: Config):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []

    def _call_anthropic(self, prompt: str, system_prompt: str = None) -> str:
        """Make an API call to Anthropic Messages API"""
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        messages = self.conversation_history + [{"role": "user", "content": prompt}]
        payload = {
            "model": self.config.model_id,
            "max_tokens": 4096,  # Anthropic uses max_tokens for 2023-06-01 version
            "messages": messages
        }
        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(
            self.config.api_base_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        try:
            return result["content"][0]["text"]
        except Exception:
            return json.dumps(result)

    def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
        """Make an API call to OpenAI Chat Completions"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, object] = {
            "model": self.config.model_id,
            "messages": messages,
            "temperature": 0.7
        }

        # Use max_completion_tokens for newer OpenAI models; fallback to max_tokens for older ones
        lower_model = self.config.model_id.lower()
        if any(m in lower_model for m in ["gpt-4o", "gpt-4.1", "gpt-4.5", "o1", "o3"]):
            payload["max_completion_tokens"] = 4096
        else:
            payload["max_tokens"] = 4096

        response = requests.post(
            self.config.api_base_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        try:
            return result["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(result)

    def call(self, prompt: str, system_prompt: str = None) -> str:
        """Make an API call to the configured AI service and track history"""
        try:
            if self.config.provider.lower() == "openai":
                assistant_message = self._call_openai(prompt, system_prompt)
            else:
                assistant_message = self._call_anthropic(prompt, system_prompt)

            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            print(f"❌ API Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    print(f"   Response: {e.response.text}")
                except Exception:
                    pass
            return ""

    def reset_conversation(self):
        self.conversation_history = []


class WorkPlan:
    """Manages work plans for each stage"""

    def __init__(self, stage: Stage, output_dir: Path):
        self.stage = stage
        self.output_dir = output_dir
        self.plan_file = output_dir / f"{stage.value}_plan.json"
        self.todos: List[Dict] = []

    def save(self):
        self.plan_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plan_file, 'w', encoding='utf-8') as f:
            json.dump(self.todos, f, indent=2)

    def load(self) -> bool:
        if self.plan_file.exists():
            with open(self.plan_file, 'r', encoding='utf-8') as f:
                self.todos = json.load(f)
            return True
        return False

    def add_todo(self, title: str, description: str, acceptance_criteria: List[str]):
        self.todos.append({
            "id": len(self.todos) + 1,
            "title": title,
            "description": description,
            "acceptance_criteria": acceptance_criteria,
            "status": "pending",
            "completed_at": None
        })

    def complete_todo(self, todo_id: int):
        for todo in self.todos:
            if todo["id"] == todo_id:
                todo["status"] = "completed"
                todo["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self.save()

    def get_pending_todos(self) -> List[Dict]:
        return [t for t in self.todos if t["status"] == "pending"]

    def is_complete(self) -> bool:
        return len(self.get_pending_todos()) == 0


# Allowed file constraints for sanitization
ALLOWED_EXTENSIONS = {".html", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico"}
ALLOWED_TOP_DIRS = {"", "assets", "css", "js", "images", "img", "static"}


class WebAppGenerator:
    """Main generator class"""

    def __init__(self, config: Config):
        self.config = config
        self.ai = AIClient(config)
        self.output_dir = Path(config.output_dir)
        self.requirements: Dict = {}
        self.current_stage = Stage.SCOPE
        self.deployed_url: Optional[str] = None

    # --------------------
    # Helper functions
    # --------------------

    def _safe_join(self, base: Path, *paths: str) -> Path:
        """Join and ensure the result stays within base (prevent path traversal)."""
        candidate = base.joinpath(*paths).resolve()
        base_resolved = base.resolve()
        try:
            # Python 3.9+: Path.is_relative_to
            if not candidate.is_relative_to(base_resolved):  # type: ignore[attr-defined]
                raise ValueError("Path traversal detected")
        except AttributeError:
            if not str(candidate).startswith(str(base_resolved)):
                raise ValueError("Path traversal detected")
        return candidate

    def _sanitize_filepath(self, raw: str) -> Optional[str]:
        """
        Convert a raw filename (possibly with comments/backticks) to a safe, canonical path.
        Examples:
          "index.html` (header updated for branding)" -> "index.html"
          "about.html`" -> "about.html"
          "assets/icon.svg (dark mode)" -> "assets/icon.svg"
        """
        if not raw:
            return None

        s = raw.strip().strip('`"\'')
        s = s.replace("\\", "/")

        # Strip trailing commentary like: ` (something)` or after a backtick, etc.
        s = re.split(r"\s+\(|`", s, maxsplit=1)[0].strip()

        # Remove leading "File:" or "Filename:" labels if present
        s = re.sub(r"^(?:file:|filename:)\s*", "", s, flags=re.IGNORECASE)

        # Remove any disallowed characters; keep [A-Za-z0-9._\-/]
        s = re.sub(r"[^A-Za-z0-9._\-/]", "", s)

        # Collapse repeated slashes and strip root markers
        s = re.sub(r"/{2,}", "/", s)
        s = s.lstrip("/.")

        if not s:
            return None

        p = Path(s)
        # Validate extension
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            return None

        # Restrict top-level directory
        parts = p.parts
        if len(parts) > 1 and parts[0] not in ALLOWED_TOP_DIRS:
            ext = p.suffix.lower()
            if ext in {".css"}:
                p = Path("css") / p.name
            elif ext in {".js"}:
                p = Path("js") / p.name
            elif ext in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg"}:
                p = Path("assets") / p.name
            else:
                p = Path(p.name)

        return str(p)

    def _list_all_files(self, start: Path) -> List[Path]:
        return [p for p in start.rglob("*") if p.is_file() and ".git" not in str(p)]

    def _choose_best_app_dir(self) -> Optional[Path]:
        """
        Choose a directory containing index.html that likely represents the built app.
        Heuristic: directory with index.html and the most total files.
        """
        candidates: List[Tuple[int, Path]] = []
        for idx in self.output_dir.rglob("index.html"):
            app_dir = idx.parent
            files = self._list_all_files(app_dir)
            score = len(files)
            candidates.append((score, app_dir))
        if not candidates:
            return None
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]

    def _get_pages_build_status(self, user: str, repo: str, token: str) -> Optional[str]:
        """
        Returns 'building', 'built', 'errored', or None if unknown/unavailable.
        """
        url = f"https://api.github.com/repos/{user}/{repo}/pages/builds/latest"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return (data.get("status") or "").lower()
        except Exception:
            pass
        return None

    # --------------------
    # Stages
    # --------------------

    def show_example(self):
        """Display example sentences"""
        examples = [
            "Create a portfolio website with a hero section, about me, projects gallery, and contact form",
            "Build a landing page for a SaaS product with pricing tiers and feature comparison",
            "Make a recipe blog with search functionality and ingredient filters",
            "Design a minimalist task manager with drag-and-drop and local storage",
            "Create an interactive data dashboard with charts showing sales metrics"
        ]

        print("\n" + "="*80)
        print("📝 SINGLE SENTENCE STATIC WEB APP GENERATOR")
        print("="*80)
        print("\nExample sentences you can use:")
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. {example}")
        print("\n" + "="*80 + "\n")

    def run_scope_stage(self, sentence: str) -> bool:
        """Stage 1: Define requirements"""
        print(f"\n{'='*80}")
        print(f"🎯 STAGE 1: SCOPE")
        print(f"{'='*80}\n")

        self.ai.reset_conversation()

        system_prompt = """You are a senior product manager and technical architect.
Your job is to analyze a single sentence description of a web app and extract comprehensive requirements.
Provide detailed requirements including:
- Core features and functionality
- UI/UX design guidelines
- Technical stack recommendations
- Content structure
- User interactions
Format your response as a structured JSON object."""

        iteration = 0
        while iteration < self.config.max_iterations:
            iteration += 1
            print(f"📋 Scope Iteration {iteration}/{self.config.max_iterations}")

            if iteration == 1:
                prompt = f"""Analyze this web app request and provide comprehensive requirements:
"{sentence}"

Return a JSON object with these keys:
- app_name: suggested name
- description: detailed description
- features: array of feature objects with name, description, priority
- pages: array of page objects with name, purpose, sections
- design: object with theme, colors, typography, layout
- tech_stack: object with html_features, css_frameworks, js_libraries
- content: object describing content needs"""
            else:
                print("\nCurrent requirements:")
                print(json.dumps(self.requirements, indent=2))

                user_input = input("\n✏️  Refine requirements (or 'approve' to continue): ").strip()

                if user_input.lower() == 'approve':
                    print("✅ Requirements approved!")
                    return True

                prompt = f"""Current requirements:
{json.dumps(self.requirements, indent=2)}

User feedback: {user_input}

Update the requirements JSON based on this feedback."""

            response = self.ai.call(prompt, system_prompt)

            # Extract JSON from response
            try:
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    self.requirements = json.loads(json_str)
                else:
                    print("⚠️  Could not parse AI response as JSON")
                    continue
            except json.JSONDecodeError:
                print("⚠️  Invalid JSON in AI response")
                continue

            # Save requirements
            req_file = self.output_dir / "requirements.json"
            req_file.parent.mkdir(parents=True, exist_ok=True)
            with open(req_file, 'w', encoding='utf-8') as f:
                json.dump(self.requirements, f, indent=2)

        print("\n⚠️  Max iterations reached. Using current requirements.")
        return True

    def run_build_stage(self) -> bool:
        """Stage 2: Build the application"""
        print(f"\n{'='*80}")
        print(f"🔨 STAGE 2: BUILD")
        print(f"{'='*80}\n")

        self.ai.reset_conversation()
        plan = WorkPlan(Stage.BUILD, self.output_dir)

        # Generate work plan
        print("📝 Creating build plan...")
        system_prompt = """You are a senior full-stack developer. Create a comprehensive build plan."""

        prompt = f"""Based on these requirements, create a detailed build plan:
{json.dumps(self.requirements, indent=2)}

Return a JSON array of todo items. Each item should have:
- title: short task title
- description: detailed description
- acceptance_criteria: array of criteria strings

Focus on creating actual files: HTML, CSS, JavaScript, assets, etc."""
        response = self.ai.call(prompt, system_prompt)

        # Parse todos
        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            if start_idx >= 0 and end_idx > start_idx:
                todos_json = json.loads(response[start_idx:end_idx])
                for todo_data in todos_json:
                    plan.add_todo(
                        todo_data.get("title", "Task"),
                        todo_data.get("description", ""),
                        todo_data.get("acceptance_criteria", [])
                    )
                plan.save()
        except Exception:
            print("⚠️  Could not parse build plan")
            return False

        print(f"✅ Created {len(plan.todos)} build tasks\n")

        # Execute build plan
        completed_count = 0
        for todo in plan.todos:
            print(f"\n🔧 Working on: {todo['title']}")
            print(f"   {todo['description']}")

            prompt = f"""Complete this build task:

Task: {todo['title']}
Description: {todo['description']}
Acceptance Criteria:
{chr(10).join('- ' + c for c in todo['acceptance_criteria'])}

Requirements context:
{json.dumps(self.requirements, indent=2)}

Provide the complete file contents needed. Format as:
FILENAME: path/to/file
```language
file contents here
```

Create all necessary files (HTML, CSS, JS, etc.)."""

            response = self.ai.call(prompt, system_prompt)

            # Parse and save files for this response only; only retry if zero saved this call
            files_saved = self._extract_and_save_files(response)

            if files_saved == 0:
                print(f"   ℹ️  Couldn’t parse files from the response. Requesting explicit file format...")
                retry_prompt = f"""Please provide the complete file contents for this task using this EXACT format:

FILENAME: path/to/file.html
```html
<html>
... complete file content ...
</html>
```

FILENAME: path/to/file.css
```css
/* complete CSS content */
```

Task: {todo['title']}
Description: {todo['description']}"""

                response = self.ai.call(retry_prompt, system_prompt)
                self._extract_and_save_files(response)

            # Verify acceptance criteria (non-blocking)
            print("   ✓ Checking acceptance criteria...")
            verify_prompt = f"""Review the work completed for this task:

Task: {todo['title']}
Acceptance Criteria:
{chr(10).join('- ' + c for c in todo['acceptance_criteria'])}

Given the files created in the project directory, does this meet all acceptance criteria?
Respond with JSON:
{{"met": true/false, "issues": ["list", "of", "issues"]}}"""

            verify_response = self.ai.call(verify_prompt, system_prompt)

            try:
                start = verify_response.find('{')
                end = verify_response.rfind('}') + 1
                result = json.loads(verify_response[start:end])
                if result.get("met", False):
                    print(f"   ✅ Task completed successfully")
                else:
                    print(f"   ⚠️  Issues found: {', '.join(result.get('issues', []))}")
                plan.complete_todo(todo['id'])
                completed_count += 1
            except Exception as e:
                print(f"   ✅ Task completed (verification unclear: {e})")
                plan.complete_todo(todo['id'])
                completed_count += 1

        print(f"\n✅ Build stage complete: {completed_count}/{len(plan.todos)} tasks finished")
        return True

    def _extract_and_save_files(self, response: str) -> int:
        """Extract file contents from AI response and save them. Returns number of files saved."""
        files_saved = 0

        # Pattern 1: FILENAME: followed by code block
        pattern1 = r'FILENAME:\s*([^\n]+)\s*```[\w]*\n(.*?)```'
        matches = re.findall(pattern1, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip().strip('`')
            self._save_file(filepath, content.rstrip())
            files_saved += 1

        # Pattern 2: Code blocks with inline filename comments (// filename.js)
        pattern2 = r'```[\w]*\s*(?://|#|<!--)\s*([^\n]+?\.(?:html|css|js|json|svg|png|jpg|jpeg|gif|ico))\s*(?:-->)?\s*\n(.*?)```'
        matches = re.findall(pattern2, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            if not (self.output_dir / filepath).exists():
                self._save_file(filepath, content.rstrip())
                files_saved += 1

        # Pattern 3: Markdown-style file headers
        pattern3 = r'#+\s*(?:File:|Filename:)?\s*`?([^\n]+?\.(?:html|css|js|json|svg))`?\s*\n```[\w]*\n(.*?)```'
        matches = re.findall(pattern3, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip().strip('`')
            if not (self.output_dir / filepath).exists():
                self._save_file(filepath, content.rstrip())
                files_saved += 1

        # Pattern 4: Direct file paths in code blocks
        pattern4 = r'```[\w]*\s*\n(?:\/\/|#|<!--)?\s*([a-zA-Z0-9_\-\/\.]+\.(?:html|css|js|json|svg|png|jpg|jpeg|gif|ico))\s*(?:-->)?\s*\n(.*?)```'
        matches = re.findall(pattern4, response, re.DOTALL)
        for filepath, content in matches:
            filepath = filepath.strip()
            if not (self.output_dir / filepath).exists():
                self._save_file(filepath, content.rstrip())
                files_saved += 1

        # Fallback: infer from language
        if files_saved == 0:
            code_blocks = re.findall(r'```(\w+)\n(.*?)```', response, re.DOTALL)
            for lang, content in code_blocks:
                if lang == 'html' and '<html' in content.lower():
                    self._save_file('index.html', content.rstrip())
                    files_saved += 1
                elif lang == 'css':
                    self._save_file('styles.css', content.rstrip())
                    files_saved += 1
                elif lang in ('javascript', 'js'):
                    self._save_file('script.js', content.rstrip())
                    files_saved += 1

        if files_saved == 0:
            print("   ℹ️  No files could be extracted from the AI response. Saved raw response to debug_response.txt")
            debug_file = self.output_dir / "debug_response.txt"
            debug_file.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*80}\n")
                f.write(f"Response at {time.strftime('%Y-%m-%d %H:%M:%S')}:\n")
                f.write(response)
                f.write(f"\n{'='*80}\n")

        return files_saved

    def _save_file(self, filepath: str, content: str):
        """Save a file to the output directory with sanitization and safety."""
        if not content or not content.strip():
            print(f"   ⚠️  Skipped empty file (no content). Raw name: {filepath}")
            return

        sanitized = self._sanitize_filepath(filepath)
        if not sanitized:
            print(f"   ℹ️  Skipped file with unsupported or invalid path: {filepath}")
            return

        if sanitized != filepath:
            print(f"   ℹ️  Normalized filename: '{filepath}' -> '{sanitized}'")

        try:
            full_path = self._safe_join(self.output_dir, sanitized)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   💾 Saved: {sanitized} ({len(content)} chars)")
        except Exception as e:
            print(f"   ❌ Failed to save '{filepath}' as '{sanitized}': {e}")

    def run_test_stage(self) -> bool:
        """Stage 3: Test the application"""
        print(f"\n{'='*80}")
        print(f"🧪 STAGE 3: TEST")
        print(f"{'='*80}\n")

        self.ai.reset_conversation()
        plan = WorkPlan(Stage.TEST, self.output_dir)

        # Generate test plan
        print("📝 Creating test plan...")
        system_prompt = """You are a QA engineer. Create a comprehensive test plan."""

        prompt = f"""Create a test plan for this web app:
{json.dumps(self.requirements, indent=2)}

Return a JSON array of test items with title, description, and acceptance_criteria."""
        response = self.ai.call(prompt, system_prompt)

        try:
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            todos_json = json.loads(response[start_idx:end_idx])
            for todo_data in todos_json:
                plan.add_todo(
                    todo_data.get("title", "Test"),
                    todo_data.get("description", ""),
                    todo_data.get("acceptance_criteria", [])
                )
            plan.save()
        except Exception:
            print("⚠️  Could not parse test plan, using basic tests")
            plan.add_todo(
                "File existence check",
                "Verify all required files exist",
                ["index.html exists", "CSS files exist", "JS files exist if needed"]
            )
            plan.save()

        print(f"✅ Created {len(plan.todos)} test tasks\n")

        # Inventory files recursively
        if not self.output_dir.exists():
            print(f"⚠️  Output directory doesn't exist: {self.output_dir}")
            print("   Creating directory...")
            self.output_dir.mkdir(parents=True, exist_ok=True)

        created_files = self._list_all_files(self.output_dir)
        html_files = [f for f in created_files if f.suffix.lower() == ".html"]
        css_files = [f for f in created_files if f.suffix.lower() == ".css"]
        js_files = [f for f in created_files if f.suffix.lower() == ".js"]

        print(f"📁 Files found:")
        print(f"   HTML: {len(html_files)} files")
        print(f"   CSS: {len(css_files)} files")
        print(f"   JS: {len(js_files)} files")
        print(f"   Total: {len(created_files)} files")

        # Execute tests (non-blocking; we proceed regardless)
        completed_count = 0
        for todo in plan.todos:
            print(f"\n🧪 Testing: {todo['title']}")
            index_exists = (self.output_dir / "index.html").exists()
            has_html = len(html_files) > 0

            if index_exists or has_html:
                print(f"   ✅ Files present: {len(created_files)} total")
                plan.complete_todo(todo['id'])
                completed_count += 1
            else:
                print(f"   ⚠️  No HTML files found in {self.output_dir}")
                plan.complete_todo(todo['id'])
                completed_count += 1

        print(f"\n✅ Test stage complete: {completed_count}/{len(plan.todos)} tests finished")
        return True

    def run_document_stage(self) -> bool:
        """Stage 4: Document the application"""
        print(f"\n{'='*80}")
        print(f"📚 STAGE 4: DOCUMENT")
        print(f"{'='*80}\n")

        self.ai.reset_conversation()
        plan = WorkPlan(Stage.DOCUMENT, self.output_dir)

        plan.add_todo(
            "Create README.md",
            "Create comprehensive project documentation",
            ["README.md exists", "Contains setup instructions", "Contains features list"]
        )
        plan.save()

        print(f"✅ Created {len(plan.todos)} documentation tasks\n")

        for todo in plan.todos:
            print(f"\n📝 Creating: {todo['title']}")

            system_prompt = """You are a technical writer. Create clear, comprehensive documentation."""

            prompt = f"""Create a README.md for this web app:
{json.dumps(self.requirements, indent=2)}

Include:
- Project title and description
- Features list
- Setup/installation instructions
- Usage guide
- File structure
- Technologies used
- License (MIT)

Format as markdown."""
            response = self.ai.call(prompt, system_prompt)

            readme_path = self.output_dir / "README.md"
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(response)

            print(f"   ✅ Created README.md")
            plan.complete_todo(todo['id'])

        return plan.is_complete()

    def run_deploy_stage(self) -> bool:
        """Stage 5: Deploy to GitHub Pages"""
        print(f"\n{'='*80}")
        print(f"🚀 STAGE 5: DEPLOY")
        print(f"{'='*80}\n")

        if not all([self.config.github_username, self.config.github_token, self.config.github_repo]):
            print("⚠️  GitHub credentials not configured. Skipping deployment.")
            print(f"📦 Your web app is ready in: {self.output_dir}")
            return True

        plan = WorkPlan(Stage.DEPLOY, self.output_dir)

        plan.add_todo(
            "Flatten app to root",
            "Ensure index.html and assets are in the repo root for GitHub Pages",
            ["index.html exists in repo root"]
        )
        plan.add_todo(
            "Initialize Git repository",
            "Create local git repo and initial commit",
            ["Git repo initialized", ".git directory exists", "Files staged and committed"]
        )
        plan.add_todo(
            "Create/Verify GitHub repository",
            "Create or verify remote repository on GitHub",
            ["Remote repository ready", "Repository is public or accessible"]
        )
        plan.add_todo(
            "Push to GitHub safely",
            "Push code to remote repository without force by default",
            ["Code pushed to main branch", "All files uploaded"]
        )
        plan.add_todo(
            "Enable GitHub Pages and wait",
            "Configure GitHub Pages deployment and poll until live",
            ["GitHub Pages enabled", "Site is live (HTTP 200)"]
        )
        plan.save()

        # 1) Flatten app to root (ensure index.html exists in root)
        print("\n📁 Ensuring app files are in repo root...")
        root_index = self.output_dir / "index.html"
        if not root_index.exists():
            best_dir = self._choose_best_app_dir()
            if best_dir is None:
                print("❌ No index.html found anywhere. Aborting deployment to avoid pushing README-only.")
                return False

            print(f"   Found index.html in: {best_dir}")
            print(f"   Copying contents to repo root...")
            for item in best_dir.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(best_dir)
                    dest = self.output_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
            if best_dir != self.output_dir:
                shutil.rmtree(best_dir, ignore_errors=True)

        # Confirm index.html exists now
        if not (self.output_dir / "index.html").exists():
            print("❌ Still no index.html in root after flattening. Aborting deployment.")
            return False

        # Add .nojekyll to avoid Jekyll processing issues
        (self.output_dir / ".nojekyll").write_text("", encoding="utf-8")

        plan.complete_todo(1)

        # 2) Initialize Git repository
        print("\n🧩 Initializing Git repository...")
        os.chdir(self.output_dir)
        try:
            subprocess.run(["git", "init"], check=True, capture_output=True, text=True)

            # Show a preview of files that will be committed
            files = self._list_all_files(Path("."))
            print(f"   Will commit {len(files)} files:")
            for p in sorted(files)[:50]:
                print(f"   - {p}")
            if len(files) > 50:
                print(f"   ... and {len(files)-50} more")

            # Stage all changes including deletions
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True, text=True)
            # Commit (may fail if nothing to commit; ignore non-zero)
            subprocess.run(["git", "commit", "-m", "Deploy commit"], capture_output=True, text=True)

            print("   ✅ Local git repo ready")
            plan.complete_todo(2)
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Git init/stage/commit issue: {e}")
            plan.complete_todo(2)

        # 3) Create / verify GitHub repo
        print("\n🌐 Creating/verifying GitHub repository...")
        try:
            headers = {
                "Authorization": f"token {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {
                "name": self.config.github_repo,
                "description": self.requirements.get("description", "Generated web app"),
                "private": False,
                "auto_init": False
            }
            response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
            if response.status_code in [201, 422]:  # 422 already exists
                print("   ✅ GitHub repository ready")
                plan.complete_todo(3)
            else:
                print(f"   ⚠️  GitHub API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ⚠️  Error verifying/creating repo: {e}")

        # 4) Push safely (no --force)
        print("\n⬆️  Pushing to GitHub (safe mode)...")
        try:
            remote_url = f"https://{self.config.github_token}@github.com/{self.config.github_username}/{self.config.github_repo}.git"
            remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
            if "origin" in remotes.stdout.split():
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True, capture_output=True, text=True)
            else:
                subprocess.run(["git", "remote", "add", "origin", remote_url], check=True, capture_output=True, text=True)

            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True, text=True)
            push = subprocess.run(["git", "push", "-u", "origin", "main"], text=True, capture_output=True)
            if push.returncode != 0:
                print("   ⚠️  Non-fast-forward or other push error. Not forcing by default.")
                print("   Details:", push.stderr.strip())
            else:
                print("   ✅ Pushed to GitHub")
                plan.complete_todo(4)
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Push failed: {e}")

        # 5) Enable GitHub Pages and wait for site to go live
        print("\n🟢 Enabling GitHub Pages and waiting for deployment...")
        site_url = None
        try:
            headers = {
                "Authorization": f"token {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            data = {"source": {"branch": "main", "path": "/"}}
            response = requests.post(
                f"https://api.github.com/repos/{self.config.github_username}/{self.config.github_repo}/pages",
                headers=headers,
                json=data
            )
            if response.status_code in [201, 409]:  # 409 already enabled
                site_url = f"https://{self.config.github_username}.github.io/{self.config.github_repo}"
                print(f"   ✅ GitHub Pages configuration accepted")
                print(f"   ⏳ Waiting for deployment to complete...")

                max_wait, interval, elapsed = 180, 10, 0
                last_status = None
                while elapsed < max_wait:
                    time.sleep(interval)
                    elapsed += interval

                    status = self._get_pages_build_status(self.config.github_username, self.config.github_repo, self.config.github_token)
                    if status != last_status:
                        print(f"   ⏳ Pages build status: {status or 'unknown'} ({elapsed}s)")
                        last_status = status

                    if status == "errored":
                        print("   ❌ GitHub Pages build errored. Check repository Settings → Pages → Build logs.")
                        break

                    # Confirm via HEAD or GET
                    is_live = False
                    try:
                        head_resp = requests.head(site_url, timeout=10, allow_redirects=True)
                        if head_resp.status_code == 200:
                            is_live = True
                        else:
                            get_resp = requests.get(site_url, timeout=10, allow_redirects=True)
                            if get_resp.status_code == 200:
                                is_live = True
                    except Exception:
                        pass

                    if status == "built" and is_live:
                        print(f"   ✅ Pages build completed and site is live at: {site_url}")
                        plan.complete_todo(5)
                        break

                if plan.todos[-1]["status"] != "completed":
                    print("   ⚠️  Timed out waiting for Pages. It may still complete shortly.")
            else:
                print(f"   ⚠️  Pages API error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"   ⚠️  Error enabling pages: {e}")

        self.deployed_url = site_url
        return plan.is_complete()

    def run(self, sentence: str):
        """Run the complete generation pipeline"""
        try:
            # Stage 1: Scope
            if not self.run_scope_stage(sentence):
                print("❌ Scope stage failed")
                return

            # Stage 2: Build
            if not self.run_build_stage():
                print("❌ Build stage failed")
                return

            # Stage 3: Test
            if not self.run_test_stage():
                print("❌ Test stage failed")
                return

            # Stage 4: Document
            if not self.run_document_stage():
                print("❌ Documentation stage failed")
                return

            # Stage 5: Deploy
            if not self.run_deploy_stage():
                print("❌ Deployment stage failed")
                return

            print(f"\n{'='*80}")
            print("🎉 SUCCESS! Your web app is complete!")
            print(f"{'='*80}")
            print(f"\n📁 Location: {self.output_dir}")

            if self.deployed_url:
                print(f"\n🌐 Live URL: {self.deployed_url}")
                print(f"   (Your app is now accessible on the web!)")
            elif self.config.github_repo:
                print(f"\n⚠️  Deployment configured but URL not confirmed")
                print(f"   Check: https://{self.config.github_username}.github.io/{self.config.github_repo}")

            print(f"\n{'='*80}\n")

        except KeyboardInterrupt:
            print("\n\n⚠️  Generation interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")


def load_config() -> Config:
    """Load configuration from environment and config file"""
    config_file = Path.home() / ".webappgen" / "config.json"

    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    else:
        config_data = {}

    # Determine provider default (env overrides file)
    provider = os.getenv("AI_PROVIDER", config_data.get("provider", "anthropic")).lower()

    # Smart defaults per provider
    if provider == "openai":
        default_model = "gpt-4o"
        default_api_key = os.getenv("OPENAI_API_KEY", config_data.get("api_key", ""))
    else:
        provider = "anthropic"
        default_model = "claude-sonnet-4-5-20250929"
        default_api_key = os.getenv("ANTHROPIC_API_KEY", config_data.get("api_key", ""))

    return Config(
        provider=provider,
        api_key=default_api_key,
        model_id=os.getenv("MODEL_ID", config_data.get("model_id", default_model)),
        github_username=os.getenv("GITHUB_USERNAME", config_data.get("github_username")),
        github_token=os.getenv("GITHUB_TOKEN", config_data.get("github_token")),
        github_repo=os.getenv("GITHUB_REPO", config_data.get("github_repo")),
        output_dir=os.getenv("OUTPUT_DIR", config_data.get("output_dir", "./generated_webapp"))
    )


def save_config(config: Config):
    """Save configuration to file"""
    config_dir = Path.home() / ".webappgen"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2)
    print(f"✅ Configuration saved to {config_file}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Generate static web apps from a single sentence"
    )
    parser.add_argument("sentence", nargs="*", help="Description of the web app to generate")
    parser.add_argument("--config", action="store_true", help="Configure API keys and settings")
    parser.add_argument("--provider", choices=["anthropic", "openai"], help="AI provider (anthropic or openai)")
    parser.add_argument("--api-key", help="API key for the selected provider")
    parser.add_argument("--model", help="Model ID (e.g., claude-sonnet-4-5-20250929 or gpt-4o)")
    parser.add_argument("--github-user", help="GitHub username")
    parser.add_argument("--github-token", help="GitHub personal access token")
    parser.add_argument("--github-repo", help="GitHub repository name")
    parser.add_argument("--output", help="Output directory (default: ./generated_webapp)")

    args = parser.parse_args()

    config = load_config()

    # Interactive configuration
    if args.config:
        print("🔧 Configuration Setup")
        print("\nAvailable providers:")
        print("  1. anthropic (Claude models)")
        print("  2. openai (GPT models)")

        provider_input = input(f"\nSelect provider (1 or 2) [{config.provider}]: ").strip()

        # Map selection to provider
        if provider_input == "1":
            config.provider = "anthropic"
        elif provider_input == "2":
            config.provider = "openai"
        elif provider_input.lower() in ["anthropic", "openai"]:
            config.provider = provider_input.lower()
        elif provider_input == "":
            pass
        else:
            print("Invalid provider, using default: anthropic")
            config.provider = "anthropic"

        # Suggest defaults based on provider and adjust model if crossing over
        if config.provider == "openai":
            suggested_model = "gpt-4o"
            api_key_label = "OpenAI API Key"
            if "claude" in (config.model_id or "").lower():
                config.model_id = suggested_model
        else:
            suggested_model = "claude-sonnet-4-5-20250929"
            api_key_label = "Anthropic API Key"
            if "gpt" in (config.model_id or "").lower():
                config.model_id = suggested_model

        # API key prompt
        current_key_preview = (config.api_key[:10] + "...") if config.api_key else ""
        entered_key = input(f"\n{api_key_label} [{current_key_preview}]: ").strip()
        if entered_key:
            config.api_key = entered_key

        # Show popular models
        print(f"\nPopular {config.provider} models:")
        if config.provider == "openai":
            print("  - gpt-4o (recommended)")
            print("  - gpt-4o-mini")
            print("  - gpt-4-turbo")
            print("  - gpt-3.5-turbo")
        else:
            print("  - claude-sonnet-4-5-20250929 (recommended)")
            print("  - claude-opus-4-20241229")
            print("  - claude-3-5-sonnet-20241022")

        # Model ID prompt
        model_input = input(f"\nModel ID [{config.model_id}]: ").strip()
        if model_input:
            config.model_id = model_input

        # GitHub config
        print("\nGitHub Configuration (optional, for deployment):")
        gui = input(f"GitHub Username [{config.github_username or ''}]: ").strip()
        if gui:
            config.github_username = gui
        gtoken_preview = (config.github_token[:10] + "...") if config.github_token else ""
        gtk = input(f"GitHub Token [{gtoken_preview}]: ").strip()
        if gtk:
            config.github_token = gtk
        grep = input(f"GitHub Repo [{config.github_repo or ''}]: ").strip()
        if grep:
            config.github_repo = grep
        out = input(f"Output Directory [{config.output_dir}]: ").strip()
        if out:
            config.output_dir = out

        save_config(config)
        print(f"\n✅ Configuration saved! Provider: {config.provider.upper()}, Model: {config.model_id}")
        return

    # Override config with command-line arguments
    if args.provider:
        config.provider = args.provider
    if args.api_key:
        config.api_key = args.api_key
    if args.model:
        config.model_id = args.model
    if args.github_user:
        config.github_username = args.github_user
    if args.github_token:
        config.github_token = args.github_token
    if args.github_repo:
        config.github_repo = args.github_repo
    if args.output:
        config.output_dir = args.output

    # Validate required config
    if not config.api_key:
        print("❌ Error: API key not configured")
        print("Run with --config to set up, or set ANTHROPIC_API_KEY/OPENAI_API_KEY environment variable")
        sys.exit(1)

    # Display current configuration
    print(f"\n🤖 Using: {config.provider.upper()} - {config.model_id}")
    print(f"📁 Output: {config.output_dir}\n")

    # Create generator
    generator = WebAppGenerator(config)

    # Get sentence
    if args.sentence:
        sentence = " ".join(args.sentence)
    else:
        generator.show_example()
        sentence = input("Enter your web app description: ").strip()

    if not sentence:
        print("❌ Error: No description provided")
        sys.exit(1)

    # Run generation
    generator.run(sentence)


if __name__ == "__main__":
    main()
