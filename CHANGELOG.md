# Changelog

## 0.3.0

- Added the optional Codex `brain-remember` skill for explicit, natural-language project corrections. It previews concrete scope, checks examples, and respects preview-only requests; it does not collect conversations automatically.
- Added `learn --dry-run` to validate positive and negative examples without writing a rule. Existing rule IDs are reported as conflicts.
- Preview and save both enforce the loader's existing rule-size and store-capacity limits, so authoring cannot silently create an unloadable rule or overflow the store.
- Added `install codex --with-skill` and the matching uninstall command. Managed skill files are protected against overwriting user edits; failed operations restore prior managed files. Existing hook-only commands remain available.
- Added a generated-client offline replay, a reproducible 20-second GIF, bilingual trial guides, and a feedback issue template.
- Native Codex acceptance now also checks discovery of the installed skill. Model-driven skill trials are separate from deterministic hook acceptance.

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
