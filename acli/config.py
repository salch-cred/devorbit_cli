"""Configuration loading: .env, persistent settings.json, and models.json."""
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from acli.settings_store import SettingsStore

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
DEFAULT_SYSTEM_PROMPT = (
    "You are DevOrbit, a concise, helpful terminal AI coding assistant. "
    "You can read/write/edit files, use git/GitHub, search the public web, fetch pages, "
    "and control a persistent Chromium browser using your tools. Prefer web_search and "
    "fetch_web_page for research; use browser tools for interactive or JavaScript pages. "
    "Use run_isolated for terminal work; it selects Docker when available and restricted native execution otherwise. Never request unrestricted run_terminal unless settings explicitly allow it. "
    "Always explain what you are about to do before changing files, GitHub, or browser state. "
    "Answer clearly and use short code blocks when showing code."
)


def load_env() -> None:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()


def resolve_local_path(value: str) -> str:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path.resolve())


def load_model_chain(path: str = None) -> List[str]:
    models_path = Path(path) if path else BASE_DIR / "models.json"
    if not models_path.exists():
        return ["z-ai/glm-5.2"]
    with open(models_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    names = [entry["name"] for entry in data if entry.get("name")]
    if not names:
        raise ValueError("models.json contains no valid model entries")
    return names


@dataclass
class Settings:
    store: SettingsStore = field(default_factory=SettingsStore)
    api_key: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    github_token: str = ""
    github_repo: str = ""
    workspace_dir: str = ""
    auto_approve: bool = False
    allow_file_reads: bool = True
    allow_file_writes: bool = True
    denied_file_patterns: list = field(default_factory=list)
    network_default: str = "allow"
    allowed_domains: list = field(default_factory=list)
    denied_domains: list = field(default_factory=list)
    terminal_policy: str = "isolated_only"
    sandbox_backend: str = "auto"
    allow_native_terminal: bool = False
    allow_outside_workspace: bool = False
    mcp_tools_enabled: bool = True
    verbose_agent_chat: bool = True
    theme: str = "dark"
    conversation_width: str = "default"
    provider: str = "nvidia"
    primary_model: str = "z-ai/glm-5.2"
    auto_route: bool = True
    response_cache: bool = True
    temperature: float = 0.4
    max_retries_per_model: int = 2
    backoff_base_seconds: float = 1.5
    max_context_tokens: int = 6000
    max_tool_iterations: int = 8
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    browser_headless: bool = False
    browser_javascript_policy: str = "ask"
    browser_confirm_actuation: bool = True
    browser_allowed_domains: list = field(default_factory=list)
    browser_denied_domains: list = field(default_factory=list)
    browser_download_dir: str = ""
    prevent_sleep: bool = True
    keep_in_background: bool = False
    notifications: bool = True
    autosave_conversations: bool = True
    history_dir: str = ""
    max_saved_conversations: int = 100
    save_tool_results: bool = True


def apply_store(settings: Settings) -> Settings:
    s = settings.store
    settings.workspace_dir = resolve_local_path(os.environ.get("WORKSPACE_DIR", s.get("permissions.workspace_dir", "./workspace")))
    env_auto = os.environ.get("AUTO_APPROVE")
    settings.auto_approve = (env_auto.strip().lower() == "true") if env_auto is not None else bool(s.get("permissions.auto_approve", False))
    settings.allow_file_reads = bool(s.get("permissions.allow_file_reads", True))
    settings.allow_file_writes = bool(s.get("permissions.allow_file_writes", True))
    settings.denied_file_patterns = list(s.get("permissions.denied_file_patterns", []))
    settings.network_default = str(s.get("permissions.network_default", "allow")).lower()
    settings.allowed_domains = list(s.get("permissions.allowed_domains", []))
    settings.denied_domains = list(s.get("permissions.denied_domains", []))
    settings.terminal_policy = str(s.get("permissions.terminal_policy", "isolated_only"))
    settings.sandbox_backend = str(s.get("permissions.sandbox_backend", "auto")).lower()
    settings.allow_native_terminal = bool(s.get("permissions.allow_native_terminal", False))
    settings.allow_outside_workspace = bool(s.get("permissions.allow_outside_workspace", False))
    settings.mcp_tools_enabled = bool(s.get("permissions.mcp_tools_enabled", True))
    settings.verbose_agent_chat = bool(s.get("appearance.verbose_agent_chat", True))
    settings.theme = str(s.get("appearance.theme", "dark"))
    settings.conversation_width = str(s.get("appearance.conversation_width", "default"))
    settings.provider = str(s.get("models.provider", "nvidia")).lower()
    settings.primary_model = str(s.get("models.primary_model", "z-ai/glm-5.2"))
    settings.auto_route = bool(s.get("models.auto_route", True))
    settings.response_cache = bool(s.get("models.response_cache", True))
    settings.temperature = max(0.0, min(2.0, float(s.get("models.temperature", 0.4))))
    settings.max_context_tokens = max(512, int(s.get("models.context_tokens", 6000)))
    settings.max_retries_per_model = max(1, int(s.get("models.retries_per_model", 2)))
    settings.backoff_base_seconds = max(0.0, float(s.get("models.backoff_seconds", 1.5)))
    settings.max_tool_iterations = max(1, min(32, int(s.get("models.max_tool_iterations", 8))))
    custom_prompt = str(s.get("customizations.system_prompt", "")).strip()
    rules = s.get("customizations.custom_rules", [])
    settings.system_prompt = custom_prompt or DEFAULT_SYSTEM_PROMPT
    if rules:
        settings.system_prompt += "\n\nCustom rules:\n- " + "\n- ".join(str(r) for r in rules)
    settings.browser_headless = bool(s.get("browser.headless", False))
    settings.browser_javascript_policy = str(s.get("browser.javascript_policy", "ask")).lower()
    settings.browser_confirm_actuation = bool(s.get("browser.confirm_actuation", True))
    settings.browser_allowed_domains = list(s.get("browser.allowed_domains", []))
    settings.browser_denied_domains = list(s.get("browser.denied_domains", []))
    requested_download_dir = Path(resolve_local_path(s.get("browser.download_dir", "./workspace/downloads")))
    workspace_path = Path(settings.workspace_dir).resolve()
    if requested_download_dir != workspace_path and workspace_path not in requested_download_dir.parents:
        requested_download_dir = workspace_path / "downloads"
    settings.browser_download_dir = str(requested_download_dir)
    settings.prevent_sleep = bool(s.get("app.prevent_sleep", True))
    settings.keep_in_background = bool(s.get("app.keep_in_background", False))
    settings.notifications = bool(s.get("app.notifications", True))
    settings.autosave_conversations = bool(s.get("conversations.autosave", True))
    settings.history_dir = resolve_local_path(s.get("conversations.history_dir", "./conversations"))
    settings.max_saved_conversations = max(1, int(s.get("conversations.max_saved", 100)))
    settings.save_tool_results = bool(s.get("conversations.save_tool_results", True))
    return settings


def load_settings() -> Settings:
    load_env()
    settings = Settings()
    settings.api_key = os.environ.get("NVIDIA_API_KEY", "")
    settings.base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    settings.github_token = os.environ.get("GITHUB_TOKEN", "")
    settings.github_repo = os.environ.get("GITHUB_REPO", "")
    return apply_store(settings)
