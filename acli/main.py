"""DevOrbit entry point and persistent settings integration."""
import argparse
import getpass
import os
import sys

from acli.config import apply_store, load_model_chain, load_settings
from acli.loop_engine import LoopEngine, LoopExhaustedError
from acli.settings_ui import handle_settings_command
from acli.settings_store import BASE_DIR
from acli.extended.providers import get_provider, provider_status
from acli.extended.dashboard import show_dashboard
from acli.extended.orchestrator import run_team
from acli.extended.project import build_index
from acli.extended.voice import speak
from acli.extended import dev_rescue
from acli.production import credentials
from acli.tools.registry import TOOL_SCHEMAS
from acli.tools.browser_tools import configure_browser, SESSION as BROWSER_SESSION

HELP_TEXT = (
    "Commands: /dashboard  /doctor  /diagnose <error>  /processes  /credential  /settings  /team <task>  /index  /providers  /speak <text>  "
    "/model <name>  /models  /tools  /reflect  /reset  /approve  /help  /exit"
)


def make_confirm_callback(auto_approve_holder, settings):
    def confirm(description):
        if auto_approve_holder["value"]:
            print("[auto-approved] " + description)
            return True
        try:
            answer = input("Approve: " + description + "? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")
    return confirm


def refresh_runtime(engine):
    """Apply settings.json changes to the live engine without restarting."""
    settings = apply_store(engine.settings)
    if engine._cli_workspace:
        settings.workspace_dir = engine._cli_workspace
    if engine._cli_auto_approve:
        settings.auto_approve = True
    headless = settings.browser_headless if engine._cli_headless is None else engine._cli_headless
    os.makedirs(settings.workspace_dir, exist_ok=True)
    os.makedirs(settings.history_dir, exist_ok=True)
    os.makedirs(settings.browser_download_dir, exist_ok=True)
    BROWSER_SESSION.close()
    configure_browser(headless=headless, download_dir=settings.browser_download_dir, settings=settings)
    chain = load_model_chain()
    primary = settings.primary_model
    engine.model_chain = [primary] + [m for m in chain if m != primary]
    engine._auto_approve_holder["value"] = settings.auto_approve
    engine._browser_headless = headless
    engine.messages[0]["content"] = settings.system_prompt
    if not engine._mock and engine._provider_name != settings.provider:
        from acli.client import NvidiaClient
        base_url, api_key = get_provider(str(BASE_DIR), settings.provider)
        engine.client = NvidiaClient(api_key=api_key, base_url=base_url)
        engine._provider_name = settings.provider


def build_engine(args):
    settings = load_settings()
    cli_workspace = args.workspace
    cli_auto_approve = bool(args.auto_approve)
    cli_headless = args.headless
    if cli_workspace:
        settings.workspace_dir = cli_workspace
    if cli_auto_approve:
        settings.auto_approve = True
    headless = settings.browser_headless if cli_headless is None else cli_headless
    os.makedirs(settings.workspace_dir, exist_ok=True)
    os.makedirs(settings.history_dir, exist_ok=True)
    os.makedirs(settings.browser_download_dir, exist_ok=True)
    configure_browser(headless=headless, download_dir=settings.browser_download_dir, settings=settings)

    chain = load_model_chain()
    model_chain = [settings.primary_model] + [m for m in chain if m != settings.primary_model]
    if args.mock:
        from acli.mock_client import MockClient
        client = MockClient()
    else:
        from acli.client import NvidiaClient
        base_url, api_key = get_provider(str(BASE_DIR), settings.provider)
        client = NvidiaClient(api_key=api_key, base_url=base_url)

    auto_holder = {"value": settings.auto_approve}
    engine = LoopEngine(
        client=client,
        model_chain=model_chain,
        settings=settings,
        confirm_callback=make_confirm_callback(auto_holder, settings),
        enable_tools=not args.no_tools,
    )
    engine._auto_approve_holder = auto_holder
    engine._browser_headless = headless
    engine._cli_workspace = cli_workspace
    engine._cli_auto_approve = cli_auto_approve
    engine._cli_headless = cli_headless
    engine._mock = bool(args.mock)
    engine._provider_name = settings.provider
    return engine


def run_repl(engine: LoopEngine) -> None:
    print("DevOrbit -- type a message, or /help for commands.")
    print("Provider: " + engine.settings.provider + " | Primary model: " + engine.model_chain[0])
    print("Workspace: " + engine.settings.workspace_dir)
    print("Tools: " + str(engine.enable_tools) + " | Browser: " + ("headless" if engine._browser_headless else "visible"))
    print("Open the Settings Center with /settings")

    while True:
        try:
            user_text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            return
        if not user_text:
            continue

        if user_text.startswith("/"):
            parts = user_text.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""
            if cmd in ("/exit", "/quit"):
                print("bye.")
                return
            if cmd == "/help":
                print(HELP_TEXT)
                print("Settings: /settings show | /settings set section.key value | /settings reset [section]")
                continue
            if cmd == "/dashboard":
                show_dashboard(engine)
                continue
            if cmd == "/doctor":
                print(dev_rescue.project_doctor(engine.settings.workspace_dir))
                continue
            if cmd == "/diagnose":
                if not arg:
                    print("Usage: /diagnose <error text or stack trace>")
                else:
                    print(dev_rescue.diagnose_error(arg))
                continue
            if cmd == "/processes":
                print(dev_rescue.list_dev_processes())
                continue
            if cmd == "/credential":
                pieces=arg.split(" ",1) if arg else []
                if len(pieces)!=2 or pieces[0] not in ("set","status","delete"):
                    print("Usage: /credential set|status|delete ENV_NAME")
                    continue
                action,name=pieces
                try:
                    if action=="set": print(credentials.set_secret(name,getpass.getpass("Secret value (hidden): ")))
                    elif action=="status": print(credentials.secret_status(name))
                    else:
                        answer=input("Delete "+name+" from OS keychain? [y/N] ").strip().lower()
                        print(credentials.delete_secret(name) if answer in ("y","yes") else "Cancelled.")
                except Exception as exc: print("[credential error] "+str(exc))
                continue
            if cmd == "/providers":
                print(provider_status(str(BASE_DIR)))
                continue
            if cmd == "/team":
                if not arg:
                    print("Usage: /team <task>")
                    continue
                try:
                    run_team(engine, arg)
                except LoopExhaustedError as exc:
                    print("[team error] " + str(exc))
                continue
            if cmd == "/index":
                print(build_index(engine.settings.workspace_dir))
                continue
            if cmd == "/speak":
                if not arg:
                    print("Usage: /speak <text>")
                else:
                    print(speak(arg))
                continue
            if cmd == "/settings":
                try:
                    changed = handle_settings_command(engine.settings.store, arg)
                    if changed == "changed":
                        refresh_runtime(engine)
                        print("Settings applied to this session.")
                except (ValueError, KeyError) as exc:
                    print("[settings error] " + str(exc))
                continue
            if cmd == "/models":
                print("Chain: " + " -> ".join(engine.model_chain))
                print("Last used: " + str(engine.last_model_used))
                continue
            if cmd == "/tools":
                if not engine.enable_tools:
                    print("Tools are disabled for this session (started with --no-tools).")
                else:
                    for schema in TOOL_SCHEMAS:
                        fn = schema["function"]
                        print("- " + fn["name"] + ": " + fn["description"])
                continue
            if cmd == "/model":
                if not arg:
                    print("Usage: /model <name>")
                    continue
                engine.settings.store.set("models.primary_model", arg)
                refresh_runtime(engine)
                print("Primary model saved as '" + arg + "'.")
                continue
            if cmd == "/system":
                if not arg:
                    print("Usage: /system <new system prompt>")
                    continue
                engine.settings.store.set("customizations.system_prompt", arg)
                refresh_runtime(engine)
                print("System prompt saved and applied.")
                continue
            if cmd == "/reflect":
                try:
                    engine.reflect()
                except LoopExhaustedError as exc:
                    print("[error] " + str(exc))
                continue
            if cmd == "/reset":
                engine.reset()
                print("Conversation cleared.")
                continue
            if cmd == "/approve":
                value = not engine._auto_approve_holder["value"]
                engine.settings.store.set("permissions.auto_approve", value)
                refresh_runtime(engine)
                print("Auto-approve mutating actions is now " + str(value))
                continue
            if cmd == "/save":
                if not arg:
                    print("Usage: /save <file.json>")
                    continue
                engine.save(arg)
                print("Saved to " + arg)
                continue
            if cmd == "/load":
                if not arg:
                    print("Usage: /load <file.json>")
                    continue
                try:
                    engine.load(arg)
                    print("Loaded " + arg)
                except FileNotFoundError as exc:
                    print("[error] " + str(exc))
                continue
            print("Unknown command. " + HELP_TEXT)
            continue

        try:
            engine.send(user_text)
        except LoopExhaustedError as exc:
            print("[error] " + str(exc))


def main() -> None:
    parser = argparse.ArgumentParser(prog="devorbit", description="DevOrbit")
    parser.add_argument("--mock", action="store_true", help="Offline loop-engine demo")
    parser.add_argument("--no-tools", action="store_true", help="Disable agent tools")
    parser.add_argument("--workspace", default=None, help="Override workspace directory for this run")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve mutating actions for this run")
    browser_group = parser.add_mutually_exclusive_group()
    browser_group.add_argument("--headless", dest="headless", action="store_true", help="Hide browser")
    browser_group.add_argument("--visible", dest="headless", action="store_false", help="Force visible browser")
    parser.set_defaults(headless=None)
    args = parser.parse_args()
    try:
        engine = build_engine(args)
    except Exception as exc:
        print("[fatal] " + str(exc))
        sys.exit(1)
    try:
        run_repl(engine)
    finally:
        dev_rescue.stop_all_dev_processes()
        BROWSER_SESSION.close()


if __name__ == "__main__":
    main()
