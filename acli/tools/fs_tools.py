"""Filesystem tools scoped to the configured workspace directory and permission settings."""
import os
from pathlib import Path

from acli.tools.policy import ensure_file_allowed


class ToolError(Exception):
    pass


def _resolve(workspace_dir: str, rel_path: str, settings=None, write=False) -> Path:
    ensure_file_allowed(rel_path, settings, write=write)
    base = Path(workspace_dir).resolve()
    target = (base / rel_path).resolve()
    if target != base and base not in target.parents:
        raise ToolError("Path escapes workspace directory: " + rel_path)
    return target


def list_files(workspace_dir: str, path: str = ".", settings=None) -> str:
    target = _resolve(workspace_dir, path, settings=settings, write=False)
    if not target.exists():
        return "Path not found: " + path
    if target.is_file():
        return path
    skip_dirs = {".git", "node_modules", ".venv", "__pycache__"}
    lines = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        rel_root = os.path.relpath(root, target)
        for name in sorted(files):
            rel = name if rel_root == "." else os.path.join(rel_root, name)
            try:
                ensure_file_allowed(rel, settings, write=False)
            except Exception:
                continue
            lines.append(rel)
        if len(lines) > 500:
            lines.append("... (truncated)")
            break
    return "\n".join(lines) if lines else "(empty directory)"


def read_file(workspace_dir: str, path: str, max_chars: int = 8000, settings=None) -> str:
    target = _resolve(workspace_dir, path, settings=settings, write=False)
    if not target.exists() or not target.is_file():
        raise ToolError("File not found: " + path)
    text = target.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars] + "\n...[truncated, " + str(len(text) - max_chars) + " more chars]"
    return text


def write_file(workspace_dir: str, path: str, content: str, settings=None) -> str:
    target = _resolve(workspace_dir, path, settings=settings, write=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return "Wrote " + str(len(content)) + " chars to " + path


def edit_file(workspace_dir: str, path: str, old_string: str, new_string: str, replace_all: bool = False, settings=None) -> str:
    target = _resolve(workspace_dir, path, settings=settings, write=True)
    if not target.exists():
        raise ToolError("File not found: " + path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old_string)
    if count == 0:
        raise ToolError("old_string not found in " + path)
    if count > 1 and not replace_all:
        raise ToolError("old_string appears " + str(count) + " times in " + path + "; pass replace_all=true or make old_string unique")
    new_text = text.replace(old_string, new_string) if replace_all else text.replace(old_string, new_string, 1)
    replacements = count if replace_all else 1
    target.write_text(new_text, encoding="utf-8")
    return "Edited " + path + " (" + str(replacements) + " replacement(s))"
