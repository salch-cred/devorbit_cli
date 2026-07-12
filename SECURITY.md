# Security Model

DevOrbit uses layered controls: explicit approvals, workspace path confinement, domain rules, secret redaction, checkpoints, and automatic isolation. `run_isolated` uses Docker when available and otherwise selects a restricted no-shell native runner. Unrestricted native `run_terminal` remains disabled by default.

The Docker sandbox drops Linux capabilities, enables `no-new-privileges`, uses a read-only container root, limits PIDs/CPU/memory, disables network by default, and mounts only the configured workspace read-write. The native fallback invokes no shell, rejects pipes/redirection/chaining, uses an executable allowlist, blocks destructive Git flags and path traversal, removes provider credentials from child environments, enforces the workspace cwd, and applies timeouts.

Secrets belong in the OS keychain or environment variables. They must never be placed in prompts, settings.json, plugins, debug bundles, or Git history.

Report vulnerabilities privately. Do not attach credentials, private source code, cookies, or full environment dumps.
