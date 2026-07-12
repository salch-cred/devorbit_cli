"""Restricted native command runner for computers without Docker.

This runner deliberately does not invoke a shell: no pipes, redirects, command chaining,
variable expansion, or shell built-ins. It allows a curated developer-tool executable list,
forces the workspace as cwd, blocks path traversal and dangerous flags, and applies timeouts.
"""
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from acli.production.environment import scrub_environment

ALLOWED_EXECUTABLES = {
    "python", "python3", "py", "pytest", "ruff", "mypy", "pyright",
    "git", "node", "npm", "npx", "pnpm", "yarn", "deno", "bun",
    "go", "cargo", "rustc", "java", "javac", "mvn", "mvnw", "gradle", "gradlew",
    "dotnet", "make", "cmake", "ctest", "ninja", "gcc", "g++", "clang", "clang++",
}
DANGEROUS_ARGUMENTS = {
    "--force", "--force-with-lease", "--hard", "--delete", "--no-preserve-root",
    "clean", "prune", "format", "shutdown", "reboot",
}
DANGEROUS_GIT_PAIRS = {("reset", "--hard"), ("clean", "-f"), ("push", "--force"), ("push", "-f")}
INLINE_FLAGS = {"-c", "-e", "--eval", "--print"}
SAFE_PYTHON_MODULES = {"compileall", "pytest", "unittest", "mypy", "ruff", "pyright"}
SHELL_META = re.compile(r"[|;&><`\r\n]")


def _split(command: str):
    if SHELL_META.search(command):
        raise PermissionError("Shell operators, redirects, chaining, and newlines are disabled in restricted native mode")
    args = shlex.split(command, posix=(os.name != "nt"))
    if os.name == "nt":
        args = [a[1:-1] if len(a) >= 2 and a[0] == a[-1] and a[0] in ("'", '"') else a for a in args]
    return args


def _inside_workspace(workspace: Path, raw: str) -> bool:
    if not raw or raw.startswith("-") or "://" in raw:
        return True
    candidate = Path(raw.strip('"\''))
    if not candidate.is_absolute() and ".." not in candidate.parts:
        return True
    resolved = (workspace / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    return resolved == workspace or workspace in resolved.parents


def validate_command(workspace: str, command: str):
    root = Path(workspace).resolve()
    args = _split(command)
    if not args:
        raise ValueError("Command is empty")
    executable = Path(args[0]).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]
    if executable not in ALLOWED_EXECUTABLES:
        raise PermissionError("Executable is not allowed in restricted native mode: " + executable)
    lowered = [a.lower() for a in args[1:]]
    if executable in {"python", "python3", "py", "node", "deno", "bun"} and any(flag in lowered for flag in INLINE_FLAGS):
        raise PermissionError("Inline interpreter code is blocked in restricted native mode; run a reviewed workspace file instead")
    if executable in {"python", "python3", "py"} and "-m" in lowered:
        module_index = lowered.index("-m") + 1
        if module_index >= len(lowered) or lowered[module_index] not in SAFE_PYTHON_MODULES:
            raise PermissionError("Python module execution is not allowlisted in restricted native mode")
    if executable == "git" and any(flag in lowered for flag in ("-c", "--exec-path", "--config-env", "--upload-pack", "--receive-pack")):
        raise PermissionError("Git execution/config override flags are blocked in restricted native mode")
    if any(arg in DANGEROUS_ARGUMENTS for arg in lowered):
        raise PermissionError("A dangerous command argument is blocked in restricted native mode")
    if executable == "git":
        for pair in DANGEROUS_GIT_PAIRS:
            if pair[0] in lowered and pair[1] in lowered:
                raise PermissionError("Dangerous Git operation blocked: " + " ".join(pair))
    for arg in args[1:]:
        if not _inside_workspace(root, arg):
            raise PermissionError("Path escapes the workspace: " + arg)
    return args


def run_restricted(workspace: str, command: str, timeout: int = 300) -> str:
    root = Path(workspace).resolve(); root.mkdir(parents=True, exist_ok=True)
    args = validate_command(str(root), command)
    executable = shutil.which(args[0])
    if not executable:
        raise FileNotFoundError("Developer tool is not installed or not on PATH: " + args[0])
    args[0] = executable
    env = scrub_environment()
    result = subprocess.run(args, cwd=root, capture_output=True, text=True, timeout=max(1, min(timeout, 1800)), env=env)
    return json.dumps({
        "backend": "native_restricted",
        "exit_code": result.returncode,
        "command": [Path(args[0]).name] + args[1:],
        "stdout": (result.stdout or "")[-12000:],
        "stderr": (result.stderr or "")[-12000:],
    }, indent=2)


def status() -> str:
    available = {name: bool(shutil.which(name)) for name in sorted(ALLOWED_EXECUTABLES)}
    return json.dumps({
        "backend": "native_restricted",
        "shell_enabled": False,
        "workspace_only": True,
        "available_tools": available,
    }, indent=2)
