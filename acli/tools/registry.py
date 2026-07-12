"""Tool schemas (OpenAI function-calling format) and dispatch logic."""
from acli.tools import fs_tools, git_tools, github_tools, web_tools, browser_tools
from acli.extended.registry import SCHEMAS as EXTENDED_SCHEMAS, MUTATING as EXTENDED_MUTATING, NAMES as EXTENDED_NAMES, describe as describe_extended, dispatch as dispatch_extended

MUTATING_TOOLS = {
    "write_file",
    "edit_file",
    "git_clone",
    "git_add_commit",
    "git_push",
    "git_checkout_new_branch",
    "github_create_issue",
    "github_create_pull_request",
    "github_create_or_update_file",
    "browser_click",
    "browser_type",
    "browser_press",
    "browser_evaluate",
    "browser_screenshot",
}
MUTATING_TOOLS.update(EXTENDED_MUTATING)

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "list_files",
        "description": "List files in the local workspace directory (recursive).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Relative path inside the workspace. Defaults to the workspace root."}
        }},
    }},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file from the local workspace directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create or overwrite a text file in the local workspace directory.",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]},
    }},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace an exact substring in an existing workspace file (find-and-replace edit).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "replace_all": {"type": "boolean"},
        }, "required": ["path", "old_string", "new_string"]},
    }},
    {"type": "function", "function": {
        "name": "git_status",
        "description": "Show local git status of the workspace.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "git_diff",
        "description": "Show unstaged git diff of the workspace.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "git_clone",
        "description": "Clone a GitHub repo into the workspace directory.",
        "parameters": {"type": "object", "properties": {"repo_url": {"type": "string"}, "dest": {"type": "string"}}, "required": ["repo_url"]},
    }},
    {"type": "function", "function": {
        "name": "git_checkout_new_branch",
        "description": "Create and switch to a new local git branch.",
        "parameters": {"type": "object", "properties": {"branch_name": {"type": "string"}}, "required": ["branch_name"]},
    }},
    {"type": "function", "function": {
        "name": "git_add_commit",
        "description": "Stage and commit changes in the workspace git repo.",
        "parameters": {"type": "object", "properties": {
            "message": {"type": "string"},
            "paths": {"type": "array", "items": {"type": "string"}},
        }, "required": ["message"]},
    }},
    {"type": "function", "function": {
        "name": "git_push",
        "description": "Push the current branch to GitHub.",
        "parameters": {"type": "object", "properties": {"branch": {"type": "string"}, "remote": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "github_create_issue",
        "description": "Create a GitHub issue on the configured or specified repo.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "body": {"type": "string"}, "repo": {"type": "string"}
        }, "required": ["title"]},
    }},
    {"type": "function", "function": {
        "name": "github_create_pull_request",
        "description": "Open a GitHub pull request.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "head": {"type": "string"}, "base": {"type": "string"},
            "body": {"type": "string"}, "repo": {"type": "string"}
        }, "required": ["title", "head"]},
    }},
    {"type": "function", "function": {
        "name": "github_get_file",
        "description": "Read a file directly from a GitHub repo via the API (no local clone needed).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "ref": {"type": "string"}, "repo": {"type": "string"}
        }, "required": ["path"]},
    }},
    {"type": "function", "function": {
        "name": "github_create_or_update_file",
        "description": "Create or update a single file directly on GitHub via the API (no local clone needed).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}, "message": {"type": "string"},
            "branch": {"type": "string"}, "repo": {"type": "string"}
        }, "required": ["path", "content", "message"]},
    }},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the public web with DuckDuckGo. No API key is required.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}, "max_results": {"type": "integer", "minimum": 1, "maximum": 15}
        }, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "fetch_web_page",
        "description": "Fetch a public URL and extract readable page text without opening the browser.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "browser_navigate",
        "description": "Open a URL in the persistent automated Chromium browser. Browser is visible unless CLI starts with --headless.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "browser_inspect",
        "description": "Read text and links from the current browser page.",
        "parameters": {"type": "object", "properties": {"max_chars": {"type": "integer"}}},
    }},
    {"type": "function", "function": {
        "name": "browser_click",
        "description": "Click the first element matching a CSS selector in the current browser page. Requires confirmation.",
        "parameters": {"type": "object", "properties": {"selector": {"type": "string"}}, "required": ["selector"]},
    }},
    {"type": "function", "function": {
        "name": "browser_type",
        "description": "Type or fill text into the first element matching a CSS selector. Requires confirmation and never reveals stored passwords.",
        "parameters": {"type": "object", "properties": {
            "selector": {"type": "string"}, "text": {"type": "string"}, "clear": {"type": "boolean"}
        }, "required": ["selector", "text"]},
    }},
    {"type": "function", "function": {
        "name": "browser_press",
        "description": "Press a keyboard key on an element, such as Enter on a form. Requires confirmation.",
        "parameters": {"type": "object", "properties": {
            "selector": {"type": "string"}, "key": {"type": "string"}
        }, "required": ["selector", "key"]},
    }},
    {"type": "function", "function": {
        "name": "browser_evaluate",
        "description": "Execute custom JavaScript in the current page, subject to Browser JavaScript policy and confirmation.",
        "parameters": {"type": "object", "properties": {"script": {"type": "string"}}, "required": ["script"]},
    }},
    {"type": "function", "function": {
        "name": "browser_screenshot",
        "description": "Save a screenshot of the current browser page in the workspace.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "full_page": {"type": "boolean"}
        }},
    }},
    {"type": "function", "function": {
        "name": "browser_back",
        "description": "Go back one page in browser history.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "browser_close",
        "description": "Close the persistent automated browser session.",
        "parameters": {"type": "object", "properties": {}},
    }},
]
TOOL_SCHEMAS.extend(EXTENDED_SCHEMAS)


def describe_call(name, args):
    if name == "write_file":
        return "write file '" + str(args.get("path")) + "' (" + str(len(args.get("content", ""))) + " chars)"
    if name == "edit_file":
        return "edit file '" + str(args.get("path")) + "'"
    if name == "git_clone":
        return "clone '" + str(args.get("repo_url")) + "' into the workspace"
    if name == "git_add_commit":
        return "git commit with message: " + str(args.get("message"))
    if name == "git_push":
        return "git push to remote '" + str(args.get("remote", "origin")) + "'"
    if name == "git_checkout_new_branch":
        return "create git branch '" + str(args.get("branch_name")) + "'"
    if name == "github_create_issue":
        return "create GitHub issue: " + str(args.get("title"))
    if name == "github_create_pull_request":
        return "open GitHub PR: " + str(args.get("title"))
    if name == "github_create_or_update_file":
        return "write '" + str(args.get("path")) + "' directly to GitHub repo " + str(args.get("repo") or "(default)")
    if name == "browser_click":
        return "click browser element '" + str(args.get("selector")) + "'"
    if name == "browser_type":
        return "type " + str(len(args.get("text", ""))) + " characters into browser element '" + str(args.get("selector")) + "'"
    if name == "browser_press":
        return "press '" + str(args.get("key")) + "' on browser element '" + str(args.get("selector")) + "'"
    if name == "browser_evaluate":
        return "execute " + str(len(args.get("script", ""))) + " characters of JavaScript in the browser"
    if name in EXTENDED_NAMES:
        return describe_extended(name, args)
    return name + "(" + str(args) + ")"


def dispatch(name, args, settings):
    ws = settings.workspace_dir
    if name.startswith("git_") and str(settings.terminal_policy).lower() == "deny":
        raise PermissionError("Git commands are disabled in Settings > Permissions")
    if name == "list_files":
        return fs_tools.list_files(ws, args.get("path", "."), settings=settings)
    if name == "read_file":
        return fs_tools.read_file(ws, args["path"], settings=settings)
    if name == "write_file":
        return fs_tools.write_file(ws, args["path"], args.get("content", ""), settings=settings)
    if name == "edit_file":
        return fs_tools.edit_file(ws, args["path"], args["old_string"], args["new_string"], args.get("replace_all", False), settings=settings)
    if name == "git_status":
        return git_tools.git_status(ws)
    if name == "git_diff":
        return git_tools.git_diff(ws)
    if name == "git_clone":
        return git_tools.git_clone(ws, args["repo_url"], args.get("dest", "."), settings=settings)
    if name == "git_checkout_new_branch":
        return git_tools.git_checkout_new_branch(ws, args["branch_name"])
    if name == "git_add_commit":
        return git_tools.git_add_commit(ws, args["message"], args.get("paths"))
    if name == "git_push":
        return git_tools.git_push(ws, args.get("branch"), args.get("remote", "origin"))
    if name == "github_create_issue":
        return github_tools.create_issue(settings, args["title"], args.get("body", ""), args.get("repo"))
    if name == "github_create_pull_request":
        return github_tools.create_pull_request(settings, args["title"], args["head"], args.get("base", "main"), args.get("body", ""), args.get("repo"))
    if name == "github_get_file":
        return github_tools.get_file(settings, args["path"], args.get("ref"), args.get("repo"))
    if name == "github_create_or_update_file":
        return github_tools.create_or_update_file(settings, args["path"], args["content"], args["message"], args.get("branch"), args.get("repo"))
    if name == "web_search":
        return web_tools.web_search(args["query"], args.get("max_results", 8), settings=settings)
    if name == "fetch_web_page":
        return web_tools.fetch_web_page(args["url"], settings=settings)
    if name == "browser_navigate":
        return browser_tools.browser_navigate(args["url"])
    if name == "browser_inspect":
        return browser_tools.browser_inspect(args.get("max_chars", 12000))
    if name == "browser_click":
        return browser_tools.browser_click(args["selector"])
    if name == "browser_type":
        return browser_tools.browser_type(args["selector"], args["text"], args.get("clear", True))
    if name == "browser_press":
        return browser_tools.browser_press(args["selector"], args["key"])
    if name == "browser_evaluate":
        return browser_tools.browser_evaluate(args["script"])
    if name == "browser_screenshot":
        return browser_tools.browser_screenshot(args.get("path", "screenshot.png"), args.get("full_page", True))
    if name == "browser_back":
        return browser_tools.browser_back()
    if name == "browser_close":
        return browser_tools.browser_close()
    if name in EXTENDED_NAMES:
        return dispatch_extended(name, args, settings)
    raise ValueError("Unknown tool: " + name)
