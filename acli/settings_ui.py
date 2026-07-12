"""Interactive terminal Settings Center and slash-command helpers."""
import json

from acli.settings_store import DEFAULTS

FIELDS = {
    "account": [
        ("telemetry", "Enable telemetry", "bool"),
        ("marketing_emails", "Marketing emails", "bool"),
        ("display_email", "Display email", "str"),
        ("plan_label", "Plan label", "str"),
    ],
    "permissions": [
        ("auto_approve", "Auto-approve mutating actions", "bool"),
        ("workspace_dir", "Workspace directory", "str"),
        ("allow_file_reads", "Allow file reads", "bool"),
        ("allow_file_writes", "Allow file writes/edits", "bool"),
        ("denied_file_patterns", "Denied file patterns", "list"),
        ("network_default", "Network default: allow/deny", "str"),
        ("allowed_domains", "Allowed network domains", "list"),
        ("denied_domains", "Denied network domains", "list"),
        ("terminal_policy", "Terminal policy", "str"),
        ("sandbox_backend", "Sandbox backend: auto/docker/native_restricted", "str"),
        ("allow_native_terminal", "Allow native terminal fallback", "bool"),
        ("allow_outside_workspace", "Commands outside workspace", "bool"),
        ("mcp_tools_enabled", "MCP tools enabled", "bool"),
    ],
    "appearance": [
        ("verbose_agent_chat", "Verbose agent steps", "bool"),
        ("conversation_width", "Conversation width", "str"),
        ("theme", "Theme: dark/light/system", "str"),
        ("light_background", "Light background", "str"),
        ("light_foreground", "Light foreground", "str"),
        ("light_accent", "Light accent", "str"),
        ("dark_background", "Dark background", "str"),
        ("dark_foreground", "Dark foreground", "str"),
        ("dark_accent", "Dark accent", "str"),
    ],
    "models": [
        ("provider", "AI provider", "str"),
        ("primary_model", "Primary model", "str"),
        ("auto_route", "Automatic task routing", "bool"),
        ("response_cache", "Response cache", "bool"),
        ("temperature", "Temperature", "float"),
        ("context_tokens", "Context token budget", "int"),
        ("retries_per_model", "Retries per model", "int"),
        ("backoff_seconds", "Retry backoff seconds", "float"),
        ("max_tool_iterations", "Maximum tool iterations", "int"),
    ],
    "customizations": [
        ("system_prompt", "Custom system prompt", "str"),
        ("enabled_skills", "Enabled skills", "list"),
        ("mcp_servers", "Installed MCP server commands", "list"),
        ("custom_rules", "Custom agent rules", "list"),
    ],
    "browser": [
        ("headless", "Headless browser", "bool"),
        ("javascript_policy", "JavaScript policy: ask/allow/deny", "str"),
        ("confirm_actuation", "Confirm clicks/typing/keys", "bool"),
        ("allowed_domains", "Allowed actuation domains", "list"),
        ("denied_domains", "Denied actuation domains", "list"),
        ("download_dir", "Download/screenshot directory", "str"),
    ],
    "app": [
        ("prevent_sleep", "Prevent sleep while running", "bool"),
        ("keep_in_background", "Keep process in background", "bool"),
        ("notifications", "Terminal notifications", "bool"),
        ("check_updates", "Check for updates", "bool"),
    ],
    "conversations": [
        ("autosave", "Autosave conversations", "bool"),
        ("history_dir", "Conversation history directory", "str"),
        ("max_saved", "Maximum saved conversations", "int"),
        ("save_tool_results", "Save tool results", "bool"),
    ],
}


def parse_value(raw, value_type):
    raw = raw.strip()
    if value_type == "bool":
        if raw.lower() in ("true", "yes", "y", "1", "on"):
            return True
        if raw.lower() in ("false", "no", "n", "0", "off"):
            return False
        raise ValueError("Enter true or false")
    if value_type == "int":
        return int(raw)
    if value_type == "float":
        return float(raw)
    if value_type == "list":
        if not raw:
            return []
        if raw.startswith("["):
            value = json.loads(raw)
            if not isinstance(value, list):
                raise ValueError("Expected a JSON list")
            return value
        return [item.strip() for item in raw.split(",") if item.strip()]
    return raw


def infer_type(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    return "str"


def format_value(value):
    if isinstance(value, list):
        return ", ".join(str(x) for x in value) if value else "(none)"
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if value == "":
        return "(empty)"
    return str(value)


def show_all(store):
    print("\nDevOrbit Settings (" + str(store.path) + ")")
    for section in FIELDS:
        print("\n[" + section.upper() + "]")
        for key, label, _ in FIELDS[section]:
            print("  " + label + ": " + format_value(store.get(section + "." + key)))


def run_settings_center(store):
    sections = list(FIELDS)
    while True:
        print("\n=== SETTINGS CENTER ===")
        for index, section in enumerate(sections, 1):
            print(str(index) + ". " + section.title())
        print("S. Show all   R. Reset all   Q. Return to chat")
        choice = input("settings> ").strip().lower()
        if choice in ("q", "quit", "back", ""):
            return
        if choice == "s":
            show_all(store)
            continue
        if choice == "r":
            confirm = input("Reset every setting to defaults? [y/N] ").strip().lower()
            if confirm in ("y", "yes"):
                store.reset()
                print("All settings reset.")
            continue
        try:
            section = sections[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            continue
        edit_section(store, section)


def edit_section(store, section):
    fields = FIELDS[section]
    while True:
        print("\n--- " + section.upper() + " ---")
        for index, (key, label, _) in enumerate(fields, 1):
            print(str(index) + ". " + label + ": " + format_value(store.get(section + "." + key)))
        print("R. Reset section   B. Back")
        choice = input(section + "> ").strip().lower()
        if choice in ("b", "back", ""):
            return
        if choice == "r":
            store.reset(section)
            print(section.title() + " settings reset.")
            continue
        try:
            key, label, value_type = fields[int(choice) - 1]
        except (ValueError, IndexError):
            print("Invalid selection.")
            continue
        old = store.get(section + "." + key)
        print("Current: " + format_value(old))
        raw = input("New value (comma-separated for lists): ")
        try:
            value = parse_value(raw, value_type)
            store.set(section + "." + key, value)
            print(label + " updated to " + format_value(value))
        except (ValueError, json.JSONDecodeError) as exc:
            print("Invalid value: " + str(exc))


def handle_settings_command(store, arg):
    parts = arg.strip().split(" ", 2) if arg else []
    if not parts:
        run_settings_center(store)
        return "changed"
    command = parts[0].lower()
    if command == "show":
        show_all(store)
        return "unchanged"
    if command == "reset":
        section = parts[1] if len(parts) > 1 else None
        store.reset(section)
        print("Reset " + (section or "all settings") + ".")
        return "changed"
    if command == "set" and len(parts) == 3:
        path, raw = parts[1], parts[2]
        old = store.get(path, None)
        if old is None:
            raise ValueError("Unknown setting: " + path)
        value = parse_value(raw, infer_type(old))
        store.set(path, value)
        print(path + " = " + format_value(value))
        return "changed"
    print("Usage: /settings | /settings show | /settings set section.key value | /settings reset [section]")
    return "unchanged"
