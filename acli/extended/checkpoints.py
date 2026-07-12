"""Workspace checkpoints and rollback without copying credential files."""
import fnmatch
import json
import shutil
import time
from pathlib import Path

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".devorbit-checkpoints"}
SENSITIVE_PATTERNS = {".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "*credentials*", "*secret*", "*.sqlite-wal", "*.sqlite-shm"}


def _dir(workspace):
    path = Path(workspace) / ".devorbit-checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sensitive(relative: Path) -> bool:
    text = str(relative).replace("\\", "/").lower()
    name = relative.name.lower()
    return any(fnmatch.fnmatch(text, pattern.lower()) or fnmatch.fnmatch(name, pattern.lower()) for pattern in SENSITIVE_PATTERNS)


def create_checkpoint(workspace: str, label: str = "checkpoint") -> str:
    safe_label = "".join(char for char in label if char.isalnum() or char in "-_ ")[:30].strip().replace(" ", "-") or "checkpoint"
    stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + str(time.time_ns())[-6:] + "-" + safe_label
    target = _dir(workspace) / stamp
    target.mkdir()
    root = Path(workspace).resolve()
    copied = []
    skipped_sensitive = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root)
        if _sensitive(relative):
            skipped_sensitive.append(str(relative))
            continue
        output = target / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, output)
        copied.append(str(relative))
    (target / "checkpoint.json").write_text(
        json.dumps({"label": label, "created": time.time(), "files": copied, "skipped_sensitive": skipped_sensitive}, indent=2),
        encoding="utf-8",
    )
    return "Created checkpoint " + stamp + " (" + str(len(copied)) + " files; " + str(len(skipped_sensitive)) + " sensitive files skipped)"


def list_checkpoints(workspace: str) -> str:
    items = sorted([path.name for path in _dir(workspace).iterdir() if path.is_dir()], reverse=True)
    return "\n".join(items) if items else "No checkpoints."


def restore_checkpoint(workspace: str, name: str) -> str:
    base = _dir(workspace).resolve()
    source = (base / name).resolve()
    if base not in source.parents or not source.exists() or not source.is_dir():
        raise FileNotFoundError("Checkpoint not found: " + name)
    root = Path(workspace).resolve()
    restored = 0
    for path in source.rglob("*"):
        if path.is_file() and path.name != "checkpoint.json":
            relative = path.relative_to(source)
            output = root / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, output)
            restored += 1
    return "Restored checkpoint " + name + " (" + str(restored) + " files)"
