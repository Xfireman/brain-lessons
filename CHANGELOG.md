# Changelog

## 0.2.0

- Codex is now the primary documented integration, using project `.codex/hooks.json`.
- Added native Bash/exec normalization and multi-file `apply_patch` matching, including delete and both sides of moves.
- Codex and Claude Code hooks share lessons but install/uninstall independently, preserving other host settings.
- Added an offline native Codex smoke test with real host decisions and synthetic model responses. Disabled rules are the negative control; enabled rules block both shell execution and file creation while a permitted command still runs.
- Codex hook trust remains an explicit user review step. The installer never trusts hooks or changes global Codex configuration.
- Existing Claude Code support remains available.

## 0.1.0

Initial experimental release:

- Project-local lesson files with explicit command/path triggers and examples.
- CLI for creating, inspecting, checking and previewing rules.
- Claude Code PreToolUse reminders and opt-in deny decisions.
- Project-local installation and removal that preserve other settings.
- Offline synthetic demo and subprocess integration tests.

Compatibility is documented in the README. No live-agent performance or productivity claim is made.
