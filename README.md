# Brain Lessons

**Turn “I already told you that” into a project rule.**

Save a correction once. Brain selects it for matching tool calls, with its source attached. Remind the agent, or explicitly block a known wrong command.

Local files · No model calls · No runtime dependencies · Python 3.10+

[中文](README.zh-CN.md) · [Rule format](docs/rules.md) · [Privacy & limits](SECURITY.md) · [Contribute](CONTRIBUTING.md)

```text
You: “This project uses pnpm test.”

Next session, the agent proposes:
  npm test     → BLOCK
                 project-tests.json: use pnpm test

Then it proposes:
  pnpm test    → no Brain decision; normal permissions apply
```

This is a deterministic hook example, not a recorded claim about model behavior. Try the real offline demo below.

## Try it

Clone or download this repository, then run from its directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/brain-lessons demo
```

The demo uses a temporary project and the actual hook handler. It runs no model or shell command and leaves your project unchanged.

To use the installed CLI in your own project, add this virtual environment to the current shell's PATH before changing directories:

```sh
export PATH="$PWD/.venv/bin:$PATH"
cd /path/to/your/project
brain-lessons init
```

Keep the virtual environment in place while its hook is installed.

## Teach one lesson

```sh
brain-lessons learn project-tests \
  --title "Use the project test runner" \
  --instruction "This project uses pnpm test. The npm test command is not configured." \
  --tool Bash \
  --command "npm test" \
  --sample-command "npm test -- --watch" \
  --miss-command "pnpm test" \
  --action block

brain-lessons check
brain-lessons recall --tool Bash --command "npm test"
```

Your correction lives in `.brain/lessons/project-tests.json`. Edit it directly, review it in Git, or set `enabled` to `false`. Learning the same ID again refuses to overwrite it.

`remind` is the default action. `block` must be chosen explicitly. Preview matching rules before installing the hook.

## Connect Claude Code

From the project where the rules should apply:

```sh
brain-lessons install claude-code
```

This adds one `PreToolUse` hook to **project-local** `.claude/settings.local.json`. It preserves other hooks and settings. Start a new Claude Code session and inspect `/hooks` before relying on it.

To remove the integration while keeping your lessons:

```sh
brain-lessons uninstall claude-code
```

The CLI and hook protocol have automated tests. Live model obedience is a separate outcome: a reminder is additional context, not a guarantee that the agent will change its next action. A block returns the host's explicit `deny` decision. Brain never returns an `allow` decision and never grants permissions.

See the [official Claude Code hook contract](https://code.claude.com/docs/en/hooks#pretooluse-decision-control). Automatic installation currently targets macOS and Linux. Other agents can call `recall` explicitly; this release does not claim native integration with other hosts.

## Why use this?

Rules that apply to every task belong in your agent's normal project instructions. Brain is useful when a correction should surface for a particular command or file, and you want to see **which rule matched and why it is there**.

- **Selective:** tools plus command phrases or project-relative path patterns.
- **Inspectable:** ordinary JSON, readable provenance, authored examples.
- **Reversible:** opt-in project installation, explicit uninstall.
- **Local:** no account, background service, database, telemetry, or Brain-operated endpoint.

Brain does not archive conversations, automatically extract lessons, or silently learn from your activity. You decide what gets saved.

## Commands

- `init` — create the local store without overwriting existing files.
- `learn` — save a correction with triggers and examples.
- `list` — inspect the complete rule set.
- `recall` — preview matching rules without running the proposed command.
- `check` — validate rules and run their positive/negative examples.
- `install` / `uninstall claude-code` — manage the project hook.
- `demo` — see the complete offline example.

Use `--help` for arguments. Global `--root /path/to/project` goes before the command. JSON output is available for `list`, `recall`, and `check`.

## Limits that matter

- Matching uses literal shell-token sequences and path globs. It is **not a full shell interpreter or a security sandbox**. Aliases, variables, command substitutions, scripts and alternative tools can behave differently. A phrase can match arguments to another program. Review your examples.
- A reminder adds context. It does not stop the current tool call. Use an explicit block only where the trigger itself is the unwanted operation.
- Bad rules are reported by `check` and skipped by the hook. Invalid hook input returns no decision. This is deliberately unsuitable as your sole safety control.
- Up to three matching lessons are shown, with blocks first and an omitted count. Review all rules with `list`.
- Rules can contain sensitive instructions. Matching rules are sent to the agent host and can enter its transcript or model context. Local storage does not make the host local.
- This is an early release. No benchmark claim is made about productivity, token savings, or error reduction.

## Development

```sh
python3 -B -m unittest discover -s tests -v
```

The tests exercise real CLI subprocesses, isolated files, installed hook commands, malformed data, privacy boundaries, and positive/negative matching. No credentials or paid models are needed.

If Brain helps, contribute a **synthetic** lesson and a failing example it catches. Please never upload a real transcript, credential, or internal project configuration.
