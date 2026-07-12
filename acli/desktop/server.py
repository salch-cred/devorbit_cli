"""FastAPI backend wrapping the existing DevOrbit LoopEngine for desktop use."""
import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from acli.config import apply_store, load_model_chain, load_settings
from acli.loop_engine import LoopEngine, LoopExhaustedError
from acli.settings_store import BASE_DIR, SettingsStore
from acli.extended.providers import get_provider, provider_status
from acli.extended.dashboard import show_dashboard
from acli.extended.orchestrator import run_team
from acli.extended.project import build_index, repo_map, search_index
from acli.extended import dev_rescue
from acli.production import credentials
from acli.tools.registry import TOOL_SCHEMAS, MUTATING_TOOLS, describe_call, dispatch
from acli.tools.browser_tools import configure_browser, SESSION as BROWSER_SESSION
from acli.tools import fs_tools

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="DevOrbit Desktop", version="2.1.0")

# ─── Engine Management ────────────────────────────────────────────────

_engine: Optional[LoopEngine] = None
_engine_lock = threading.Lock()
_auto_approve = {"value": False}
_pending_confirmations: Dict[str, dict] = {}
_confirm_results: Dict[str, bool] = {}


def _build_engine(mock: bool = False, workspace: str = None, headless: bool = True):
    """Build a LoopEngine configured for desktop use."""
    settings = load_settings()
    if workspace:
        settings.workspace_dir = workspace
    headless_val = headless if headless is not None else settings.browser_headless
    os.makedirs(settings.workspace_dir, exist_ok=True)
    os.makedirs(settings.history_dir, exist_ok=True)
    os.makedirs(settings.browser_download_dir, exist_ok=True)
    configure_browser(headless=headless_val, download_dir=settings.browser_download_dir, settings=settings)

    chain = load_model_chain()
    model_chain = [settings.primary_model] + [m for m in chain if m != settings.primary_model]

    if mock:
        from acli.mock_client import MockClient
        client = MockClient()
    else:
        from acli.client import MultiKeyNvidiaClient
        from acli.extended.providers import get_nvidia_keys
        keys = get_nvidia_keys()
        if not keys:
            base_url, api_key = get_provider(str(BASE_DIR), settings.provider)
            keys = [api_key]
        else:
            base_url = settings.base_url
        client = MultiKeyNvidiaClient(api_keys=keys, base_url=base_url)

    _auto_approve["value"] = settings.auto_approve

    def confirm_callback(description: str) -> bool:
        import uuid as _uuid
        confirm_id = _uuid.uuid4().hex[:12]
        _pending_confirmations[confirm_id] = {"description": description}
        # Notify via websocket that a confirmation is needed
        # (the WS handler will pick it up)
        import time as _time
        deadline = _time.time() + 120
        while _time.time() < deadline:
            if confirm_id in _confirm_results:
                return _confirm_results.pop(confirm_id)
            _time.sleep(0.3)
        return False

    engine = LoopEngine(
        client=client,
        model_chain=model_chain,
        settings=settings,
        confirm_callback=confirm_callback,
        enable_tools=True,
    )
    engine._auto_approve_holder = _auto_approve
    engine._browser_headless = headless_val
    engine._cli_workspace = workspace
    engine._cli_auto_approve = False
    engine._cli_headless = headless_val
    engine._mock = mock
    engine._provider_name = settings.provider
    return engine


def get_engine() -> LoopEngine:
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = _build_engine(mock=True, headless=True)
        return _engine


def rebuild_engine(mock: bool = None, workspace: str = None, headless: bool = None):
    global _engine
    with _engine_lock:
        if _engine is not None:
            BROWSER_SESSION.close()
        current = _engine
        use_mock = mock if mock is not None else (current._mock if current else True)
        use_workspace = workspace or (current.settings.workspace_dir if current else None)
        use_headless = headless if headless is not None else (current._browser_headless if current else True)
        _engine = _build_engine(mock=use_mock, workspace=use_workspace, headless=use_headless)
    return _engine


def _refresh_runtime(engine: LoopEngine):
    """Apply settings.json changes to the live engine."""
    settings = apply_store(engine.settings)
    if engine._cli_workspace:
        settings.workspace_dir = engine._cli_workspace
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
        from acli.client import MultiKeyNvidiaClient
        from acli.extended.providers import get_nvidia_keys
        keys = get_nvidia_keys()
        if not keys:
            base_url, api_key = get_provider(str(BASE_DIR), settings.provider)
            keys = [api_key]
        else:
            base_url = settings.base_url
        engine.client = MultiKeyNvidiaClient(api_keys=keys, base_url=base_url)
        engine._provider_name = settings.provider


# ─── REST Endpoints ───────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    engine = get_engine()
    status = {
        "provider": engine.settings.provider,
        "primary_model": engine.model_chain[0],
        "last_model": engine.last_model_used,
        "workspace": engine.settings.workspace_dir,
        "browser": "headless" if engine._browser_headless else "visible",
        "tools_enabled": engine.enable_tools,
        "auto_approve": engine._auto_approve_holder["value"],
        "message_count": len(engine.messages),
        "model_count": len(engine.model_chain),
        "mock": engine._mock,
        "models": engine.model_chain,
    }
    # Add key stats if using MultiKeyNvidiaClient
    if hasattr(engine.client, "key_count"):
        status["key_count"] = engine.client.key_count
        status["key_stats"] = engine.client.key_stats()
    return status


@app.get("/api/settings")
async def api_get_settings():
    store = SettingsStore()
    return store.export()


@app.post("/api/settings")
async def api_set_settings(payload: dict):
    store = SettingsStore()
    path = payload.get("path")
    value = payload.get("value")
    if path and value is not None:
        old = store.get(path, None)
        if old is None:
            return JSONResponse({"error": "Unknown setting: " + path}, status_code=400)
        # Infer type
        if isinstance(old, bool):
            value = str(value).lower() in ("true", "1", "yes", "on")
        elif isinstance(old, int):
            value = int(value)
        elif isinstance(old, float):
            value = float(value)
        elif isinstance(old, list):
            if isinstance(value, str):
                value = [v.strip() for v in value.split(",") if v.strip()]
        store.set(path, value)
    # Apply to live engine
    engine = get_engine()
    _refresh_runtime(engine)
    return {"ok": True, "settings": store.export()}


@app.post("/api/settings/reset")
async def api_reset_settings(payload: dict = None):
    store = SettingsStore()
    section = (payload or {}).get("section")
    store.reset(section)
    engine = get_engine()
    _refresh_runtime(engine)
    return {"ok": True}


@app.get("/api/models")
async def api_models():
    engine = get_engine()
    return {
        "chain": engine.model_chain,
        "last_used": engine.last_model_used,
        "primary": engine.model_chain[0],
    }


@app.post("/api/models/set")
async def api_set_model(payload: dict):
    model = payload.get("model")
    if not model:
        return JSONResponse({"error": "model is required"}, status_code=400)
    store = SettingsStore()
    store.set("models.primary_model", model)
    engine = get_engine()
    _refresh_runtime(engine)
    return {"ok": True, "primary": model, "chain": engine.model_chain}


@app.get("/api/providers")
async def api_providers():
    return {"status": provider_status(str(BASE_DIR))}


@app.get("/api/tools")
async def api_tools():
    tools = []
    for schema in TOOL_SCHEMAS:
        fn = schema["function"]
        tools.append({
            "name": fn["name"],
            "description": fn["description"],
            "mutating": fn["name"] in MUTATING_TOOLS,
            "parameters": fn.get("parameters", {}).get("properties", {}),
        })
    return {"tools": tools, "count": len(tools)}


@app.get("/api/keys")
async def api_key_stats():
    """Get NVIDIA API key rotation stats."""
    engine = get_engine()
    if hasattr(engine.client, "key_stats"):
        return {"keys": engine.client.key_stats(), "total": engine.client.key_count}
    return {"keys": [], "total": 0, "error": "Multi-key client not in use"}


@app.post("/api/keys/add")
async def api_add_key(payload: dict):
    """Add a new NVIDIA API key at runtime."""
    key = (payload or {}).get("key", "").strip()
    if not key:
        return JSONResponse({"error": "key is required"}, status_code=400)
    engine = get_engine()
    if hasattr(engine.client, "_keys"):
        if key in engine.client._keys:
            return {"ok": True, "message": "Key already exists", "total": engine.client.key_count}
        from openai import OpenAI
        engine.client._keys.append(key)
        engine.client._clients[key] = OpenAI(api_key=key, base_url=engine.client._base_url)
        engine.client._key_status[key] = {
            "available": True, "cooldown_until": 0,
            "requests": 0, "errors": 0, "last_used": 0,
        }
        return {"ok": True, "message": f"Key added (now {engine.client.key_count} keys)", "total": engine.client.key_count}
    return JSONResponse({"error": "Multi-key client not in use"}, status_code=400)


@app.post("/api/keys/remove")
async def api_remove_key(payload: dict):
    """Remove an NVIDIA API key by index (1-based)."""
    index = (payload or {}).get("index")
    engine = get_engine()
    if hasattr(engine.client, "_keys") and index is not None:
        idx = int(index) - 1
        if 0 <= idx < len(engine.client._keys):
            key = engine.client._keys.pop(idx)
            engine.client._clients.pop(key, None)
            engine.client._key_status.pop(key, None)
            return {"ok": True, "message": f"Key removed (now {engine.client.key_count} keys)", "total": engine.client.key_count}
    return JSONResponse({"error": "Invalid index"}, status_code=400)


@app.get("/api/dashboard")
async def api_dashboard():
    engine = get_engine()
    return {
        "provider": engine.settings.provider,
        "primary_model": engine.model_chain[0],
        "last_model": str(engine.last_model_used or "—"),
        "workspace": engine.settings.workspace_dir,
        "browser": "headless" if engine._browser_headless else "visible",
        "tools": str(engine.enable_tools),
        "auto_approve": str(engine._auto_approve_holder["value"]),
        "messages": len(engine.messages),
        "models": len(engine.model_chain),
        "max_tool_loops": engine.settings.max_tool_iterations,
        "context_budget": engine.settings.max_context_tokens,
        "temperature": engine.settings.temperature,
        "mock": engine._mock,
    }


@app.get("/api/files")
async def api_list_files(path: str = "."):
    engine = get_engine()
    try:
        result = fs_tools.list_files(engine.settings.workspace_dir, path, settings=engine.settings)
        return {"files": result, "path": path}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.get("/api/files/read")
async def api_read_file(path: str):
    engine = get_engine()
    try:
        content = fs_tools.read_file(engine.settings.workspace_dir, path, max_chars=50000, settings=engine.settings)
        return {"path": path, "content": content}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/files/write")
async def api_write_file(payload: dict):
    engine = get_engine()
    try:
        result = fs_tools.write_file(
            engine.settings.workspace_dir, payload["path"], payload["content"], settings=engine.settings
        )
        return {"ok": True, "message": result}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/files/create")
async def api_create_file(payload: dict):
    engine = get_engine()
    try:
        path = payload["path"]
        content = payload.get("content", "")
        result = fs_tools.write_file(
            engine.settings.workspace_dir, path, content, settings=engine.settings
        )
        return {"ok": True, "message": result, "path": path}
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@app.post("/api/chat/reset")
async def api_chat_reset():
    engine = get_engine()
    engine.reset()
    return {"ok": True}


@app.post("/api/chat/reflect")
async def api_chat_reflect():
    engine = get_engine()
    try:
        result = engine.reflect()
        return {"ok": True, "response": result}
    except LoopExhaustedError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/chat/save")
async def api_chat_save(payload: dict):
    engine = get_engine()
    path = payload.get("path", "conversation.json")
    engine.save(path)
    return {"ok": True, "path": path}


@app.post("/api/chat/load")
async def api_chat_load(payload: dict):
    engine = get_engine()
    path = payload.get("path", "conversation.json")
    try:
        engine.load(path)
        return {"ok": True, "messages": engine.messages}
    except FileNotFoundError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)


@app.get("/api/chat/history")
async def api_chat_history():
    engine = get_engine()
    return {"messages": engine.messages}


@app.post("/api/approve/toggle")
async def api_toggle_approve():
    engine = get_engine()
    value = not engine._auto_approve_holder["value"]
    store = SettingsStore()
    store.set("permissions.auto_approve", value)
    _refresh_runtime(engine)
    return {"ok": True, "auto_approve": value}


@app.post("/api/confirm/{confirm_id}")
async def api_confirm(confirm_id: str, payload: dict):
    approved = payload.get("approved", False)
    _confirm_results[confirm_id] = approved
    _pending_confirmations.pop(confirm_id, None)
    return {"ok": True}


@app.get("/api/confirmations")
async def api_confirmations():
    return {"pending": _pending_confirmations}


@app.post("/api/engine/rebuild")
async def api_rebuild_engine(payload: dict = None):
    payload = payload or {}
    mock = payload.get("mock")
    workspace = payload.get("workspace")
    headless = payload.get("headless")
    rebuild_engine(mock=mock, workspace=workspace, headless=headless)
    return {"ok": True}


@app.post("/api/team")
async def api_team(payload: dict):
    engine = get_engine()
    task = payload.get("task", "")
    if not task:
        return JSONResponse({"error": "task is required"}, status_code=400)
    try:
        result = run_team(engine, task)
        return {"ok": True, "result": result}
    except LoopExhaustedError as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@app.post("/api/index")
async def api_build_index():
    engine = get_engine()
    return {"ok": True, "message": build_index(engine.settings.workspace_dir)}


@app.post("/api/doctor")
async def api_doctor():
    engine = get_engine()
    return {"ok": True, "result": dev_rescue.project_doctor(engine.settings.workspace_dir)}


# ─── WebSocket Chat ───────────────────────────────────────────────────

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()
    engine = get_engine()
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "message":
                user_text = data.get("content", "")
                if not user_text.strip():
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                # Handle slash commands
                if user_text.startswith("/"):
                    cmd_parts = user_text.split(" ", 1)
                    cmd = cmd_parts[0].lower()
                    arg = cmd_parts[1].strip() if len(cmd_parts) > 1 else ""

                    if cmd in ("/exit", "/quit"):
                        await websocket.send_json({"type": "system", "message": "Session ended."})
                        break
                    elif cmd == "/reset":
                        engine.reset()
                        await websocket.send_json({"type": "system", "message": "Conversation cleared."})
                    elif cmd == "/models":
                        await websocket.send_json({"type": "system", "message": "Chain: " + " -> ".join(engine.model_chain) + "\nLast used: " + str(engine.last_model_used)})
                    elif cmd == "/tools":
                        tool_list = "\n".join("- " + s["function"]["name"] + ": " + s["function"]["description"] for s in TOOL_SCHEMAS)
                        await websocket.send_json({"type": "system", "message": tool_list})
                    elif cmd == "/approve":
                        value = not engine._auto_approve_holder["value"]
                        store = SettingsStore()
                        store.set("permissions.auto_approve", value)
                        _refresh_runtime(engine)
                        await websocket.send_json({"type": "system", "message": "Auto-approve is now " + str(value)})
                    elif cmd == "/reflect":
                        await websocket.send_json({"type": "status", "message": "Reflecting..."})
                        try:
                            result = await asyncio.get_event_loop().run_in_executor(None, engine.reflect)
                            await websocket.send_json({"type": "response", "content": result})
                        except LoopExhaustedError as exc:
                            await websocket.send_json({"type": "error", "message": str(exc)})
                    elif cmd == "/team":
                        if not arg:
                            await websocket.send_json({"type": "error", "message": "Usage: /team <task>"})
                        else:
                            await websocket.send_json({"type": "status", "message": "Running team task: " + arg})
                            try:
                                result = await asyncio.get_event_loop().run_in_executor(None, run_team, engine, arg)
                                await websocket.send_json({"type": "response", "content": result})
                            except LoopExhaustedError as exc:
                                await websocket.send_json({"type": "error", "message": str(exc)})
                    elif cmd == "/index":
                        await websocket.send_json({"type": "status", "message": "Building index..."})
                        result = build_index(engine.settings.workspace_dir)
                        await websocket.send_json({"type": "system", "message": result})
                    elif cmd == "/dashboard":
                        dash = {
                            "provider": engine.settings.provider,
                            "primary_model": engine.model_chain[0],
                            "workspace": engine.settings.workspace_dir,
                            "messages": len(engine.messages),
                            "models": len(engine.model_chain),
                        }
                        await websocket.send_json({"type": "system", "message": json.dumps(dash, indent=2)})
                    elif cmd == "/providers":
                        result = provider_status(str(BASE_DIR))
                        await websocket.send_json({"type": "system", "message": result})
                    elif cmd == "/model":
                        if arg:
                            store = SettingsStore()
                            store.set("models.primary_model", arg)
                            _refresh_runtime(engine)
                            await websocket.send_json({"type": "system", "message": "Primary model set to " + arg})
                        else:
                            await websocket.send_json({"type": "error", "message": "Usage: /model <name>"})
                    else:
                        await websocket.send_json({"type": "error", "message": "Unknown command: " + cmd})
                    continue

                # Normal message — run engine in executor to avoid blocking
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                try:
                    # Patch the confirm callback to send WS notifications
                    original_confirm = engine.confirm_callback

                    def ws_confirm(description):
                        import uuid as _uuid
                        confirm_id = _uuid.uuid4().hex[:12]
                        _pending_confirmations[confirm_id] = {"description": description}
                        # Send confirmation request via WebSocket (async)
                        asyncio.run_coroutine_threadsafe(
                            websocket.send_json({"type": "confirm", "id": confirm_id, "description": description}),
                            asyncio.get_event_loop()
                        )
                        import time as _time
                        deadline = _time.time() + 120
                        while _time.time() < deadline:
                            if confirm_id in _confirm_results:
                                return _confirm_results.pop(confirm_id)
                            _time.sleep(0.3)
                        return False

                    engine.confirm_callback = ws_confirm

                    result = await asyncio.get_event_loop().run_in_executor(None, engine.send, user_text)
                    engine.confirm_callback = original_confirm
                    await websocket.send_json({"type": "response", "content": result})
                except LoopExhaustedError as exc:
                    engine.confirm_callback = original_confirm
                    await websocket.send_json({"type": "error", "message": str(exc)})
                except Exception as exc:
                    engine.confirm_callback = original_confirm
                    await websocket.send_json({"type": "error", "message": str(exc)})

            elif msg_type == "confirm":
                confirm_id = data.get("id", "")
                approved = data.get("approved", False)
                _confirm_results[confirm_id] = approved

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass


# ─── Serve Static UI ──────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


def run_desktop(host: str = "127.0.0.1", port: int = 8765, mock: bool = False, workspace: str = None, headless: bool = True):
    """Launch the desktop application server."""
    import uvicorn
    # Pre-build engine
    global _engine
    _engine = _build_engine(mock=mock, workspace=workspace, headless=headless)
    print(f"\n  DevOrbit Desktop running at http://{host}:{port}\n  Press Ctrl+C to stop.\n")
    uvicorn.run(app, host=host, port=port, log_level="warning")
