---
name: brain-remember
description: Save an explicit project correction as a tested Brain Lessons command or path rule. Use for "remember this project rule" or "记住这条项目规矩" requests about tool actions. Ordinary preferences, explanations, and one-time fixes do not need a rule.
---

# Save a project correction

Turn the user's correction into a narrowly scoped rule that Brain Lessons can match before a tool call. Use the user's language when explaining the result. This skill does not archive conversations or learn from them automatically.

The installed CLI for this skill is:

```sh
{{BRAIN_LESSONS_COMMAND}}
```

Append `--root <absolute-project-path>` before each subcommand. This command uses the Python environment that installed the skill, even when `brain-lessons` is absent from PATH. If that environment was removed, explain the problem and ask the user to reinstall in their chosen environment; do not install software or change global configuration silently.

## Decide whether a rule fits

Read only the project files needed to identify the intended command/path and existing rules (`list --json`). Prefer an existing equivalent rule over creating duplicates.

- Match a concrete shell command token sequence or project-relative path glob. Broad quality requests such as "write clean code" and preferences such as "reply in Chinese" belong in ordinary instructions or memory. Explain that briefly; do not manufacture an all-tools rule or edit AGENTS.md without a request.
- Keep scope within the current project. Ask for missing paths or commands when the correction is ambiguous; do not guess a broad glob. For mixed requests, save only the supported, authorized part and explain what remains.
- Default to `remind`. Use `block` only when the user explicitly requests blocking/denying matching calls. "Remember" alone is not permission to block. If they explicitly authorize a clear blocking rule, do not ask for the same permission again.
- For generated-file protection, use `--tool Edit --tool Write` and the relevant generated directory. Do not block reads. These tools cover matching native Codex apply_patch candidates; shell-based file writes and other tool shapes are not covered by a path rule. Command matching is consecutive shell tokens, not a full shell interpreter.
- Save only the reusable correction. Do not include credentials, personal data, conversation excerpts, or unrelated project content.

## Preview, then save within the user's request

Use `learn <kebab-id> --title ... --instruction ...` with concrete `--tool`, `--command` or `--path` flags. Add at least one real positive example and a nearby allowed negative example using `--sample-command` / `--miss-command` or `--sample-path` / `--miss-path`. Safely quote arguments or use a subprocess argument list; never interpolate the user's words into executable shell syntax.

First run the exact proposed command with `--dry-run`. This returns the candidate JSON and checks both example types without creating files. Resolve any failed examples by correcting the rule's scope, not by replacing a meaningful negative case with an unrelated one.

Show a short preview: the correction, action, matching scope, one matching action, and one allowed action. If the user asked for a preview or confirmation before saving, stop here. Otherwise save when scope and action are already authorized by running the same command without `--dry-run`, then run `check` and `recall` for both examples. Never execute the prohibited example just to test it. Do not overwrite an existing rule automatically; show the conflict and ask which rule should change if the request does not settle it.

Example arguments for an explicitly requested generated-file block:

```text
learn generated-client --title "Edit the schema, then regenerate" --instruction "Change schema/api.json, then regenerate; do not edit src/generated/ directly." --tool Edit --tool Write --path "src/generated/*" --action block --sample-path src/generated/client.py --miss-path src/main.py --dry-run
```

## Report what actually happened

Report the saved file (or that nothing was saved), remind/block, examples checked, and the first action the user needs. Saving a rule is distinct from the hook being active: verify the project has a Brain Lessons hook, but never claim its trust status from the file alone. Codex requires hooks enabled, a trusted project, and review/trust of the exact hook in `/hooks`. Do not edit trust records or global settings. If installation is missing, offer the project-local `install codex --with-skill` command and explain its effect.

Ordinary rule edits take effect on the next matching call once the hook is active. `remind` adds context; `block` denies the matching call. Neither is a security sandbox or a guarantee about all future behavior.
