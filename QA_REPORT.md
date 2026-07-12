# DevOrbit v2.1.0 Beta 2 — QA Report

Date: 2026-07-12

## Final result

All locally executable tests pass. The suite runs with `ResourceWarning` promoted to an error and completes without warnings.

- 15 automated unit/integration tests passed
- 44 Python modules imported successfully
- 76 tool schemas validated
- 33 mutating tools verified behind approval gates
- Offline CLI startup, dashboard, models, providers, diagnostics, settings, reflection, and shutdown exercised
- Python compilation, dependency consistency, JSON/YAML configuration, shell-script syntax, branding, and packaging definitions validated

## Directly verified

- File list/read/write/edit permissions and workspace traversal protection
- Hidden `.env` and key-file denial patterns
- Local Git status, diff, branch, and commit workflows
- Repository mapping and SQLite full-text indexing
- Checkpoint creation/restoration with credential-file exclusion
- Restricted native command validation, timeouts, inline-code blocking, and environment-secret scrubbing
- Unified patch preview/apply/rollback
- Model routing and response caching
- History trimming at complete conversation-turn boundaries
- MCP stdio success, error closure, timeout enforcement, and process cleanup
- PDF/DOCX/PPTX/XLSX/text extraction paths
- Plugin execution in a separate isolated Python process with scrubbed environment
- Security scanning, audit metrics, recovery state, settings persistence, and debug diagnostics
- Portable/installer definitions and cross-platform CI configuration

## Mocked integration verification

- GitHub issue, pull request, file read, and file write request/response handling
- DuckDuckGo result parsing and web-page extraction
- MCP Streamable HTTP JSON and SSE parsing
- Browser navigation/inspection/click/type/key/JavaScript/screenshot APIs and permission rules
- OS keychain status behavior without revealing secret values

## Defects found and fixed in this pass

1. History trimming could leave orphan assistant/tool messages.
2. `.env` denial was bypassed by incorrect leading-dot normalization.
3. Native child processes leaked non-provider cloud secrets such as AWS keys.
4. MCP stdio timeout used a blocking read and could hang past its timeout.
5. MCP subprocess pipes/processes were not always closed cleanly.
6. SQLite response-cache connections produced resource warnings.
7. Checkpoints copied `.env`, PEM, key, credential, and secret files.
8. Browser screenshot directories could be configured outside the workspace.
9. Browser screenshots were not included in mutating-action approvals.
10. Plugins executed inside the main DevOrbit process with inherited secrets.
11. Restricted native mode allowed inline interpreter execution (`python -c`, `node -e`).
12. Unrestricted/background child processes inherited API and authentication secrets.
13. Empty model lists did not produce a clear routing error.

## Environment-dependent certification still required

The following cannot be truthfully certified in this sandbox without external systems or target hardware:

- Live NVIDIA/GLM, OpenAI, OpenRouter, Groq, Ollama, and LM Studio inference and quotas
- Live GitHub authentication, protected branches, pushes, pull requests, and Actions
- Real Playwright browser installation, interactive logins, downloads, microphone permissions, and CAPTCHA/manual takeover
- Real Docker daemon isolation on a target host (the CI security contract is defined and validated structurally)
- Microphone recording, OS speech output, and provider transcription
- Windows EXE/NSIS build, macOS signing/notarization, and Linux package execution on their native operating systems
- Real third-party MCP servers and OAuth flows

These items require CI runners, credentials, devices, or provider accounts. They are not reported as passing merely because mocked contracts pass.

## Reproduce the local QA pass

```bash
python -m compileall -q acli packaging tests
PYTHONWARNINGS=error::ResourceWarning python -m unittest discover -s tests -v
python -m acli.main --mock --headless
```
