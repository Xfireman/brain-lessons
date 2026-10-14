# Privacy and security boundaries

Brain Lessons makes no network requests, runs no model, starts no background service, and collects no telemetry. It does not read transcripts or persist incoming hook payloads. Diagnostics do not echo raw tool commands, payloads, or parsing exceptions.

Rules are intentionally readable on disk. Selected rule titles, instructions and relative source paths are returned to the agent host. **The host may send these to its model provider and save them in a transcript.** Do not put secrets or data you cannot share with that host into lessons.

## Trust model

- Treat lessons like project instructions: review them before enabling them. A malicious instruction can still influence an agent.
- Only enable this hook in projects you trust. Project configuration is not a sandbox against someone who can modify files concurrently.
- Rule files are data. Brain never evaluates code from a rule and never executes a proposed tool command.
- Literal matching is not a shell security policy. Use the host's permissions and sandbox for security enforcement.
- Invalid payloads produce no decision. Invalid lessons are skipped with a diagnostic. Brain is not a fail-closed security control.
- Automatic hook installation supports macOS/Linux. It merges project-local settings and records each adapter's exact managed hook in `.brain/installation.json`. Keep this machine-specific file out of Git.
- Codex project hooks require project trust and explicit hook review in `/hooks`. The installer never grants trust, bypasses it, enables global features, or edits global settings. Test fixture trust is isolated to a disposable test home.

## What is written

`init` creates `.brain/lessons/` and, if absent, `.brain/.gitignore`. `learn` writes one new lesson. `install codex` changes `.codex/hooks.json`; `install claude-code` changes `.claude/settings.local.json`. Both record ownership in `.brain/installation.json`. `uninstall` removes only the selected adapter's hook and ownership entry, preserving the other adapter. No global agent settings are changed.

The project-local agent configuration can contain your other private settings. Follow your host's guidance for keeping it out of Git. Brain does not archive or upload it.

## Reporting a concern

For ordinary bugs, open an issue with a minimal **synthetic** reproduction. Remove credentials, private paths, organization names, internal domains, real transcripts and personal metadata first. For a sensitive issue, use GitHub's private vulnerability reporting when available; do not disclose secrets in a public issue.
