# DevOrbit v2.1 Beta

**MVP coverage for all 15 requested feature areas plus the cross-platform production-hardening foundation is included.** See `FEATURES.md` for the implementation matrix, commands, limitations, and security boundary.

The b2 package includes a complete local regression and mocked-integration pass. See `QA_REPORT.md` for verified coverage, fixed defects, and environment-dependent items.

A Python terminal coding agent powered by NVIDIA NIM models. It includes a multi-model loop engine, local file editing, GitHub workflows, API-key-free DuckDuckGo search, and persistent Chromium browser automation.

## Production-hardening foundation

- Automatic isolation: Docker is used when available; unsupported PCs fall back to a restricted no-shell native runner limited to approved developer tools and the workspace.
- Unified-diff preview/application with checkpoints and automatic rollback after failed validation.
- OS keychain credential storage through `/credential set|status|delete ENV_NAME`; secrets are never printed.
- MCP Streamable HTTP plus existing stdio transport.
- Cross-language diagnostics, redacted audit metrics, and atomic crash-recovery state.
- Windows, macOS, and Linux CI/build definitions plus ZIP and native-installer build scripts.
- A dedicated Ubuntu CI job builds the Docker image and validates the complete sandbox contract; manual Docker Desktop/Engine testing on every target OS is not required.

Docker Desktop is optional for end users. See `SECURITY.md` and `PRODUCTION.md`. Signed/notarized public installers still require external certificates and platform accounts.

## Developer Rescue Suite

The v1.1 release adds difficult-issue tooling for day-to-day development:

- `/doctor` inventories runtimes, package managers, Git state, disk space, environment-key drift, Docker, and project markers.
- `/diagnose <error>` classifies common stack traces and CLI failures with concrete next steps.
- Background dev-process management with named processes and persistent logs.
- Repeated-test execution for flaky-test detection.
- Dependency consistency checks for Python, npm, Go, and Rust.
- Merge-conflict analysis, port/process inspection, HTTP endpoint probing, container diagnostics, and migration status checks.
- Reproduction reports and sanitized debug bundles that exclude source files, secrets, and environment values.

All commands that execute processes, probe endpoints, reproduce failures, or create bundles remain behind approval gates when called by the agent.

## v1 quick commands

```text
/dashboard                  Rich status dashboard
/doctor                     Toolchain and environment diagnostics
/diagnose <error>           Stack-trace and CLI-error triage
/processes                  Background dev-process status
/team <task>                Planner → coder → tester → reviewer loop
/index                      Build the repository FTS index
/providers                  Show NVIDIA/OpenAI/OpenRouter/Groq/Ollama/LM Studio status
/settings                   Persistent settings center
/tools                      Show all 76 agent tools
```

## Features

- **Coding runtime:** approved shell commands, checkpoints/rollback, project indexing, test/lint/build loops, security scanning, document/OCR reading, skills/plugins, MCP, voice, and multi-agent orchestration.
- **Multi-provider routing:** NVIDIA, OpenAI, OpenRouter, Groq, Ollama, LM Studio, custom OpenAI-compatible providers, task routing, caching, and fallback.
- **NVIDIA model loop:** GLM-5.2 first, with GLM-5.1/4.7, Llama, Qwen, Mixtral, Kimi, DeepSeek, MiniMax, GPT-OSS, Gemma, and Phi fallback entries in `models.json`.
- **Loop engineering:** retry with backoff, model fallback, context trimming, reflection, and an eight-step agent tool loop.
- **Files:** list, read, write, and exact-string edit inside a sandboxed workspace.
- **GitHub:** clone, branch, edit, diff, commit, push, and create pull requests. GitHub API tools can also read/write files and create issues.
- **Web search:** DuckDuckGo search without an API key, plus readable page extraction.
- **Browser automation:** persistent Playwright Chromium session with navigation, page inspection, clicks, typing, key presses, screenshots, back, and close.
- **Safety:** file path traversal is blocked. File/Git/GitHub writes and browser clicks, typing, or key presses require `[y/N]` confirmation unless explicitly auto-approved.

## Build a Windows application without Docker

Docker Desktop is not required. On Windows, double-click or run:

```bat
make-windows-app.bat
```

This creates `dist\\DevOrbit.exe` and a portable ZIP. If NSIS is installed it also creates `dist\\DevOrbit-Setup.exe`. The executable stores settings beside itself and automatically uses restricted native isolation when Docker is unavailable.

## Installation

### Linux/macOS

```bash
unzip devorbit-cli.zip
cd devorbit-cli
chmod +x install.sh run.sh
./install.sh
cp .env.example .env
# Edit .env and add NVIDIA_API_KEY
./run.sh
```

### Windows

```bat
:: Unzip, open Command Prompt in the folder, then:
install.bat
copy .env.example .env
:: Edit .env and add NVIDIA_API_KEY
run.bat
```

The installer creates `.venv`, installs Python dependencies, and downloads Playwright Chromium.

## Configuration

Get a free NVIDIA key from <https://build.nvidia.com>. Open a model, select **Get API Key**, and set:

```dotenv
NVIDIA_API_KEY=nvapi-...
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
```

Optional GitHub connection:

1. Create a fine-grained token at <https://github.com/settings/tokens>.
2. Give it repository **Contents** and **Pull requests** read/write access. Add **Issues** only if you want issue creation.
3. Configure:

```dotenv
GITHUB_TOKEN=github_pat_...
GITHUB_REPO=owner/repository
WORKSPACE_DIR=./workspace
AUTO_APPROVE=false
```

Never commit `.env`; it is included in `.gitignore`.

## Running

```bash
./run.sh                         # visible browser by default
./run.sh --headless              # hidden browser
./run.sh --workspace /path/repo  # use an existing local repository
./run.sh --no-tools              # chat only
./run.sh --mock                  # offline loop-engine demo
```

Windows equivalents use `run.bat`.

## Settings Center

Open the persistent terminal settings dashboard:

```text
/settings
```

It provides the same categories shown in DevOrbit-style settings screens:

- **Account:** telemetry, marketing preference, display email, plan label
- **Permissions:** workspace, file read/write switches, denied file patterns, network allow/deny rules, Git policy, outside-workspace policy, MCP permission
- **Appearance:** verbose agent steps, conversation width, dark/light/system theme, foreground/background/accent colors
- **Models:** primary NVIDIA model, temperature, context budget, retry count, backoff, maximum agent-tool loops
- **Customizations:** custom system prompt, skills list, MCP server list, custom rules
- **Browser:** visible/headless default, JavaScript policy, actuation confirmation, allowed/denied domains, download directory
- **App:** prevent sleep, background preference, notifications, update checks
- **Conversations:** autosave, history folder, retention limit, tool-result persistence

Settings are saved to `settings.json` and applied immediately without restarting. The file is ignored by Git. You can also automate settings:

```text
/settings show
/settings set models.primary_model z-ai/glm-5.2
/settings set appearance.verbose_agent_chat false
/settings set permissions.denied_domains ads.example,tracker.example
/settings reset browser
/settings reset
```

Operational settings are enforced by the runtime: model parameters feed the NVIDIA requests, file and network policies gate tools, browser rules gate automation, and conversation settings control autosave and retention.

## Example prompts

```text
Clone https://github.com/owner/repo into the workspace, inspect it, and explain its architecture.
Create a branch, fix the validation bug, show me the diff, then commit and push after I approve.
Search the web for the newest Python packaging guidance and summarize five sources.
Open https://example.com in the browser, inspect the page, and save a screenshot.
Fill this web form but ask before every click, typing action, or submission.
```

## Tools

### Local files and Git

- `list_files`, `read_file`, `write_file`, `edit_file`
- `git_clone`, `git_status`, `git_diff`, `git_checkout_new_branch`, `git_add_commit`, `git_push`

All local operations are restricted to `WORKSPACE_DIR`.

### GitHub

- `github_get_file`, `github_create_or_update_file`
- `github_create_pull_request`, `github_create_issue`

Git operations use your local Git credentials. GitHub API operations use `GITHUB_TOKEN`.

### Web search

- `web_search`: DuckDuckGo HTML search, no API key
- `fetch_web_page`: readable text extraction from a public HTTP/HTTPS page

### Browser

- `browser_navigate`, `browser_inspect`
- `browser_click`, `browser_type`, `browser_press`, `browser_evaluate`
- `browser_screenshot`, `browser_back`, `browser_close`

The browser is **visible by default** and preserves cookies and tabs during the CLI session. Use `--headless` on servers or when a visible window is not wanted. Browser clicks, typing, and key presses require confirmation because they may submit forms or change external data.

## CLI commands

| Command | Purpose |
|---|---|
| `/settings` | Open the persistent Settings Center |
| `/settings show` | Print every setting |
| `/settings set section.key value` | Change and immediately apply a setting |
| `/models` | Show fallback models and the last model used |
| `/model <id>` | Move a model to the front of the chain |
| `/tools` | List all available agent tools |
| `/reflect` | Critique and improve the previous answer |
| `/system <text>` | Replace the system prompt |
| `/approve` | Toggle automatic approval for mutating actions |
| `/reset` | Clear conversation history |
| `/save <file>` | Save conversation JSON |
| `/load <file>` | Load conversation JSON |
| `/exit` | Exit and close the browser |

## Architecture

```text
User prompt
  -> context-trim loop
  -> NVIDIA model retry/fallback loop
  -> model requests tool(s)
  -> confirmation gate for mutating actions
  -> tool execution and result appended to conversation
  -> loop back to model (maximum eight tool iterations)
  -> final answer
```

Important files:

```text
acli/loop_engine.py          retries, fallback, context, and tool loop
acli/client.py               NVIDIA OpenAI-compatible client
acli/tools/registry.py       tool schemas and dispatch
acli/tools/fs_tools.py       sandboxed file access
acli/tools/git_tools.py      local Git workflow
acli/tools/github_tools.py   GitHub REST API
acli/tools/web_tools.py      DuckDuckGo and page extraction
acli/tools/browser_tools.py  persistent Playwright browser
acli/settings_store.py       persistent JSON settings and defaults
acli/settings_ui.py          interactive terminal Settings Center
```

## Troubleshooting

- **Chromium missing:** activate `.venv`, then run `python -m playwright install chromium`.
- **Visible browser fails on a server:** run with `--headless`.
- **Git push authentication fails:** configure Git Credential Manager or SSH for the repository URL.
- **GitHub API returns 403:** verify token repository access and Contents/Pull requests permissions.
- **DuckDuckGo returns no results:** retry later; its HTML endpoint can temporarily throttle automated requests.
- **A model does not call tools:** move GLM-5.2, GLM-5.1, Llama 3.1, Qwen 2.5, or Mixtral to the front with `/model <id>`.
