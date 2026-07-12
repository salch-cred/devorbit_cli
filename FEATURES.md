# DevOrbit v2.1 Beta — Feature Matrix

This release intentionally provides **working MVP coverage** for all 15 requested product areas. It is not a claim that every integration is production-hardened.

1. **Coding agent workflow** — approved `run_terminal`, repository map, SQLite FTS index/search, quality checks, checkpoints and rollback, file tools, diff/status tools.
2. **Multi-agent loop** — `/team <task>` runs planner, coder, tester, and reviewer passes through the same model/tool loop.
3. **GitHub** — clone, branch, status, diff, commit, push, issues, direct file reads/writes, and pull requests.
4. **MCP** — minimal JSON-RPC stdio client with tool discovery and tool calls; controlled by MCP permission settings.
5. **Project intelligence** — `repo_map`, `build_project_index`, and `search_project_index` over source and documentation files.
6. **Browser automation** — persistent visible/headless Chromium, page inspection, clicks, typing, keys, JavaScript, screenshots, navigation, cookies/session persistence, and domain policy.
7. **Web research** — DuckDuckGo search, page extraction, and `research_web` with parallel source retrieval and source labels.
8. **Multiple providers** — NVIDIA, OpenAI, OpenRouter, Groq, Ollama, LM Studio, and custom `providers.json` entries using OpenAI-compatible APIs.
9. **Model engineering** — task routing, retry/backoff, multi-model fallback, context trimming, response cache, reflection, health-by-fallback behavior, and tool-loop limits.
10. **Images and documents** — PDF, DOCX, PPTX, XLSX, text, and OCR image extraction through `read_document`.
11. **Terminal interface** — `/dashboard`, structured Settings Center, theme preferences, verbose-step control, tool/model status, and slash commands.
12. **Voice** — cross-platform system text-to-speech, ffmpeg microphone recording, and an API transcription hook.
13. **Skills and plugins** — local Markdown skills and Python plugins with discovery and execution. Example files are included.
14. **Security** — secret detection, prompt-injection indicators, command risk scoring, hard-blocked destructive commands, path sandboxing, domain rules, and approvals.
15. **Developer quality** — automatic language-aware test/lint/build presets, compile checks, Git changelog generation, security scan, and CI-friendly exit/output capture.

## Cross-platform production foundation (v2.1 Beta)

- Automatic `run_isolated` backend selection: hardened Docker when available, restricted no-shell native execution otherwise
- Unified patch preview/application, automatic checkpoints, validation, and rollback
- OS keychain credentials and hidden credential entry
- MCP Streamable HTTP and stdio transports
- Cross-language compile/type/lint diagnostics
- Redacted local audit metrics and atomic crash recovery state
- Windows, macOS, and Linux CI plus platform build/installer definitions
- Dedicated Linux CI sandbox-contract testing, replacing manual Docker Desktop/Engine testing on every target OS
- Portable ZIP distribution and native-installer pipelines
- Frozen-executable path handling so settings/models live beside the application
- One-command Windows application builder: `make-windows-app.bat`

Public signed/notarized installers require external Apple/Windows signing certificates and hosted CI credentials; see `PRODUCTION.md`.

## Developer Rescue Suite (v1.1)

The agent now has additional tools for the hardest development failures:

- `project_doctor`, `environment_doctor`, `dependency_doctor`
- `diagnose_error`, `diagnose_log_file`
- `flaky_test_check`, `analyze_merge_conflicts`
- `inspect_port`, `start_dev_process`, `list_dev_processes`, `dev_process_logs`, `stop_dev_process`
- `api_probe`, `container_doctor`, `database_migration_doctor`
- `reproduce_issue`, `create_debug_bundle`

The debug bundle is deliberately sanitized: it includes toolchain and project metadata but excludes source code, `.env` values, credentials, and cookies.

## High-impact commands

```text
/dashboard
/team Build and test the requested feature
/index
/settings
/providers
/tools
```

## High-impact tool prompts

```text
Create a checkpoint, fix the bug, run quality_check, show the diff, and restore if tests fail.
Index this repository and find every authentication-related implementation.
Run a security scan before committing.
Research the latest official guidance and cite each retrieved source.
List tools from this MCP server command: python my_server.py
Read report.pdf and summarize it.
```

## Security boundary

Mutating tools require confirmation by default. `run_terminal`, plugin execution, MCP calls, restore operations, browser actuation, GitHub writes, and recording are included in the approval gate. `--auto-approve` should only be used in an isolated workspace.
