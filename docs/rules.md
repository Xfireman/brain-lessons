# Rule format

Lessons live in `.brain/lessons/<id>.json`. Each file is independent. The [examples directory](../examples/) contains synthetic rules you can inspect and adapt.

```json
{
  "schema_version": 1,
  "id": "project-tests",
  "title": "Use the project test runner",
  "instruction": "This project uses pnpm test.",
  "action": "block",
  "enabled": true,
  "match": {
    "tools": ["Bash"],
    "commands": ["npm test"],
    "paths": []
  },
  "examples": {
    "match": [{"tool": "Bash", "command": "npm test -- --watch"}],
    "miss": [{"tool": "Bash", "command": "pnpm test"}]
  }
}
```

## Matching

The tool must match one of `tools`. Then **any** command phrase **or** path pattern can match. Empty command/path lists are allowed individually, but both cannot be empty.

Command phrases are consecutive POSIX shell tokens, using Python's `shlex`. `npm test` matches `cd app && npm test -- --watch`, but does not match `pnpm test`. Comments and a single quoted argument are tokenized, not executed. This does not resolve shell syntax, substitutions, variables, aliases, scripts, or the real executable. `echo npm test` can also match. Use it for project conventions, not hostile command detection.

Paths use case-sensitive `fnmatch` on normalized project-relative paths. Supply both `Dockerfile` and `**/Dockerfile` to include the root and nested directories. `*` may cross directory separators. Files resolved outside the project do not match. Lesson symlinks and symlinked configuration directories are rejected.

`--root` is a global CLI option and must appear before the subcommand. With it, relative preview paths are interpreted inside that project. Without it, discovery stops at the nearest `.brain` directory or Git repository boundary, and preview paths are relative to the current directory. Hook calls outside the installed project or inside a nested repository receive no parent-project rules.

## Actions

- `remind`: return additional context to the host. The current tool call is not stopped.
- `block`: return an explicit `deny` decision with the lesson as its reason. The matching operation is refused by a host honoring this hook contract. The agent can choose another operation, which is checked separately.

Blocks are ordered before reminders, then by ID. At most three lessons are included in a response. The total decision considers all matching rules; a block cannot be hidden behind the display cap. Any omitted count is displayed. `list --json` includes every loaded rule.

## Validation and examples

`check` checks schema and authored examples. Each rule needs at least one positive example to pass, including disabled rules. Negative examples are strongly recommended. A disabled rule is never injected, but its examples still run so re-enabling it does not hide stale matching logic.

Examples exercise the trigger, not the AI's ability to follow its instruction. Passing examples do not prove model obedience or absence of false positives on other inputs.

The implementation bounds each rule to 64 KiB, each instruction to 1,200 characters, each trigger list to 20 entries, and each example list to 50 entries. It loads at most 500 rules per project; a larger store is rejected visibly. These are input/resource limits for this release, not measured optimal settings. Hook input is bounded to 262,144 text characters and is not persisted.

Use lowercase IDs with digits and hyphens, up to 64 characters. The filename must match the ID. Titles and instructions reject terminal control characters. A malformed rule is skipped by the hook and reported by `check`.
