export function focusOnElement(selector: string) {
  const element = document.querySelector(selector) as HTMLElement | null;
  if (element) {
    element.focus();
  }
}