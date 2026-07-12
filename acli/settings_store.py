"""Persistent JSON settings for DevOrbit."""
import copy
import json
import sys
from pathlib import Path

BASE_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "settings.json"

DEFAULTS = {
    "account": {
        "telemetry": False,
        "marketing_emails": False,
        "display_email": "",
        "plan_label": "NVIDIA NIM API",
    },
    "permissions": {
        "auto_approve": False,
        "workspace_dir": "./workspace",
        "allow_file_reads": True,
        "allow_file_writes": True,
        "denied_file_patterns": [".env", "*.pem", "*.key", "*credentials*"],
        "network_default": "allow",
        "allowed_domains": [],
        "denied_domains": [],
        "terminal_policy": "isolated_only",
        "sandbox_backend": "auto",
        "allow_native_terminal": False,
        "allow_outside_workspace": False,
        "mcp_tools_enabled": True,
    },
    "appearance": {
        "verbose_agent_chat": True,
        "conversation_width": "default",
        "theme": "dark",
        "light_background": "#EEEEEE",
        "light_foreground": "#101010",
        "light_accent": "#007ACC",
        "dark_background": "#101010",
        "dark_foreground": "#E6E6E6",
        "dark_accent": "#4F8FEF",
    },
    "models": {
        "provider": "nvidia",
        "primary_model": "z-ai/glm-5.2",
        "auto_route": True,
        "response_cache": True,
        "temperature": 0.4,
        "context_tokens": 6000,
        "retries_per_model": 2,
        "backoff_seconds": 1.5,
        "max_tool_iterations": 8,
    },
    "customizations": {
        "system_prompt": "",
        "enabled_skills": [],
        "mcp_servers": [],
        "custom_rules": [],
    },
    "browser": {
        "headless": False,
        "javascript_policy": "ask",
        "confirm_actuation": True,
        "allowed_domains": [],
        "denied_domains": [],
        "download_dir": "./workspace/downloads",
    },
    "app": {
        "prevent_sleep": True,
        "keep_in_background": False,
        "notifications": True,
        "check_updates": True,
    },
    "conversations": {
        "autosave": True,
        "history_dir": "./conversations",
        "max_saved": 100,
        "save_tool_results": True,
    },
}


def _deep_merge(base, override):
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else SETTINGS_PATH
        self.data = copy.deepcopy(DEFAULTS)
        self.load()

    def load(self):
        if self.path.exists():
            try:
                user_data = json.loads(self.path.read_text(encoding="utf-8"))
                self.data = _deep_merge(DEFAULTS, user_data)
            except (OSError, json.JSONDecodeError) as exc:
                backup = self.path.with_suffix(".json.bak")
                try:
                    self.path.replace(backup)
                except OSError:
                    pass
                self.data = copy.deepcopy(DEFAULTS)
                print("[settings] Invalid settings file moved to " + str(backup) + ": " + str(exc))
        return self.data

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf-8")
        temp.replace(self.path)

    def get(self, dotted_path, default=None):
        current = self.data
        for part in dotted_path.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def set(self, dotted_path, value):
        parts = dotted_path.split(".")
        current = self.data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        self.save()

    def reset(self, section=None):
        if section:
            if section not in DEFAULTS:
                raise KeyError("Unknown settings section: " + section)
            self.data[section] = copy.deepcopy(DEFAULTS[section])
        else:
            self.data = copy.deepcopy(DEFAULTS)
        self.save()

    def export(self):
        return copy.deepcopy(self.data)
