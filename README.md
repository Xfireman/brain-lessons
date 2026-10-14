# Brain Lessons

**Turn recurring corrections into checks that run when your coding agent acts.**

For project rules such as “edit the schema before regenerating the client” or “use this project's test runner,” Brain Lessons can surface the relevant instruction at the tool call and, when you explicitly choose `block`, refuse a matching operation.

It packages rule storage, matching, examples, and host integration into one small tool. **It is an early rule-execution component:** saving a lesson is explicit; it does not automatically learn from conversations.

Codex first · Claude Code supported · Local files · No model calls · Python 3.10+

[中文](README.zh-CN.md) · [Rule format](docs/rules.md) · [Privacy & limits](SECURITY.md) · [Contribute](CONTRIBUTING.md)

## A concrete problem it can help with

Suppose `src/generated/` is produced from `schema/api.json`. Direct edits to generated files will disappear the next time the client is regenerated. You have already explained this convention, but the agent proposes another patch to a generated file.

After you save the matching rule and enable the integration:

```text
Codex proposes an apply_patch edit to src/generated/client.py
  → Brain matches the generated-client rule
  → The host refuses this patch
  → The agent receives the reason and the rule's source:
    “Update schema/api.json, then regenerate the client.”
```

The immediate benefit is a repeatable check on that known mistake. The agent still has to choose the next correct action. A rule can also use `remind` to supply context while letting the current call continue.

This example describes a matching tool call. It does not prevent every way of changing a file: an arbitrary shell script is outside this file-rule check.

## Why not just tell Codex to remember?

For preferences and general instructions, **telling Codex to remember is usually the simpler choice**. Memory and `AGENTS.md` can persist too; persistence alone is not Brain's differentiator.

- **Stored instructions** inform the model, which then has to apply them to its actions.
- **A Brain `block` rule** is checked by code at the tool boundary. With the hook installed, trusted, and enabled, the host rejects a matching call.
- **A Brain `remind` rule** supplies the relevant instruction at that moment. It does not enforce compliance.

You can also ask Codex to write equivalent hooks or checks directly. Brain packages that work into a shared format, repeatable validation, and reversible integrations; it does not give Codex an exclusive new ability.

## When it earns its place

Use it when the same mistake recurs, the triggering command or file pattern is clear, and you want:

- **A check at the relevant action:** a generated-file patch or a known wrong command.
- **Evidence you can inspect:** the matching lesson and its source are shown; `check` runs your positive and negative examples.
- **Rules you can maintain:** ordinary JSON files that you can review, version, and reuse after checking their assumptions in the new project.
- **A small integration to maintain:** the same lesson store works with Codex and Claude Code, with separate install/uninstall controls.

For “reply in Chinese,” broad judgment calls such as “be more careful,” or occasional reminders, start with normal agent instructions. If you already maintain equivalent hooks and checks, keeping those may be simpler.

Brain itself needs no API key, database, or background service. Your coding agent keeps its normal setup, and selected lessons still enter that host's context; see [privacy boundaries](SECURITY.md).

**What this version does today:** you or your agent explicitly write lessons. The installed hook loads matching rules during tool calls. It does not archive conversations, automatically extract corrections, or replace a full personal knowledge system. There are no measured claims here about productivity, token savings, or error reduction.

## Try the mechanism first

Clone or download this repository, then run from its directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/brain-lessons demo
```

The offline demo uses a simpler test-runner rule: `npm test` is blocked, while `pnpm test` gets no Brain decision. It exercises the Codex adapter in a temporary project, without calling a model, executing those shell commands, or changing your project. It is a mechanism demo, not a recording of an agent learning on its own.

## Use it in a project

The workflow is **save one rule → preview its matches → install and trust the hook once → work normally**. Later lesson changes are loaded on subsequent tool calls; they do not require reinstalling the integration.

### 1. Make the CLI available

To use the installed CLI in your own project, add this virtual environment to the current shell's PATH before changing directories:

```sh
export PATH="$PWD/.venv/bin:$PATH"
cd /path/to/your/project
brain-lessons init
```

Keep the virtual environment in place while its hook is installed.

If Codex cannot find `brain-lessons`, give it the absolute path to `.venv/bin/brain-lessons` in the installation directory; a desktop app may not inherit this terminal's PATH.

### 2. Save a rule yourself, or ask Codex to do it

You do not have to type every `learn` command yourself. With the CLI available in the project, you can give Codex this request:

> Use the installed `brain-lessons` CLI to save a project rule that blocks direct patch edits to `src/generated/`. The source of truth is `schema/api.json`; changes belong there before regenerating the client. Include an example that should match and one that should not, run `brain-lessons check`, and show me the saved rule and its matching scope.

This is a request for Codex to operate the existing CLI, not a built-in automatic learning feature. Saying “remember this” alone does not create a Brain rule. Review the proposed scope before connecting or relying on it. Adapt these example paths to your project.

The equivalent manual commands are:

```sh
brain-lessons learn generated-client \
  --title "Generated clients follow the schema" \
  --instruction "src/generated/ is produced from schema/api.json. Update the schema, then regenerate the client." \
  --tool Edit --tool Write \
  --path "src/generated/*" \
  --sample-path "src/generated/client.py" \
  --miss-path "src/main.py" \
  --action block

brain-lessons check
brain-lessons recall --tool Edit --path src/generated/client.py
```

Your correction lives in `.brain/lessons/generated-client.json`. In an otherwise empty lesson store, `check` should report two examples and zero problems; `recall` should show this block rule and its source without executing an edit. Edit the file directly, review it in Git, or set `enabled` to `false`. Learning the same ID again refuses to overwrite it.

`remind` is the default action. `block` must be chosen explicitly. Preview matching rules before installing the hook.

### 3. Connect Codex once for this project

From the project where the rules should apply:

```sh
brain-lessons install codex
```

This adds one `PreToolUse` hook to **project-local** `.codex/hooks.json`, preserving other hooks and settings. It handles Codex shell calls and `apply_patch`, including multiple files and both sides of a move.

Start a new Codex session in this project. The project must be trusted, hooks must be enabled, and you must **review and trust the exact hook in `/hooks`** before it runs. If you disabled hooks, start the CLI with `codex --enable hooks`. Installing Brain does not grant hook trust or change your global Codex configuration. Changed hook definitions need review again.

After trust is granted, work with Codex normally. There is no extra Brain command to run before each edit; the host invokes the hook. Only defined matches trigger a lesson.

To remove the integration while keeping your lessons:

```sh
brain-lessons uninstall codex
```

Live model obedience is a separate outcome: a reminder is additional context, not a guarantee that the agent will change its next action. A block returns the host's explicit `deny` decision. Brain never returns an `allow` decision and never grants permissions.

See the [official Codex hook contract](https://learn.chatgpt.com/docs/hooks). Automatic installation currently targets macOS and Linux.

## Claude Code support

```sh
brain-lessons install claude-code
# Later, to remove only the Claude Code integration:
brain-lessons uninstall claude-code
```

Claude Code uses `.claude/settings.local.json`. Codex and Claude Code share the lesson store but install and uninstall independently. Start a new session and inspect `/hooks` after installation.

See the [official Claude Code hook contract](https://code.claude.com/docs/en/hooks#pretooluse-decision-control). Other agents can call `recall` explicitly; native integrations are provided for Codex and Claude Code.

## Commands

- `init` — create the local store without overwriting existing files.
- `learn` — save a correction with triggers and examples.
- `list` — inspect the complete rule set.
- `recall` — preview matching rules without running the proposed command.
- `check` — validate rules and run their positive/negative examples.
- `install codex` / `uninstall codex` — manage the Codex project hook; `claude-code` is also supported.
- `demo` — see the complete offline example.

Use `--help` for arguments. Global `--root /path/to/project` goes before the command. JSON output is available for `list`, `recall`, and `check`.

## Limits that matter

- Matching uses literal shell-token sequences and path globs. It is **not a full shell interpreter or a security sandbox**. Aliases, variables, command substitutions, scripts and alternative tools can behave differently. A phrase can match arguments to another program. Review your examples.
- Codex file rules inspect `apply_patch` operations, not files changed indirectly by arbitrary shell commands. A later `write_stdin` call does not trigger another pre-tool check for the original shell command.
- A reminder adds context. It does not stop the current tool call. Use an explicit block only where the trigger itself is the unwanted operation.
- Bad rules are reported by `check` and skipped by the hook. Invalid hook input returns no decision. This is deliberately unsuitable as your sole safety control.
- Up to three matching lessons are shown, with blocks first and an omitted count. Review all rules with `list`.
- Rules can contain sensitive instructions. Matching rules are sent to the agent host and can enter its transcript or model context. Local storage does not make the host local.
- This is an early release. No benchmark claim is made about productivity, token savings, or error reduction.

## Development

Native smoke tests use **Codex CLI 0.162.1 on macOS** with a local synthetic response server. With rules disabled, the fixture commands and patch execute; with rules enabled, Codex blocks the selected shell call and patch while a permitted command still runs, and a reminder reaches the next model request. This verifies actual host behavior without a paid model call. Other Codex surfaces need the compatible hook runtime and access to the installed Python executable.

```sh
python3 -B -m unittest discover -s tests -v
```

The tests exercise real CLI subprocesses, isolated files, installed hook commands, malformed data, privacy boundaries, and positive/negative matching. No credentials or paid models are needed.

With Codex CLI 0.162.1 on PATH, run the native host smoke test:

```sh
python3 -B tests/native_codex.py
```

It creates an isolated Codex home, records trust only for the reviewed fixture hook's exact hash, and uses a loopback response server. It does not use your login, modify your real Codex settings, or measure a model's intelligence. The CI runs this test separately from the CLI suite.

The native CI job runs on macOS with Codex's default workspace filesystem sandbox and tool network isolation. Linux runs the CLI integration suite; native Linux enforcement has not been validated for this release because the hosted Ubuntu worker cannot start Codex's bubblewrap namespaces. The test does not relax the sandbox or silently switch backends. Normal installation never changes sandbox or network settings.

If Brain helps, contribute a **synthetic** lesson and a failing example it catches. Please never upload a real transcript, credential, or internal project configuration.
