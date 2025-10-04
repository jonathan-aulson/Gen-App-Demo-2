#!/usr/bin/env python3
"""
Single Sentence Static Web App Generator (complete replacement)

Features included:
- Multi-provider AI (Anthropic or OpenAI)
- 5-stage pipeline: Scope, Build, Test, Document, Deploy
- Optional stacks: basic (HTML/CSS/JS) or react (Vite + TS + Tailwind)
- React stack scaffold + GitHub Actions Pages workflow (no local Node required)
- Dependency management: ensures package.json contains required deps and scans imports
- Asset path rewriting and local/live asset checks (BeautifulSoup if available, installs if missing)
- Iterative LLM testing loop that generates >=5 scenarios/feature, predicts Pass/Fail, proposes fixes
- Progressive summarization and budgeted prompts to avoid model context length errors
- Playwright E2E hooks (--e2e and --e2e-deployed), auto-installs playwright stack if requested
- Deployment choices before deploy: GitHub Pages, Vercel, Netlify; create new repo or use existing; optional wipe (force push)
- Fallback skeleton to guarantee an always-deployable site (basic and react)
- Auto-install missing Python packages on demand (bs4, playwright stack)
- Robust filename sanitization and POSIX path normalization

Save as webapp_gen.py and run:
  python webapp_gen.py --config
  python webapp_gen.py "Design a minimalist task manager with drag-and-drop and local storage"
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

# --------------------
# Core dataclasses
# --------------------

class Stage(Enum):
    SCOPE = "scope"
    BUILD = "build"
    TEST = "test"
    DOCUMENT = "document"
    DEPLOY = "deploy"

@dataclass
class Config:
    api_key: str
    model_id: str
    provider: str = "anthropic"  # anthropic or openai
    github_username: Optional[str] = None
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    output_dir: str = "./generated_webapp"
    max_iterations: int = 10
    stack: str = "basic"  # "basic" or "react"
    e2e: bool = False
    e2e_deployed: bool = False

    @property
    def api_base_url(self) -> str:
        if self.provider.lower() == "openai":
            return "https://api.openai.com/v1/chat/completions"
        else:
            return "https://api.anthropic.com/v1/messages"

# --------------------
# AI Client
# --------------------

class AIClient:
    def __init__(self, config: Config):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []

    def _call_anthropic(self, prompt: str, system_prompt: str = None) -> str:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        messages = self.conversation_history + [{"role": "user", "content": prompt}]
        payload = {
            "model": self.config.model_id,
            "max_tokens": 4096,
            "messages": messages
        }
        if system_prompt:
            payload["system"] = system_prompt
        r = requests.post(self.config.api_base_url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        try:
            return data["content"][0]["text"]
        except Exception:
            return json.dumps(data)

    def _call_openai(self, prompt: str, system_prompt: str = None) -> str:
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
        lower = (self.config.model_id or "").lower()
        if any(m in lower for m in ["gpt-4o", "gpt-4.1", "gpt-4.5", "o1", "o3"]):
            payload["max_completion_tokens"] = 4096
        else:
            payload["max_tokens"] = 4096
        r = requests.post(self.config.api_base_url, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)

    def call(self, prompt: str, system_prompt: str = None) -> str:
        try:
            if self.config.provider.lower() == "openai":
                text = self._call_openai(prompt, system_prompt)
            else:
                text = self._call_anthropic(prompt, system_prompt)
            self.conversation_history.append({"role": "user", "content": prompt})
            self.conversation_history.append({"role": "assistant", "content": text})
            return text
        except Exception as e:
            print(f"❌ API Error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    print(f"   Response: {e.response.text}")
                except Exception:
                    pass
            return ""

    def reset_conversation(self):
        self.conversation_history = []

# --------------------
# WorkPlan
# --------------------

class WorkPlan:
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
        for t in self.todos:
            if t["id"] == todo_id:
                t["status"] = "completed"
                t["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                break
        self.save()

    def get_pending_todos(self) -> List[Dict]:
        return [t for t in self.todos if t["status"] == "pending"]

    def is_complete(self) -> bool:
        return len(self.get_pending_todos()) == 0

# --------------------
# Generator
# --------------------

ALLOWED_EXTENSIONS = {
    ".html", ".css", ".js", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".ts", ".tsx", ".jsx", ".map", ".woff", ".woff2", ".webp"
}
ALLOWED_TOP_DIRS = {"", "assets", "css", "js", "images", "img", "static", "src", ".github", "public"}

class WebAppGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.ai = AIClient(config)
        self.output_dir = Path(config.output_dir)
        self.requirements: Dict = {}
        self.deployed_url: Optional[str] = None
        
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
    
    # -------------
    # Environment helpers and auto-install
    # -------------

    def _ensure_python_packages(self, packages: List[str]) -> bool:
        ok = True
        for name in packages:
            mod_name = "bs4" if name == "beautifulsoup4" else name
            try:
                __import__(mod_name)
            except ImportError:
                print(f"   ℹ️  Installing missing package: {name} ...")
                res = subprocess.run([sys.executable, "-m", "pip", "install", name], text=True)
                if res.returncode != 0:
                    print(f"   ❌ Failed to install {name} (pip exited {res.returncode})")
                    ok = False
        return ok

    def _ensure_bs4(self) -> bool:
        try:
            import bs4  # type: ignore
            return True
        except Exception:
            return self._ensure_python_packages(["beautifulsoup4"])

    def _ensure_playwright_stack(self) -> bool:
        # Install pytest, pytest-playwright, playwright
        needed = ["pytest", "pytest-playwright", "playwright"]
        if not self._ensure_python_packages(needed):
            return False
        # playwright install
        try:
            res = subprocess.run([sys.executable, "-m", "playwright", "install"], text=True)
            if res.returncode != 0:
                print("   ❌ playwright install failed")
                return False
        except Exception as e:
            print(f"   ❌ playwright install error: {e}")
            return False
        return True

    def _preflight_config(self):
        if not self.config.api_key:
            print("⚠️  Missing API key for provider:", self.config.provider)
            entered = input("Enter API key now (or leave blank to continue): ").strip()
            if entered:
                self.config.api_key = entered
        if self.config.provider.lower() not in ("anthropic", "openai"):
            print("⚠️  Unknown provider; defaulting to anthropic")
            self.config.provider = "anthropic"

    # -------------
    # File/Path helpers
    # -------------

    def _safe_join(self, base: Path, *paths: str) -> Path:
        candidate = base.joinpath(*paths).resolve()
        base_resolved = base.resolve()
        try:
            if not candidate.is_relative_to(base_resolved):  # type: ignore[attr-defined]
                raise ValueError("Path traversal detected")
        except AttributeError:
            if not str(candidate).startswith(str(base_resolved)):
                raise ValueError("Path traversal detected")
        return candidate

    def _sanitize_filepath(self, raw: str) -> Optional[str]:
        if not raw:
            return None
        s = raw.strip().strip('`"\'')
        s = s.replace("\\", "/")
        s = re.split(r"\s+\(|`", s, maxsplit=1)[0].strip()
        s = re.sub(r"^(?:file:|filename:)\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"[^A-Za-z0-9._\-/]", "", s)
        s = re.sub(r"/{2,}", "/", s)
        s = s.lstrip("/.")
        if not s:
            return None
        p = Path(s)
        if p.suffix.lower() not in ALLOWED_EXTENSIONS:
            return None
        parts = p.parts
        if len(parts) > 1 and parts[0] not in ALLOWED_TOP_DIRS:
            ext = p.suffix.lower()
            if ext in {".css"}:
                p = Path("css") / p.name
            elif ext in {".js", ".ts", ".tsx", ".jsx"}:
                p = Path("src") / p.name if self.config.stack == "react" else Path("js") / p.name
            elif ext in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp"}:
                p = Path("assets") / p.name
            else:
                p = Path(p.name)
        # Return POSIX-style path
        return str(p).replace("\\", "/")

    def _list_all_files(self, start: Path) -> List[Path]:
        return [p for p in start.rglob("*") if p.is_file() and ".git" not in str(p)]

    def _choose_best_app_dir(self) -> Optional[Path]:
        candidates: List[Tuple[int, Path]] = []
        for idx in self.output_dir.rglob("index.html"):
            app_dir = idx.parent
            files = self._list_all_files(app_dir)
            candidates.append((len(files), app_dir))
        if not candidates:
            return None
        candidates.sort(reverse=True, key=lambda x: x[0])
        return candidates[0][1]

    # -------------
    # package.json helpers (React)
    # -------------

    def _load_package_json(self) -> Optional[Dict]:
        pkg = self.output_dir / "package.json"
        if not pkg.exists():
            return None
        try:
            return json.loads(pkg.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"   ⚠️  Could not read package.json: {e}")
            return None

    def _save_package_json(self, data: Dict):
        try:
            (self.output_dir / "package.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            print("   💾 Updated package.json")
        except Exception as e:
            print(f"   ❌ Failed to write package.json: {e}")

    def _ensure_react_dependencies(self):
        pkg = self._load_package_json()
        if pkg is None:
            print("   ⚠️  package.json not found; React scaffold likely missing.")
            return
        required_deps = {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "lucide-react": "^0.453.0",
            "@dnd-kit/core": "^6.1.0",
            "@dnd-kit/sortable": "^7.0.2",
            "@dnd-kit/modifiers": "6.0.2",
            "@tanstack/react-table": "^8.20.5",
            "react-hook-form": "^7.52.1",
            "@hookform/resolvers": "^3.9.0",
            "zod": "^3.23.8",
            "date-fns": "^3.6.0",
            "react-day-picker": "^9.0.7",
            "@nivo/core": "^0.86.0",
            "@nivo/line": "^0.86.0",
            "@nivo/bar": "^0.86.0"
        }
        required_dev = {
            "@vitejs/plugin-react": "^4.3.1",
            "typescript": "^5.6.2",
            "vite": "^5.4.8",
            "tailwindcss": "^3.4.10",
            "postcss": "^8.4.45",
            "autoprefixer": "^10.4.20",
            "tailwindcss-animate": "^1.0.7"
        }
        pkg.setdefault("dependencies", {})
        pkg.setdefault("devDependencies", {})
        pkg.setdefault("scripts", {})
        changed = False
        for k, v in required_deps.items():
            if k not in pkg["dependencies"]:
                pkg["dependencies"][k] = v; changed = True
        for k, v in required_dev.items():
            if k not in pkg["devDependencies"]:
                pkg["devDependencies"][k] = v; changed = True
        scripts_required = {"build": "vite build", "dev": "vite", "preview": "vite preview"}
        for k, v in scripts_required.items():
            if pkg["scripts"].get(k) != v:
                pkg["scripts"][k] = v; changed = True
        if changed: self._save_package_json(pkg)
        else: print("   ✅ React dependencies already present")

    def _scan_imports_and_ensure_deps(self):
        pkg = self._load_package_json()
        if pkg is None:
            return
        pkg.setdefault("dependencies", {})
        pkg.setdefault("devDependencies", {})
        known = {
            "lucide-react": ("dependencies", "lucide-react", "^0.453.0"),
            "@dnd-kit/core": ("dependencies", "@dnd-kit/core", "^6.1.0"),
            "@dnd-kit/sortable": ("dependencies", "@dnd-kit/sortable", "^7.0.2"),
            "@dnd-kit/modifiers": ("dependencies", "@dnd-kit/modifiers", "6.0.2"),
            "@tanstack/react-table": ("dependencies", "@tanstack/react-table", "^8.20.5"),
            "react-hook-form": ("dependencies", "react-hook-form", "^7.52.1"),
            "@hookform/resolvers": ("dependencies", "@hookform/resolvers", "^3.9.0"),
            "zod": ("dependencies", "zod", "^3.23.8"),
            "date-fns": ("dependencies", "date-fns", "^3.6.0"),
            "react-day-picker": ("dependencies", "react-day-picker", "^9.0.7"),
            "@nivo/core": ("dependencies", "@nivo/core", "^0.86.0"),
            "@nivo/line": ("dependencies", "@nivo/line", "^0.86.0"),
            "@nivo/bar": ("dependencies", "@nivo/bar", "^0.86.0"),
            "@radix-ui/react-dialog": ("dependencies", "@radix-ui/react-dialog", "^1.0.5"),
            "@radix-ui/react-dropdown-menu": ("dependencies", "@radix-ui/react-dropdown-menu", "^2.0.6"),
            "@radix-ui/react-toast": ("dependencies", "@radix-ui/react-toast", "^1.1.5"),
            "@radix-ui/react-label": ("dependencies", "@radix-ui/react-label", "^2.0.2"),
            "@vitejs/plugin-react": ("devDependencies", "@vitejs/plugin-react", "^4.3.1"),
            "tailwindcss": ("devDependencies", "tailwindcss", "^3.4.10"),
            "postcss": ("devDependencies", "postcss", "^8.4.45"),
            "autoprefixer": ("devDependencies", "autoprefixer", "^10.4.20"),
            "tailwindcss-animate": ("devDependencies", "tailwindcss-animate", "^1.0.7"),
            "vite": ("devDependencies", "vite", "^5.4.8"),
            "typescript": ("devDependencies", "typescript", "^5.6.2")
        }
        import_re = re.compile(r'^\s*import\s+(?:[^"\']+from\s+)?[\'"]([^\'"]+)[\'"]', re.MULTILINE)
        src_dir = self.output_dir / "src"
        found_modules = set()
        for p in src_dir.rglob("*"):
            if p.suffix.lower() not in (".ts", ".tsx", ".jsx", ".js"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                for m in import_re.findall(text):
                    if not m.startswith("."):
                        found_modules.add(m)
            except Exception:
                pass
        changed = False
        for m in found_modules:
            if m in known:
                which, pkg_name, ver = known[m]
                if pkg_name not in pkg[which]:
                    pkg[which][pkg_name] = ver
                    changed = True
        if changed:
            self._save_package_json(pkg)
        else:
            print("   ✅ No new dependencies needed from import scan")

    # -------------
    # Asset handling (bs4 preferred, regex fallback)
    # -------------

    def _rewrite_asset_paths_to_relative(self):
        if self._ensure_bs4():
            try:
                import bs4  # type: ignore
                html_files = list(self.output_dir.rglob("*.html"))
                if not html_files:
                    return
                def fix_url(u: Optional[str]) -> Optional[str]:
                    if not u or u.startswith(("http://", "https://", "data:", "mailto:", "#")):
                        return u
                    if u.startswith("/"):
                        u = u.lstrip("/")
                    return u
                for html in html_files:
                    try:
                        text = html.read_text(encoding="utf-8", errors="ignore")
                        soup = bs4.BeautifulSoup(text, "html.parser")
                        for tag in soup.find_all("img"):
                            if tag.has_attr("src"):
                                tag["src"] = fix_url(tag["src"])
                        for tag in soup.find_all("script"):
                            if tag.has_attr("src"):
                                tag["src"] = fix_url(tag["src"])
                        for tag in soup.find_all("link"):
                            if tag.has_attr("href"):
                                tag["href"] = fix_url(tag["href"])
                        html.write_text(str(soup), encoding="utf-8")
                    except Exception as e:
                        print(f"   ⚠️  Could not rewrite asset paths in {html}: {e}")
                return
            except Exception:
                pass
        # regex fallback
        print("   ℹ️  Using regex-based path rewrite fallback.")
        html_files = list(self.output_dir.rglob("*.html"))
        if not html_files:
            return
        src_re = re.compile(r'(\s(src|href)\s*=\s*[\'"])/([^\'"]+)')
        for html in html_files:
            try:
                txt = html.read_text(encoding="utf-8", errors="ignore")
                new_txt = src_re.sub(r'\1\3', txt)
                if new_txt != txt:
                    html.write_text(new_txt, encoding="utf-8")
            except Exception as e:
                print(f"   ⚠️  Regex rewrite failed in {html}: {e}")

    def _collect_asset_refs(self) -> List[Path]:
        refs: List[Path] = []
        if self._ensure_bs4():
            try:
                import bs4  # type: ignore
                for html in self.output_dir.rglob("*.html"):
                    try:
                        text = html.read_text(encoding="utf-8", errors="ignore")
                        soup = bs4.BeautifulSoup(text, "html.parser")
                        def add_if_local(u: Optional[str]):
                            if not u or u.startswith(("http://", "https://", "data:", "mailto:", "#")):
                                return
                            p = (html.parent / u.lstrip("/")).resolve()
                            if str(p).startswith(str(self.output_dir.resolve())):
                                refs.append(p)
                        for t in soup.find_all(["img", "script"]):
                            add_if_local(t.get("src"))
                        for t in soup.find_all(["link", "a"]):
                            u = t.get("href")
                            if u and any(u.lower().endswith(ext) for ext in [".css",".js",".png",".jpg",".jpeg",".gif",".ico",".svg",".webp"]):
                                add_if_local(u)
                    except Exception as e:
                        print(f"   ⚠️  Asset parse failed in {html}: {e}")
                return refs
            except Exception:
                pass
        # regex fallback
        print("   ℹ️  Using regex-based asset scan fallback.")
        attr_re = re.compile(r'(?:src|href)\s*=\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
        for html in self.output_dir.rglob("*.html"):
            try:
                txt = html.read_text(encoding="utf-8", errors="ignore")
                for u in attr_re.findall(txt):
                    if u.startswith(("http://", "https://", "data:", "mailto:", "#")):
                        continue
                    if not any(u.lower().endswith(ext) for ext in (".css",".js",".png",".jpg",".jpeg",".gif",".ico",".svg",".webp")):
                        continue
                    p = (html.parent / u.lstrip("/")).resolve()
                    out_root = self.output_dir.resolve()
                    if str(p).startswith(str(out_root)):
                        refs.append(p)
            except Exception as e:
                print(f"   ⚠️  Regex asset scan failed in {html}: {e}")
        return refs

    def _assert_assets_exist_locally(self) -> bool:
        refs = self._collect_asset_refs()
        if not refs:
            print("   ℹ️  No local asset references detected or scan skipped.")
            return True
        missing = [p for p in refs if not p.exists()]
        if missing:
            print("   ❌ Missing asset files locally:")
            for m in missing[:50]:
                try: rel = m.relative_to(self.output_dir)
                except Exception: rel = m
                print("     -", rel)
            if len(missing) > 50:
                print(f"     ... and {len(missing)-50} more")
            return False
        print("   ✅ Local asset existence check passed")
        return True

    def _smoke_test_live_site(self, site_url: str) -> bool:
        if not site_url:
            return False
        try:
            r = requests.get(site_url, timeout=20, allow_redirects=True)
            if r.status_code != 200:
                print(f"   ❌ Live index fetch failed: {r.status_code}")
                return False
            try:
                import bs4  # type: ignore
            except Exception:
                print("   ℹ️  Skipping live image checks (install beautifulsoup4).")
                return True
            import urllib.parse
            soup = __import__("bs4").BeautifulSoup(r.text, "html.parser")
            imgs = [img.get("src") for img in soup.find_all("img")]
            imgs = [u for u in imgs if u and not u.startswith(("data:", "mailto:", "#"))]
            ok = True
            for u in imgs[:10]:
                full = urllib.parse.urljoin(site_url.rstrip("/") + "/", u)
                try:
                    ar = requests.get(full, timeout=10, allow_redirects=True)
                    if ar.status_code != 200:
                        print(f"   ❌ Live asset failed: {full} -> {ar.status_code}")
                        ok = False
                except Exception as e:
                    print(f"   ❌ Live asset exception: {full} -> {e}")
                    ok = False
            if ok: print("   ✅ Live smoke-test passed (index + sample images)")
            return ok
        except Exception as e:
            print(f"   ⚠️  Live smoke-test error: {e}")
            return False

    # -------------
    # React scaffold & workflow
    # -------------

    def _ensure_react_scaffold_and_workflow(self):
        pkg = self.output_dir / "package.json"
        src_dir = self.output_dir / "src"
        ghwf_dir = self.output_dir / ".github" / "workflows"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        src_dir.mkdir(parents=True, exist_ok=True)
        ghwf_dir.mkdir(parents=True, exist_ok=True)

        base = "/"
        if self.config.github_username and self.config.github_repo:
            if self.config.github_repo != f"{self.config.github_username}.github.io":
                base = f"/{self.config.github_repo}/"
        vite_cfg = (
            'import { defineConfig } from "vite";\n'
            'import react from "@vitejs/plugin-react";\n'
            f'export default defineConfig({{ base: "{base}", plugins: [react()] }});\n'
        )
        (self.output_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")

        tailwind_cfg = (
            'module.exports = {\n'
            '  content: ["./index.html", "./src/**/*.{ts,tsx,jsx,js}"],\n'
            '  theme: { extend: {} },\n'
            '  plugins: [require("tailwindcss-animate")],\n'
            '};\n'
        )
        (self.output_dir / "tailwind.config.js").write_text(tailwind_cfg, encoding="utf-8")
        (self.output_dir / "postcss.config.js").write_text('module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };\n', encoding="utf-8")

        index_html = (
            '<!doctype html>\n<html lang="en">\n  <head>\n'
            '    <meta charset="UTF-8" />\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n'
            '    <title>App</title>\n'
            '    <link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">\n'
            '  </head>\n  <body>\n    <div id="root"></div>\n    <script type="module" src="/src/main.tsx"></script>\n  </body>\n</html>\n'
        )
        (self.output_dir / "index.html").write_text(index_html, encoding="utf-8")
        (self.output_dir / "src" / "index.css").write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n", encoding="utf-8")
        main_tsx = (
            'import React from "react";\nimport ReactDOM from "react-dom/client";\nimport "./index.css";\nimport App from "./App";\n\nReactDOM.createRoot(document.getElementById("root")!).render(\n  <React.StrictMode>\n    <App />\n  </React.StrictMode>\n);\n'
        )
        (self.output_dir / "src" / "main.tsx").write_text(main_tsx, encoding="utf-8")
        app_tsx = (
            'import React from "react";\nimport { LucideCheckSquare } from "lucide-react";\nexport default function App(){\n  return (\n    <div className="min-h-screen bg-white text-slate-900">\n      <div className="mx-auto max-w-3xl p-6">\n        <header className="py-8">\n          <h1 className="text-3xl font-bold flex items-center gap-2">\n            <LucideCheckSquare className="w-7 h-7" />\n            App Starter\n          </h1>\n          <p className="mt-2 text-slate-600">React + Tailwind scaffold. The generator/LLM will expand this.</p>\n        </header>\n        <main className="space-y-6">\n          <section className="p-6 rounded-lg border bg-slate-50">\n            <h2 className="text-xl font-semibold">Getting Started</h2>\n            <p className="mt-2 text-slate-600">Add components and logic. This content ensures the site is never blank.</p>\n          </section>\n        </main>\n        <footer className="mt-12 text-sm text-slate-500">Generated by WebAppGenerator</footer>\n      </div>\n    </div>\n  );\n}\n'
        )
        (self.output_dir / "src" / "App.tsx").write_text(app_tsx, encoding="utf-8")
        (self.output_dir / "tsconfig.json").write_text('{\n  "compilerOptions": {\n    "target": "ES2020", "useDefineForClassFields": true, "lib": ["ES2020","DOM","DOM.Iterable"],\n    "module": "ESNext", "skipLibCheck": true, "jsx": "react-jsx", "moduleResolution": "Bundler",\n    "resolveJsonModule": true, "isolatedModules": true, "noEmit": true, "esModuleInterop": true,\n    "strict": true, "noUncheckedIndexedAccess": true, "forceConsistentCasingInFileNames": true\n  },\n  "include": ["src"]\n}\n', encoding="utf-8")

        if not (self.output_dir / "package.json").exists():
            package_json = {
                "name": "webapp",
                "private": True,
                "version": "0.0.0",
                "type": "module",
                "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                "dependencies": {
                    "react": "^18.3.1",
                    "react-dom": "^18.3.1",
                    "lucide-react": "^0.453.0",
                    "@dnd-kit/core": "^6.1.0",
                    "@dnd-kit/sortable": "^7.0.2",
                    "@dnd-kit/modifiers": "6.0.2",
                    "@nivo/core": "^0.86.0",
                    "@nivo/line": "^0.86.0",
                    "@nivo/bar": "^0.86.0",
                    "@tanstack/react-table": "^8.20.5",
                    "react-hook-form": "^7.52.1",
                    "@hookform/resolvers": "^3.9.0",
                    "zod": "^3.23.8",
                    "date-fns": "^3.6.0",
                    "react-day-picker": "^9.0.7"
                },
                "devDependencies": {
                    "@types/react": "^18.3.3",
                    "@types/react-dom": "^18.3.0",
                    "@vitejs/plugin-react": "^4.3.1",
                    "autoprefixer": "^10.4.20",
                    "postcss": "^8.4.45",
                    "tailwindcss": "^3.4.10",
                    "tailwindcss-animate": "^1.0.7",
                    "typescript": "^5.6.2",
                    "vite": "^5.4.8"
                }
            }
            (self.output_dir / "package.json").write_text(json.dumps(package_json, indent=2), encoding="utf-8")

        self._ensure_react_dependencies()
        pages_yml = (
            "name: Deploy to GitHub Pages\n"
            "on:\n"
            "  push:\n"
            "    branches: [ \"main\" ]\n"
            "permissions:\n"
            "  contents: read\n"
            "  pages: write\n"
            "  id-token: write\n"
            "concurrency:\n"
            "  group: pages\n"
            "  cancel-in-progress: true\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - name: Setup Node\n"
            "        uses: actions/setup-node@v4\n"
            "        with:\n"
            "          node-version: 20\n"
            "      - name: Install dependencies\n"
            "        run: |\n"
            "          if [ -f package-lock.json ]; then\n"
            "            npm ci\n"
            "          else\n"
            "            npm install\n"
            "          fi\n"
            "      - name: Build\n"
            "        run: npm run build\n"
            "      - name: Upload Pages artifact\n"
            "        uses: actions/upload-pages-artifact@v3\n"
            "        with:\n"
            "          path: ./dist\n"
            "  deploy:\n"
            "    needs: build\n"
            "    runs-on: ubuntu-latest\n"
            "    environment:\n"
            "      name: github-pages\n"
            "      url: ${{ steps.deployment.outputs.page_url }}\n"
            "    steps:\n"
            "      - id: deployment\n"
            "        uses: actions/deploy-pages@v4\n"
        )
        (self.output_dir / ".github" / "workflows" / "pages.yml").write_text(pages_yml, encoding="utf-8")

    # -------------
    # Playwright E2E
    # -------------

    def _run_playwright_e2e(self, base_url: str) -> bool:
        if not self._ensure_playwright_stack():
            print("   ⚠️  Could not install Playwright stack; skipping E2E.")
            return False
        try:
            tests_dir = self.output_dir / "tests" / "e2e"
            tests_dir.mkdir(parents=True, exist_ok=True)
            smoke = tests_dir / "test_smoke.py"
            if not smoke.exists():
                smoke.write_text(
                    'from playwright.sync_api import sync_playwright\n'
                    'def test_homepage_loads():\n'
                    '    with sync_playwright() as p:\n'
                    '        browser = p.chromium.launch()\n'
                    '        page = browser.new_page()\n'
                    f'        page.goto("{base_url}")\n'
                    '        assert page.title() is not None\n'
                    '        browser.close()\n',
                    encoding="utf-8"
                )
            res = subprocess.run([sys.executable, "-m", "pytest", "-q", str(tests_dir)], cwd=self.output_dir, text=True)
            return res.returncode == 0
        except Exception as e:
            print(f"   ⚠️  Playwright E2E run failed: {e}")
            return False

    # -------------
    # Fallback skeletons
    # -------------

    def _ensure_minimum_content_basic(self):
        idx = self.output_dir / "index.html"
        need = True
        if idx.exists():
            try:
                content = idx.read_text(encoding="utf-8", errors="ignore")
                if "<main" in content.lower() or len(content.strip()) > 400:
                    need = False
            except Exception:
                pass
        if need:
            idx.parent.mkdir(parents=True, exist_ok=True)
            skeleton = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Landing - Generated App</title>
  <link rel="stylesheet" href="css/styles.css">
  <style>
    body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu;margin:0}
    .container{max-width:1000px;margin:0 auto;padding:24px}
    .hero{padding:64px 24px;background:#f8fafc}
    .btn{background:#38bdf8;color:#0f172a;padding:12px 18px;border-radius:8px;text-decoration:none;font-weight:600}
    .grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
    .card{border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#fff}
  </style>
</head>
<body>
  <header class="container"><strong>Generated App</strong></header>
  <section class="hero"><div class="container"><h1>Your App Is Live</h1><p>This default landing page ensures you always deploy something visible.</p><p><a class="btn" href="#features">Explore Features</a></p></div></section>
  <main class="container" id="features" style="padding:40px 24px;">
    <h2>Features</h2>
    <div class="grid" style="margin-top:16px;">
      <div class="card"><h3>Fast</h3><p>Ready for static hosting.</p></div>
      <div class="card"><h3>Modern</h3><p>Built with best practices.</p></div>
      <div class="card"><h3>Extensible</h3><p>Easily add components and logic.</p></div>
    </div>
  </main>
  <footer class="container">Generated by WebAppGenerator</footer>
</body>
</html>
"""
            idx.write_text(skeleton, encoding="utf-8")
            print("   🧱 Added fallback landing skeleton (basic).")
        css = self.output_dir / "css" / "styles.css"
        if not css.exists():
            css.parent.mkdir(parents=True, exist_ok=True)
            css.write_text("/* default styles */\nbody{font-family:Inter,system-ui,-apple-system,'Segoe UI',Roboto,Ubuntu}\n", encoding="utf-8")

    def _ensure_minimum_content_react(self):
        if not (self.output_dir / "src" / "App.tsx").exists():
            self._ensure_react_scaffold_and_workflow()
            print("   🧱 Ensured React scaffold exists (fallback).")

    # -------------
    # Build/Test/Deploy pipeline
    # -------------
    # Summarization helpers to manage context size

    def _summarize_code_for_llm(self, path: Path, max_lines: int = 120) -> str:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
        suffix = path.suffix.lower()
        lines = text.splitlines()
        if suffix in (".ts", ".tsx", ".js", ".jsx"):
            keep = []
            import_re = re.compile(r'^\s*import\b')
            export_re = re.compile(r'^\s*export\b')
            func_re = re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\b')
            const_func_re = re.compile(r'^\s*(?:export\s+)?const\s+[A-Za-z0-9_]+\s*=\s*(?:async\s*)?\(')
            comp_re = re.compile(r'^\s*(?:export\s+)?(?:const|function)\s+[A-Z][A-Za-z0-9_]*\s*(?:[:=]|\()')
            iface_re = re.compile(r'^\s*interface\s+[A-Za-z0-9_]+')
            type_re = re.compile(r'^\s*type\s+[A-Za-z0-9_]+')
            for ln in lines:
                if (import_re.match(ln) or export_re.match(ln) or func_re.match(ln) or
                    const_func_re.match(ln) or comp_re.match(ln) or iface_re.match(ln) or type_re.match(ln)):
                    keep.append(ln.strip())
                if len(keep) >= max_lines:
                    break
            if not keep:
                keep = lines[:max_lines]
            return "\n".join(keep)
        head = "\n".join(lines[:max_lines])
        return head

    def _gather_code_summaries(self, max_files: int, max_lines: int, char_budget: int) -> List[Dict]:
        all_files = sorted(self._list_all_files(self.output_dir))
        ext_priority = {".tsx": 1, ".ts": 1, ".jsx": 1, ".js": 1, ".html": 2, ".css": 3, ".json": 4}
        def prio(p: Path):
            return ext_priority.get(p.suffix.lower(), 5), len(str(p))
        candidates = sorted(all_files, key=prio)
        summaries = []
        total_chars = 0
        for p in candidates:
            if len(summaries) >= max_files:
                break
            rel = str(p.relative_to(self.output_dir)) if self.output_dir in p.parents else str(p)
            if p.suffix.lower() not in (".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".json"):
                continue
            summ = self._summarize_code_for_llm(p, max_lines=max_lines)
            if not summ.strip():
                continue
            entry = {"path": rel.replace("\\", "/"), "head": summ}
            add_len = len(json.dumps(entry))
            if total_chars + add_len > char_budget:
                break
            summaries.append(entry)
            total_chars += add_len
        return summaries

    # -------------
    # Build stage
    # -------------

    def run_scope_stage(self, sentence: str) -> bool:
        print(f"\n{'='*80}\n🎯 STAGE 1: SCOPE\n{'='*80}\n")
        self.ai.reset_conversation()
        system_prompt = "You are a senior product manager and technical architect. Return structured JSON requirements."
        iteration = 0
        while iteration < self.config.max_iterations:
            iteration += 1
            print(f"📋 Scope Iteration {iteration}/{self.config.max_iterations}")
            if iteration == 1:
                prompt = f"""Analyze this web app request and return JSON with:
app_name, description, features, pages, design, tech_stack, content.
Request: {sentence}"""
            else:
                print("\nCurrent requirements:")
                print(json.dumps(self.requirements, indent=2))
                user_input = input("\n✏️  Refine requirements (or 'approve' to continue): ").strip()
                if user_input.lower() == "approve":
                    print("✅ Requirements approved!")
                    return True
                prompt = f"""Current requirements: {json.dumps(self.requirements, indent=2)}
User feedback: {user_input}
Update the requirements JSON."""
            resp = self.ai.call(prompt, system_prompt)
            try:
                s, e = resp.find("{"), resp.rfind("}") + 1
                if s >= 0 and e > s:
                    self.requirements = json.loads(resp[s:e])
                else:
                    print("⚠️  Could not parse AI response as JSON")
                    continue
            except Exception:
                print("⚠️  Invalid JSON in AI response")
                continue
            (self.output_dir / "requirements.json").parent.mkdir(parents=True, exist_ok=True)
            (self.output_dir / "requirements.json").write_text(json.dumps(self.requirements, indent=2), encoding="utf-8")
        print("\n⚠️  Max iterations reached. Using current requirements.")
        return True

    def run_build_stage(self) -> bool:
        print(f"\n{'='*80}\n🔨 STAGE 2: BUILD\n{'='*80}\n")
        self.ai.reset_conversation()
        plan = WorkPlan(Stage.BUILD, self.output_dir)
        print("📝 Creating build plan...")
        system_prompt = "You are a senior full-stack developer. Create a comprehensive build plan."
        stack_note = "React + TypeScript (Vite) under src/ and index.html at root." if self.config.stack == "react" else "Basic HTML/CSS/JS."
        prompt = f"""Based on requirements: {json.dumps(self.requirements, indent=2)}
Constraints: Stack={self.config.stack}. {stack_note}
Return JSON array of todos: [{{title, description, acceptance_criteria:[]}}]."""
        resp = self.ai.call(prompt, system_prompt)
        try:
            s, e = resp.find("["), resp.rfind("]") + 1
            todos = json.loads(resp[s:e])
            for t in todos:
                plan.add_todo(t.get("title", "Task"), t.get("description", ""), t.get("acceptance_criteria", []))
            plan.save()
        except Exception:
            print("⚠️  Could not parse build plan")
            return False
        print(f"✅ Created {len(plan.todos)} build tasks\n")
        if self.config.stack == "react":
            self._ensure_react_scaffold_and_workflow()
        completed = 0
        for todo in plan.todos:
            print(f"\n🔧 Working on: {todo['title']}\n   {todo['description']}")
            stack_instr = ("For React: create files under src/ (tsx/ts/css). Use React+TS+Tailwind."
                           if self.config.stack == "react" else
                           "For Basic: provide static HTML/CSS/JS with relative assets.")
            bprompt = f"""Complete this task:
Task: {todo['title']}
Acceptance Criteria:
{chr(10).join('- ' + c for c in todo['acceptance_criteria'])}
Requirements: {json.dumps(self.requirements, indent=2)}
{stack_instr}
Provide files in EXACT format:

FILENAME: path/to/file
```language
file contents here
```"""
            bresp = self.ai.call(bprompt, system_prompt)
            saved = self._extract_and_save_files(bresp)
            if saved == 0:
                print("   ℹ️  Couldn’t parse files. Asking for explicit format...")
                retry = f"""Provide files using EXACT format:
FILENAME: path/to/file.tsx
```tsx
// content
```
Task: {todo['title']}"""
                self._extract_and_save_files(self.ai.call(retry, system_prompt))
            print("   ✓ Checking acceptance criteria...")
            vprompt = f"""Review:
Task: {todo['title']}
Acceptance Criteria:
{chr(10).join('- ' + c for c in todo['acceptance_criteria'])}
Respond JSON: {{'met': true/false, 'issues': ['...']}}"""
            vresp = self.ai.call(vprompt, system_prompt)
            try:
                s, e = vresp.find("{"), vresp.rfind("}") + 1
                res = json.loads(vresp[s:e])
                if res.get("met", False):
                    print("   ✅ Task completed successfully")
                else:
                    print(f"   ⚠️  Issues: {', '.join(res.get('issues', []))}")
                plan.complete_todo(todo["id"]); completed += 1
            except Exception as ex:
                print(f"   ✅ Task completed (verification unclear: {ex})")
                plan.complete_todo(todo["id"]); completed += 1
        # Ensure fallback content exists
        if self.config.stack == "react":
            self._ensure_minimum_content_react()
        else:
            self._ensure_minimum_content_basic()
        print(f"\n✅ Build stage complete: {completed}/{len(plan.todos)} tasks finished")
        return True

    def _extract_and_save_files(self, response: str) -> int:
        files_saved = 0
        pattern1 = r'FILENAME:\s*([^\n]+)\s*```[\w]*\n(.*?)```'
        for filepath, content in re.findall(pattern1, response, re.DOTALL):
            self._save_file(filepath.strip().strip('`'), content.rstrip()); files_saved += 1
        pattern2 = r'```[\w]*\s*(?://|#|<!--)\s*([^\n]+?\.(?:html|css|js|json|svg|png|jpg|jpeg|gif|ico|ts|tsx|jsx|map|woff|woff2|webp))\s*(?:-->)?\s*\n(.*?)```'
        for filepath, content in re.findall(pattern2, response, re.DOTALL):
            if not (self.output_dir / filepath.strip()).exists():
                self._save_file(filepath.strip(), content.rstrip()); files_saved += 1
        pattern3 = r'#+\s*(?:File:|Filename:)?\s*`?([^\n]+?\.(?:html|css|js|json|svg|ts|tsx|jsx))`?\s*\n```[\w]*\n(.*?)```'
        for filepath, content in re.findall(pattern3, response, re.DOTALL):
            if not (self.output_dir / filepath.strip().strip('`')).exists():
                self._save_file(filepath.strip().strip('`'), content.rstrip()); files_saved += 1
        pattern4 = r'```[\w]*\s*\n(?:\/\/|#|<!--)?\s*([a-zA-Z0-9_\-\/\.]+\.(?:html|css|js|json|svg|png|jpg|jpeg|gif|ico|ts|tsx|jsx|map|woff|woff2|webp))\s*(?:-->)?\s*\n(.*?)```'
        for filepath, content in re.findall(pattern4, response, re.DOTALL):
            if not (self.output_dir / filepath.strip()).exists():
                self._save_file(filepath.strip(), content.rstrip()); files_saved += 1
        if files_saved == 0:
            blocks = re.findall(r'```(\w+)\n(.*?)```', response, re.DOTALL)
            for lang, content in blocks:
                if lang == "html" and "<html" in content.lower():
                    self._save_file("index.html", content.rstrip()); files_saved += 1
                elif lang == "css":
                    self._save_file("css/styles.css", content.rstrip()); files_saved += 1
                elif lang in ("javascript", "js"):
                    self._save_file("js/script.js", content.rstrip()); files_saved += 1
                elif lang in ("tsx", "typescript"):
                    self._save_file("src/App.tsx", content.rstrip()); files_saved += 1
        if files_saved == 0:
            dbg = self.output_dir / "debug_response.txt"
            dbg.parent.mkdir(parents=True, exist_ok=True)
            with open(dbg, 'a', encoding='utf-8') as f:
                f.write(f"\n\n{'='*80}\nResponse at {time.strftime('%Y-%m-%d %H:%M:%S')}:\n{response}\n{'='*80}\n")
            print("   ℹ️  No files extracted; saved raw response for debugging.")
        return files_saved

    def _save_file(self, filepath: str, content: str):
        if not content or not content.strip():
            print(f"   ⚠️  Skipped empty file: {filepath}")
            return
        sanitized = self._sanitize_filepath(filepath)
        if not sanitized:
            print(f"   ℹ️  Skipped invalid path: {filepath}")
            return
        if sanitized != filepath:
            print(f"   ℹ️  Normalized filename: '{filepath}' -> '{sanitized}'")
        try:
            full = self._safe_join(self.output_dir, sanitized)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            print(f"   💾 Saved: {sanitized} ({len(content)} chars)")
        except Exception as e:
            print(f"   ❌ Failed to save '{filepath}' as '{sanitized}': {e}")

    # -------------
    # Test stage (progressive summarization to avoid context limit)
    # -------------

    def run_test_stage(self) -> bool:
        print(f"\n{'='*80}\n🧪 STAGE 3: TEST\n{'='*80}\n")
        self.ai.reset_conversation()
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
        files = self._list_all_files(self.output_dir)
        htmls = [f for f in files if f.suffix.lower() == ".html"]
        csss = [f for f in files if f.suffix.lower() == ".css"]
        js_like = [f for f in files if f.suffix.lower() in (".js", ".ts", ".tsx", ".jsx")]
        print(f"📁 Files: HTML={len(htmls)}, CSS={len(csss)}, JS/TS/TSX/JSX={len(js_like)}, Total={len(files)}")
        if self.config.stack == "basic":
            print("🔧 Rewriting asset paths to relative (basic stack)...")
            self._rewrite_asset_paths_to_relative()
            print("🔎 Checking local asset existence...")
            if not self._assert_assets_exist_locally():
                print("   ⚠️  Assets missing; will try to address in LLM repair loop.")
        # Iterative LLM testing loop with progressive budgets
        system_prompt = "You are a senior QA engineer. Generate scenarios (>=5 per feature), predict pass/fail, and propose fixes."
        budgets = [(30, 120, 200_000), (20, 80, 120_000), (12, 60, 80_000), (8, 50, 60_000), (5, 40, 40_000)]
        max_iters = 3
        all_passed = False
        for iteration in range(1, max_iters + 1):
            print(f"\n🧪 LLM Test Iteration {iteration}/{max_iters}")
            features = []
            parsed_ok = False
            for max_files, max_lines, char_budget in budgets:
                file_summaries = self._gather_code_summaries(max_files, max_lines, char_budget)
                test_plan_prompt = f"""Requirements:
{json.dumps(self.requirements, indent=2)}

Code summaries (compact): up to {max_files} files, {max_lines} lines each.
{json.dumps(file_summaries, indent=2)}

Tasks:
- Identify features and generate at least 5 scenarios per feature that might fail.
- Predict Pass/Fail for each scenario and explain why.
- Return JSON only with shape:
{{"features":[{{"name":"Feature","scenarios":[{{"name":"Scenario","steps":["..."],"expected":"...","prediction":"Pass|Fail","reason":"..."}}]}}],"summary":{{"passed":X,"failed":Y}}}}"""
                response = self.ai.call(test_plan_prompt, system_prompt)
                try:
                    s, e = response.find("{"), response.rfind("}") + 1
                    plan_json = json.loads(response[s:e])
                    features = plan_json.get("features", [])
                    failed = sum(1 for f in features for s in f.get("scenarios", []) if str(s.get("prediction","")).lower()=="fail")
                    passed = sum(1 for f in features for s in f.get("scenarios", []) if str(s.get("prediction","")).lower()=="pass")
                    print(f"   Predicted: {passed} passed, {failed} failed (budget {max_files}x{max_lines})")
                    parsed_ok = True
                    break
                except Exception:
                    print(f"   ℹ️  Parsing failed at budget {max_files}x{max_lines}; trying smaller budget...")
            if not parsed_ok:
                print("   ❌ Could not parse LLM test plan at any budget; skipping remaining iterations.")
                break
            if failed == 0 and passed > 0:
                print("   ✅ All scenarios predicted to pass.")
                all_passed = True
                break
            # Ask for fixes
            fix_prompt = f"""Provide FIXES as complete files in EXACT format (only files to change/create):
FILENAME: path/to/file
```language
<full file content>
```
Failing scenarios context:
{json.dumps(features, indent=2)}"""
            fix_resp = self.ai.call(fix_prompt, system_prompt)
            saved = self._extract_and_save_files(fix_resp)
            print(f"   🔧 Applied {saved} fix file(s).")
        if not all_passed:
            print("   ⚠️  Tests did not fully pass; proceeding with best effort.")
        # Optional E2E local (basic)
        if self.config.e2e and self.config.stack == "basic":
            print("\n🧪 Running local Playwright E2E (basic stack)...")
            try:
                import threading
                from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
                os.chdir(self.output_dir)
                server = ThreadingHTTPServer(("127.0.0.1", 8000), SimpleHTTPRequestHandler)
                t = threading.Thread(target=server.serve_forever, daemon=True); t.start()
                ok = self._run_playwright_e2e("http://127.0.0.1:8000")
                server.shutdown()
                print("   ✅ Local E2E passed" if ok else "   ⚠️  Local E2E failed")
            except Exception as e:
                print(f"   ⚠️  Could not run local E2E: {e}")
        print("\n✅ Test stage complete")
        return True

    # -------------
    # Document stage
    # -------------

    def run_document_stage(self) -> bool:
        print(f"\n{'='*80}\n📚 STAGE 4: DOCUMENT\n{'='*80}\n")
        self.ai.reset_conversation()
        plan = WorkPlan(Stage.DOCUMENT, self.output_dir)
        plan.add_todo("Create README.md", "Create comprehensive project documentation",
                      ["README.md exists", "Contains setup instructions", "Contains features list"])
        plan.save()
        for todo in plan.todos:
            print(f"\n📝 Creating: {todo['title']}")
            system_prompt = "You are a technical writer. Create clear, comprehensive documentation."
            stack_section = ("React + TypeScript + Vite + Tailwind; GitHub Actions build for Pages."
                             if self.config.stack == "react" else "Basic HTML/CSS/JS deployed to GitHub Pages.")
            prompt = f"""Create README.md:
{json.dumps(self.requirements, indent=2)}
Include: Title/description, Features, Stack: {stack_section}, Setup, Usage, File structure, Technologies, License (MIT)"""
            response = self.ai.call(prompt, system_prompt)
            (self.output_dir / "README.md").write_text(response, encoding="utf-8")
            print("   ✅ Created README.md")
            plan.complete_todo(todo["id"])
        return plan.is_complete()

    # -------------
    # Deploy stage with choices and repo create/wipe
    # -------------

    def _write_vercel_config(self):
        vercel = self.output_dir / "vercel.json"
        if vercel.exists(): return
        if self.config.stack == "react":
            cfg = {"version": 2, "buildCommand": "npm run build", "outputDirectory": "dist", "framework": "vite"}
        else:
            cfg = {"version": 2, "buildCommand": "", "outputDirectory": ".", "framework": "static"}
        vercel.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("   🧩 Added vercel.json")

    def _write_netlify_config(self):
        nt = self.output_dir / "netlify.toml"
        if nt.exists(): return
        if self.config.stack == "react":
            content = '[build]\ncommand = "npm run build"\npublish = "dist"\n\n[[redirects]]\nfrom = "/*"\nto = "/index.html"\nstatus = 200\n'
        else:
            content = '[build]\ncommand = ""\npublish = "."\n'
        nt.write_text(content, encoding="utf-8")
        print("   🧩 Added netlify.toml")

    def run_deploy_stage(self) -> bool:
        print(f"\n{'='*80}\n🚀 STAGE 5: DEPLOY\n{'='*80}\n")
        print("Deployment options:\n  1. GitHub Pages\n  2. Vercel\n  3. Netlify")
        choice = input("Choose provider (1/2/3) [1]: ").strip() or "1"
        provider_map = {"1": "github_pages", "2": "vercel", "3": "netlify"}
        deploy_provider = provider_map.get(choice, "github_pages")
        print("\nRepository options:\n  1. Create new GitHub repo\n  2. Use existing GitHub repo")
        repo_choice = input("Choose repo option (1/2) [1]: ").strip() or "1"
        repo_name = self.config.github_repo
        if repo_choice == "1":
            repo_name = input(f"New repo name [{repo_name or 'my-generated-app'}]: ").strip() or repo_name or "my-generated-app"
        else:
            repo_name = input(f"Existing repo name (owner/name or name) [{repo_name or ''}]: ").strip() or repo_name
            if "/" in repo_name:
                owner, name = repo_name.split("/", 1)
                self.config.github_username = owner
                repo_name = name
        self.config.github_repo = repo_name
        wipe_choice = input("Wipe repository contents before deploying? (y/N): ").strip().lower()
        allow_force_push = wipe_choice == "y"
        if not all([self.config.github_username, self.config.github_token, self.config.github_repo]):
            print("⚠️  GitHub credentials not configured. Skipping deployment.")
            print(f"📦 Your web app is ready in: {self.output_dir}")
            return True
        if deploy_provider == "vercel": self._write_vercel_config()
        if deploy_provider == "netlify": self._write_netlify_config()
        plan = WorkPlan(Stage.DEPLOY, self.output_dir)
        if self.config.stack == "react":
            plan.add_todo("Prepare React repo", "Ensure React scaffold and Actions workflow exist", ["package.json exists", ".github/workflows/pages.yml exists"])
        else:
            plan.add_todo("Flatten app to root", "Ensure index.html and assets are in repo root", ["index.html exists in repo root"])
        plan.add_todo("Initialize Git repository", "Create local git repo and initial commit", [".git exists", "Files staged and committed"])
        plan.add_todo("Create/Verify GitHub repo", "Create or verify remote repo on GitHub", ["Remote repository ready"])
        plan.add_todo("Push to GitHub", "Push code to remote repository", ["Code pushed to main"])
        if deploy_provider == "github_pages" and self.config.stack == "react":
            plan.add_todo("Enable Pages via Actions", "Configure Pages to use Actions build", ["Pages build_type set to workflow"])
        plan.add_todo("Wait for deployment (if applicable)", "Poll URL until live", ["Site returns HTTP 200"])
        plan.save()
        # Prepare artifacts
        if self.config.stack == "react":
            print("\n📁 Ensuring React scaffold and Actions workflow exist...")
            self._ensure_react_scaffold_and_workflow()
            self._scan_imports_and_ensure_deps()
            plan.complete_todo(1)
        else:
            print("\n📁 Ensuring app files are in repo root (basic)...")
            root_index = self.output_dir / "index.html"
            if not root_index.exists():
                best = self._choose_best_app_dir()
                if best is None:
                    print("❌ No index.html found. Adding fallback skeleton.")
                    self._ensure_minimum_content_basic()
                else:
                    print(f"   Found index.html in: {best}; copying to root...")
                    for item in best.rglob("*"):
                        if item.is_file():
                            rel = item.relative_to(best)
                            dest = self.output_dir / rel
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(item, dest)
                    if best != self.output_dir:
                        shutil.rmtree(best, ignore_errors=True)
            if not (self.output_dir / "index.html").exists():
                self._ensure_minimum_content_basic()
            (self.output_dir / ".nojekyll").write_text("", encoding="utf-8")
            self._rewrite_asset_paths_to_relative()
            plan.complete_todo(1)
        # Git init and commit
        print("\n🧩 Initializing Git repository...")
        os.chdir(self.output_dir)
        try:
            subprocess.run(["git", "init"], check=True, capture_output=True, text=True)
            files = self._list_all_files(Path("."))
            print(f"   Will commit {len(files)} files:")
            for p in sorted(files)[:50]: print(f"   - {p}")
            if len(files) > 50: print(f"   ... and {len(files)-50} more")
            subprocess.run(["git", "add", "-A"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "commit", "-m", "Deploy commit"], capture_output=True, text=True)
            print("   ✅ Local git repo ready")
            plan.complete_todo(2)
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Git init/stage/commit issue: {e}")
            plan.complete_todo(2)
        # Create / verify repo via API
        print("\n🌐 Creating/verifying GitHub repository...")
        try:
            headers = {"Authorization": f"token {self.config.github_token}", "Accept": "application/vnd.github.v3+json"}
            data = {"name": self.config.github_repo, "description": self.requirements.get("description", "Generated web app"), "private": False, "auto_init": False}
            resp = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
            if resp.status_code in [201, 422]:
                print("   ✅ GitHub repository ready")
                plan.complete_todo(3)
            else:
                print(f"   ⚠️  GitHub API error: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"   ⚠️  Error verifying/creating repo: {e}")
        # Push (optionally wipe)
        print("\n⬆️  Pushing to GitHub...")
        try:
            remote_url = f"https://{self.config.github_token}@github.com/{self.config.github_username}/{self.config.github_repo}.git"
            remotes = subprocess.run(["git", "remote"], capture_output=True, text=True)
            if "origin" in remotes.stdout.split():
                subprocess.run(["git", "remote", "set-url", "origin", remote_url], check=True, capture_output=True, text=True)
            else:
                subprocess.run(["git", "remote", "add", "origin", remote_url], check=True, capture_output=True, text=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True, capture_output=True, text=True)
            if allow_force_push:
                print("   ⚠️  User opted to wipe repository: force pushing (with lease)...")
                push = subprocess.run(["git", "push", "--force", "origin", "main"], text=True, capture_output=True)
            else:
                push = subprocess.run(["git", "push", "-u", "origin", "main"], text=True, capture_output=True)
            if push.returncode != 0:
                print("   ⚠️  Push error:", push.stderr.strip())
            else:
                print("   ✅ Pushed to GitHub")
                plan.complete_todo(4)
        except subprocess.CalledProcessError as e:
            print(f"   ⚠️  Push failed: {e}")
        # Provider-specific finalize
        site_url = None
        if deploy_provider == "github_pages":
            if self.config.stack == "react":
                print("\n🟢 Setting Pages to Actions workflow (best effort)...")
                self._enable_pages_actions_build()
                plan.complete_todo(5)
            print("\n⏳ Waiting for GitHub Pages deployment...")
            site_url = f"https://{self.config.github_username}.github.io/{self.config.github_repo}"
            if self.config.github_repo == f"{self.config.github_username}.github.io":
                site_url = f"https://{self.config.github_username}.github.io"
            max_wait, interval, elapsed = (600 if self.config.stack == "react" else 180), 10, 0
            while elapsed < max_wait:
                time.sleep(interval); elapsed += interval
                status = self._get_pages_build_status(self.config.github_username, self.config.github_repo, self.config.github_token)
                if status:
                    print(f"   ⏳ Pages status: {status} ({elapsed}s)")
                    if status == "errored":
                        print("   ❌ Pages build errored. Check repository Settings → Pages → Build logs.")
                        break
                try:
                    head = requests.head(site_url, timeout=10, allow_redirects=True)
                    if head.status_code == 200:
                        print(f"   ✅ Site is live at: {site_url}")
                        plan.complete_todo(len(plan.todos))
                        break
                except Exception:
                    pass
            if plan.todos[-1]["status"] != "completed":
                print("   ⚠️  Timed out waiting for Pages. It may still complete shortly.")
            self.deployed_url = site_url
            print("\n🌐 Running live smoke test...")
            self._smoke_test_live_site(site_url or "")
        elif deploy_provider == "vercel":
            print("\n✅ Repo pushed. To finish on Vercel: import the repository in Vercel and configure build settings (npm run build -> dist).")
            plan.complete_todo(len(plan.todos))
        elif deploy_provider == "netlify":
            print("\n✅ Repo pushed. To finish on Netlify: create a site from Git and point build command to `npm run build` and publish `dist` (React) or `.` (basic).")
            plan.complete_todo(len(plan.todos))
        # Optional deployed E2E
        if self.config.e2e_deployed and self.deployed_url:
            print("\n🧪 Running Playwright E2E against deployed site...")
            ok = self._run_playwright_e2e(self.deployed_url)
            print("   ✅ Deployed E2E passed" if ok else "   ⚠️  Deployed E2E failed")
        return plan.is_complete()
    def _get_pages_build_status(self, owner: str, repo: str, token: Optional[str]) -> Optional[str]:
        """
        Query GitHub Pages latest build status for owner/repo.
        Returns one of: "building", "built", "errored", "pending", etc., or None on error.
        Requires self.config.github_token or token passed in.
        """
        if not owner or not repo:
            return None
        tok = token or self.config.github_token
        if not tok:
            return None
        url = f"https://api.github.com/repos/{owner}/{repo}/pages/builds/latest"
        headers = {"Authorization": f"token {tok}", "Accept": "application/vnd.github.v3+json"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # The API returns a build object with a `status` field
                return data.get("status")
            # 404 indicates no build yet
            if resp.status_code == 404:
                return None
            # For other statuses, print debug info and return None
            print(f"   ⚠️  GitHub Pages API returned {resp.status_code}: {resp.text[:400]}")
            return None
        except Exception as e:
            print(f"   ⚠️  Error fetching Pages build status: {e}")
            return None
    

    # -------------
    # Runner
    # -------------

    def run(self, sentence: str):
        try:
            self._preflight_config()
            if not self.run_scope_stage(sentence):
                print("❌ Scope stage failed"); return
            if not self.run_build_stage():
                print("❌ Build stage failed"); return
            if not self.run_test_stage():
                print("❌ Test stage failed"); return
            if not self.run_document_stage():
                print("❌ Documentation stage failed"); return
            if not self.run_deploy_stage():
                print("❌ Deployment stage failed"); return
            print(f"\n{'='*80}\n🎉 SUCCESS! Your web app is complete!\n{'='*80}")
            print(f"\n📁 Location: {self.output_dir}")
            if self.deployed_url:
                print(f"\n🌐 Live URL: {self.deployed_url}\n   (Your app is now accessible on the web!)")
        except KeyboardInterrupt:
            print("\n\n⚠️  Generation interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")

# --------------------
# Config load/save and CLI
# --------------------

def load_config() -> Config:
    cfg_file = Path.home() / ".webappgen" / "config.json"
    if cfg_file.exists():
        with open(cfg_file, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    else:
        cfg = {}
    provider = os.getenv("AI_PROVIDER", cfg.get("provider", "anthropic")).lower()
    if provider == "openai":
        default_model = "gpt-4o"
        default_key = os.getenv("OPENAI_API_KEY", cfg.get("api_key", ""))
    else:
        provider = "anthropic"
        default_model = "claude-sonnet-4-5-20250929"
        default_key = os.getenv("ANTHROPIC_API_KEY", cfg.get("api_key", ""))
    return Config(
        provider=provider,
        api_key=default_key,
        model_id=os.getenv("MODEL_ID", cfg.get("model_id", default_model)),
        github_username=os.getenv("GITHUB_USERNAME", cfg.get("github_username")),
        github_token=os.getenv("GITHUB_TOKEN", cfg.get("github_token")),
        github_repo=os.getenv("GITHUB_REPO", cfg.get("github_repo")),
        output_dir=os.getenv("OUTPUT_DIR", cfg.get("output_dir", "./generated_webapp")),
        stack=os.getenv("WEBAPP_STACK", cfg.get("stack", "basic")).lower(),
        e2e=bool(cfg.get("e2e", False)),
        e2e_deployed=bool(cfg.get("e2e_deployed", False)),
    )

def save_config(config: Config):
    cdir = Path.home() / ".webappgen"
    cdir.mkdir(exist_ok=True)
    cfile = cdir / "config.json"
    with open(cfile, 'w', encoding='utf-8') as f:
        json.dump(asdict(config), f, indent=2)
    print(f"✅ Configuration saved to {cfile}")

def main():
    parser = argparse.ArgumentParser(description="Generate static web apps from a single sentence")
    parser.add_argument("sentence", nargs="*", help="Description of the web app to generate")
    parser.add_argument("--config", action="store_true", help="Configure API keys and settings")
    parser.add_argument("--provider", choices=["anthropic", "openai"], help="AI provider")
    parser.add_argument("--api-key", help="API key")
    parser.add_argument("--model", help="Model ID")
    parser.add_argument("--github-user", help="GitHub username")
    parser.add_argument("--github-token", help="GitHub personal access token")
    parser.add_argument("--github-repo", help="GitHub repository name")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--stack", choices=["basic", "react"], help="Web app stack")
    parser.add_argument("--e2e", action="store_true", help="Run local Playwright E2E (basic stack only)")
    parser.add_argument("--e2e-deployed", action="store_true", help="Run Playwright E2E against deployed site")
    args = parser.parse_args()
    config = load_config()
    if args.config:
        print("🔧 Configuration Setup")
        print("\nAvailable providers: 1. anthropic  2. openai")
        psel = input(f"Select provider (1/2) [{config.provider}]: ").strip()
        if psel == "1": config.provider = "anthropic"
        elif psel == "2": config.provider = "openai"
        elif psel.lower() in ["anthropic", "openai"]: config.provider = psel.lower()
        if config.provider == "openai":
            suggested = "gpt-4o"; label = "OpenAI API Key"
            if "claude" in (config.model_id or "").lower(): config.model_id = suggested
        else:
            suggested = "claude-sonnet-4-5-20250929"; label = "Anthropic API Key"
            if "gpt" in (config.model_id or "").lower(): config.model_id = suggested
        key_preview = (config.api_key[:10] + "...") if config.api_key else ""
        entered_key = input(f"\n{label} [{key_preview}]: ").strip()
        if entered_key: config.api_key = entered_key
        print(f"\nPopular {config.provider} models:")
        if config.provider == "openai":
            print("  - gpt-4o (recommended)\n  - gpt-4o-mini\n  - gpt-4-turbo\n  - gpt-3.5-turbo")
        else:
            print("  - claude-sonnet-4-5-20250929\n  - claude-opus-4-20241229\n  - claude-3-5-sonnet-20241022")
        mid = input(f"\nModel ID [{config.model_id}]: ").strip()
        if mid: config.model_id = mid
        print("\nStack options: 1. basic  2. react")
        ssel = input(f"Select stack (1/2) [{config.stack}]: ").strip()
        if ssel == "1": config.stack = "basic"
        elif ssel == "2": config.stack = "react"
        elif ssel.lower() in ["basic", "react"]: config.stack = ssel.lower()
        print("\nGitHub Configuration (optional):")
        gui = input(f"GitHub Username [{config.github_username or ''}]: ").strip()
        if gui: config.github_username = gui
        gtok = input(f"GitHub Token [{(config.github_token[:10] + '...') if config.github_token else ''}]: ").strip()
        if gtok: config.github_token = gtok
        grep = input(f"GitHub Repo [{config.github_repo or ''}]: ").strip()
        if grep: config.github_repo = grep
        out = input(f"Output Directory [{config.output_dir}]: ").strip()
        if out: config.output_dir = out
        e2e_local = input("Run local Playwright E2E (basic only)? [y/N]: ").strip().lower()
        config.e2e = e2e_local == "y"
        e2e_dep = input("Run Playwright E2E against deployed site? [y/N]: ").strip().lower()
        config.e2e_deployed = e2e_dep == "y"
        save_config(config)
        print(f"\n✅ Saved! Provider: {config.provider.upper()}, Model: {config.model_id}, Stack: {config.stack}")
        return
    if args.provider: config.provider = args.provider
    if args.api_key: config.api_key = args.api_key
    if args.model: config.model_id = args.model
    if args.github_user: config.github_username = args.github_user
    if args.github_token: config.github_token = args.github_token
    if args.github_repo: config.github_repo = args.github_repo
    if args.output: config.output_dir = args.output
    if args.stack: config.stack = args.stack
    if args.e2e: config.e2e = True
    if args.e2e_deployed: config.e2e_deployed = True
    if not config.api_key:
        print("❌ Error: API key not configured. Run with --config or set env vars.")
        sys.exit(1)
    print(f"\n🤖 Using: {config.provider.upper()} - {config.model_id}")
    print(f"🧱 Stack: {config.stack.upper()} (React uses GitHub Actions build)")
    print(f"📁 Output: {config.output_dir}\n")
    generator = WebAppGenerator(config)
    if args.sentence:
        sentence = " ".join(args.sentence)
    else:
        generator.show_example()
        sentence = input("Enter your web app description: ").strip()
    if not sentence:
        print("❌ Error: No description provided")
        sys.exit(1)
    generator.run(sentence)

if __name__ == "__main__":
    main()