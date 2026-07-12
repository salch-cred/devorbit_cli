"""Persistent Playwright browser automation with settings-backed permissions."""
import json
from pathlib import Path

from acli.tools.policy import ensure_network_allowed


class ToolError(Exception):
    pass


class BrowserSession:
    def __init__(self):
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._headless = False
        self._download_dir = None
        self._settings = None

    def configure(self, headless: bool, download_dir: str, settings=None) -> None:
        changed = self._browser is not None and self._headless != bool(headless)
        if changed:
            self.close()
        self._headless = bool(headless)
        requested = Path(download_dir).resolve()
        if settings is not None and getattr(settings, "workspace_dir", None):
            workspace = Path(settings.workspace_dir).resolve()
            if requested != workspace and workspace not in requested.parents:
                raise ToolError("Browser download directory must stay inside the workspace")
        self._download_dir = str(requested)
        self._settings = settings
        Path(self._download_dir).mkdir(parents=True, exist_ok=True)

    def _ensure(self):
        if self._page and not self._page.is_closed():
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise ToolError("Playwright is not installed. Run: pip install -r requirements.txt && playwright install chromium") from exc
        try:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=self._headless)
            self._context = self._browser.new_context(accept_downloads=True)
            self._page = self._context.new_page()
            self._page.set_default_timeout(15000)
            return self._page
        except Exception as exc:
            self.close()
            raise ToolError("Could not start Chromium. Run: playwright install chromium. Details: " + str(exc)) from exc

    def _check_current_actuation(self):
        page = self._ensure()
        if self._settings:
            ensure_network_allowed(page.url, self._settings, browser_actuation=True)
        return page

    def close(self):
        for obj, method in ((self._context, "close"), (self._browser, "close")):
            if obj:
                try:
                    getattr(obj, method)()
                except Exception:
                    pass
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
        self._playwright = self._browser = self._context = self._page = None

    def navigate(self, url: str) -> str:
        if not url.startswith(("http://", "https://")):
            raise ToolError("Only http:// and https:// URLs are allowed")
        if self._settings:
            ensure_network_allowed(url, self._settings)
        page = self._ensure()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        return "Opened " + page.url + "\nTitle: " + page.title()

    def inspect(self, max_chars: int = 12000) -> str:
        page = self._ensure()
        data = page.locator("body").inner_text(timeout=15000)
        links = page.locator("a").all()
        link_lines = []
        for i, link in enumerate(links[:60]):
            try:
                text = link.inner_text().strip()
                href = link.get_attribute("href") or ""
                if text or href:
                    link_lines.append("[link " + str(i) + "] " + text[:120] + " -> " + href)
            except Exception:
                pass
        output = "URL: " + page.url + "\nTitle: " + page.title() + "\n\nPAGE TEXT:\n" + data
        if link_lines:
            output += "\n\nLINKS:\n" + "\n".join(link_lines)
        return output[:max_chars] + ("\n...[truncated]" if len(output) > max_chars else "")

    def click(self, selector: str) -> str:
        page = self._check_current_actuation()
        page.locator(selector).first.click()
        page.wait_for_timeout(500)
        return "Clicked " + selector + "\nCurrent URL: " + page.url

    def type_text(self, selector: str, text: str, clear: bool = True) -> str:
        page = self._check_current_actuation()
        locator = page.locator(selector).first
        locator.fill(text) if clear else locator.type(text)
        return "Typed into " + selector + " (" + str(len(text)) + " characters)"

    def press(self, selector: str, key: str) -> str:
        page = self._check_current_actuation()
        page.locator(selector).first.press(key)
        page.wait_for_timeout(500)
        return "Pressed " + key + " on " + selector + "\nCurrent URL: " + page.url

    def evaluate(self, script: str) -> str:
        policy = getattr(self._settings, "browser_javascript_policy", "ask") if self._settings else "ask"
        if policy == "deny":
            raise ToolError("Browser JavaScript execution is denied in Settings > Browser")
        page = self._check_current_actuation()
        result = page.evaluate(script)
        try:
            return json.dumps(result, ensure_ascii=False)[:12000]
        except TypeError:
            return str(result)[:12000]

    def screenshot(self, path: str, full_page: bool = True) -> str:
        page = self._ensure()
        target = Path(self._download_dir) / Path(path).name
        page.screenshot(path=str(target), full_page=bool(full_page))
        return "Saved screenshot to " + str(target)

    def back(self) -> str:
        page = self._ensure()
        page.go_back(wait_until="domcontentloaded")
        return "Went back to " + page.url


SESSION = BrowserSession()


def configure_browser(headless: bool, download_dir: str, settings=None) -> None:
    SESSION.configure(headless, download_dir, settings=settings)


def browser_navigate(url: str) -> str: return SESSION.navigate(url)
def browser_inspect(max_chars: int = 12000) -> str: return SESSION.inspect(max_chars)
def browser_click(selector: str) -> str: return SESSION.click(selector)
def browser_type(selector: str, text: str, clear: bool = True) -> str: return SESSION.type_text(selector, text, clear)
def browser_press(selector: str, key: str) -> str: return SESSION.press(selector, key)
def browser_evaluate(script: str) -> str: return SESSION.evaluate(script)
def browser_screenshot(path: str = "screenshot.png", full_page: bool = True) -> str: return SESSION.screenshot(path, full_page)
def browser_back() -> str: return SESSION.back()
def browser_close() -> str:
    SESSION.close()
    return "Browser closed"
