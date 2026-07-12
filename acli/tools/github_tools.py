"""GitHub REST API tools. Requires GITHUB_TOKEN (and usually GITHUB_REPO) in .env."""
import base64
from acli.tools.policy import ensure_network_allowed

API_BASE = "https://api.github.com"


class ToolError(Exception):
    pass


def _headers(token: str):
    if not token:
        raise ToolError("No GITHUB_TOKEN set. Add one to .env to use GitHub tools.")
    return {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _repo(settings, repo):
    ensure_network_allowed(API_BASE, settings)
    return repo or settings.github_repo


def create_issue(settings, title: str, body: str = "", repo: str = None) -> str:
    import requests

    repo = _repo(settings, repo)
    if not repo:
        raise ToolError("No repo specified and no default GITHUB_REPO configured.")
    url = API_BASE + "/repos/" + repo + "/issues"
    resp = requests.post(url, headers=_headers(settings.github_token), json={"title": title, "body": body}, timeout=30)
    if resp.status_code >= 300:
        raise ToolError("GitHub API error " + str(resp.status_code) + ": " + resp.text)
    data = resp.json()
    return "Created issue #" + str(data.get("number")) + ": " + data.get("html_url", "")


def create_pull_request(settings, title: str, head: str, base: str = "main", body: str = "", repo: str = None) -> str:
    import requests

    repo = _repo(settings, repo)
    if not repo:
        raise ToolError("No repo specified and no default GITHUB_REPO configured.")
    url = API_BASE + "/repos/" + repo + "/pulls"
    resp = requests.post(url, headers=_headers(settings.github_token), json={"title": title, "head": head, "base": base, "body": body}, timeout=30)
    if resp.status_code >= 300:
        raise ToolError("GitHub API error " + str(resp.status_code) + ": " + resp.text)
    data = resp.json()
    return "Created PR #" + str(data.get("number")) + ": " + data.get("html_url", "")


def get_file(settings, path: str, ref: str = None, repo: str = None) -> str:
    import requests

    repo = _repo(settings, repo)
    if not repo:
        raise ToolError("No repo specified and no default GITHUB_REPO configured.")
    url = API_BASE + "/repos/" + repo + "/contents/" + path
    params = {"ref": ref} if ref else {}
    resp = requests.get(url, headers=_headers(settings.github_token), params=params, timeout=30)
    if resp.status_code >= 300:
        raise ToolError("GitHub API error " + str(resp.status_code) + ": " + resp.text)
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return content


def create_or_update_file(settings, path: str, content: str, message: str, branch: str = None, repo: str = None) -> str:
    import requests

    repo = _repo(settings, repo)
    if not repo:
        raise ToolError("No repo specified and no default GITHUB_REPO configured.")
    url = API_BASE + "/repos/" + repo + "/contents/" + path
    headers = _headers(settings.github_token)
    params = {"ref": branch} if branch else {}
    existing = requests.get(url, headers=headers, params=params, timeout=30)
    sha = existing.json().get("sha") if existing.status_code == 200 else None

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
    }
    if branch:
        payload["branch"] = branch
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 300:
        raise ToolError("GitHub API error " + str(resp.status_code) + ": " + resp.text)
    data = resp.json()
    commit_url = data.get("commit", {}).get("html_url", "")
    return "Wrote " + path + " on GitHub (" + commit_url + ")"
