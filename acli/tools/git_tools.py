"""Local git operations, scoped to the configured workspace directory."""
import subprocess
from pathlib import Path
from acli.tools.policy import ensure_network_allowed


class ToolError(Exception):
    pass


def _run(workspace_dir: str, args):
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=workspace_dir,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise ToolError("git is not installed on this machine")
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        raise ToolError("git " + " ".join(args) + " failed:\n" + output)
    return output.strip() or "(no output)"


def git_status(workspace_dir: str) -> str:
    return _run(workspace_dir, ["status", "--short", "--branch"])


def git_diff(workspace_dir: str) -> str:
    return _run(workspace_dir, ["diff"])


def git_clone(workspace_dir: str, repo_url: str, dest: str = ".", settings=None) -> str:
    if settings is not None and repo_url.startswith(("http://", "https://")):
        ensure_network_allowed(repo_url, settings)
    Path(workspace_dir).mkdir(parents=True, exist_ok=True)
    return _run(workspace_dir, ["clone", repo_url, dest])


def git_add_commit(workspace_dir: str, message: str, paths=None) -> str:
    add_args = ["add"] + (paths if paths else ["-A"])
    _run(workspace_dir, add_args)
    return _run(workspace_dir, ["commit", "-m", message])


def git_push(workspace_dir: str, branch: str = None, remote: str = "origin") -> str:
    args = ["push", remote]
    if branch:
        args.append(branch)
    return _run(workspace_dir, args)


def git_checkout_new_branch(workspace_dir: str, branch_name: str) -> str:
    return _run(workspace_dir, ["checkout", "-b", branch_name])
