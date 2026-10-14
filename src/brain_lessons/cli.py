"""Small, explicit user commands. All writes stay in the chosen project."""
import argparse
import io
import json
from pathlib import Path
import sys
import tempfile

from . import __version__
from .core import LessonError, check, context, find_root, load_lessons, recall, safe_path, validate
from .hooks import hook, install, uninstall


def parser():
    p = argparse.ArgumentParser(prog="brain-lessons", description="Turn corrections into project rules that show up when you act.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--root", type=Path, help="Project directory (default: nearest .brain or Git root)")
    sub = p.add_subparsers(dest="verb", required=True)
    sub.add_parser("init", help="Create a local lesson store without overwriting files")
    learn = sub.add_parser("learn", help="Save one correction as a new rule")
    learn.add_argument("id")
    learn.add_argument("--title", required=True)
    learn.add_argument("--instruction", required=True)
    learn.add_argument("--tool", action="append", default=[])
    learn.add_argument("--command", action="append", default=[], help="Consecutive shell tokens to match (not a regex)")
    learn.add_argument("--path", action="append", default=[], help="Project-relative path glob")
    learn.add_argument("--action", choices=["remind", "block"], default="remind")
    for option in ("sample-command", "miss-command", "sample-path", "miss-path"):
        learn.add_argument("--" + option, action="append", default=[])
    ls = sub.add_parser("list", help="List local lessons and validation problems")
    ls.add_argument("--json", action="store_true")
    rec = sub.add_parser("recall", help="Preview rules for a tool call without executing it")
    rec.add_argument("--tool", required=True)
    rec.add_argument("--command", default="")
    rec.add_argument("--path", default="")
    rec.add_argument("--json", action="store_true")
    chk = sub.add_parser("check", help="Validate rule data and authored positive/negative examples")
    chk.add_argument("--json", action="store_true")
    for verb in ("install", "uninstall"):
        cmd = sub.add_parser(verb, help=verb.capitalize() + " the project-local hook")
        cmd.add_argument("adapter", choices=["claude-code"])
    sub.add_parser("hook", help="Read a Claude Code PreToolUse event on stdin")
    sub.add_parser("demo", help="Run a synthetic, offline demo in a disposable directory")
    return p


def init(root):
    directory = safe_path(root, ".brain/lessons")
    directory.mkdir(parents=True, exist_ok=True)
    ignore = safe_path(root, ".brain/.gitignore")
    if not ignore.exists():
        with ignore.open("x", encoding="utf-8") as target:
            target.write("# Local machine data; lessons remain shareable by choice.\ninstallation.json\n")
    print("Ready: .brain/lessons/. Add your first correction with brain-lessons learn.")


def learn(root, args):
    tools = args.tool or (["Bash"] if args.command else ["Read", "Edit", "Write"])
    examples = {"match": [], "miss": []}
    for key, values, field, tool in (
        ("match", args.sample_command, "command", "Bash"),
        ("miss", args.miss_command, "command", "Bash"),
        ("match", args.sample_path, "path", "Edit"),
        ("miss", args.miss_path, "path", "Edit"),
    ):
        selected_tool = tool if tool in tools else tools[0]
        examples[key].extend({"tool": selected_tool, field: value} for value in values)
    value = validate({"schema_version": 1, "id": args.id, "title": args.title,
                      "instruction": args.instruction, "enabled": True, "action": args.action,
                      "match": {"tools": tools, "commands": args.command, "paths": args.path}, "examples": examples})
    path = safe_path(root, f".brain/lessons/{value['id']}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    except FileExistsError:
        raise LessonError("Lesson already exists; edit its JSON explicitly instead of overwriting") from None
    print(f"Saved .brain/lessons/{value['id']}.json ({value['action']}). Run brain-lessons check.")


def demo():
    with tempfile.TemporaryDirectory(prefix="brain-lessons-demo-") as temporary:
        root = Path(temporary).resolve()
        rule = {"schema_version": 1, "id": "project-tests", "title": "Use this project's test runner",
                "instruction": "This project uses pnpm test. The npm test command is not configured.",
                "action": "block", "enabled": True,
                "match": {"tools": ["Bash"], "commands": ["npm test"], "paths": []},
                "examples": {"match": [{"tool": "Bash", "command": "npm test"}],
                             "miss": [{"tool": "Bash", "command": "pnpm test"}]}}
        directory = root / ".brain/lessons"
        directory.mkdir(parents=True)
        (directory / "project-tests.json").write_text(json.dumps(rule), encoding="utf-8")
        print("BRAIN LESSONS / OFFLINE DEMO\n")
        print("1. Correction saved: this project uses pnpm test.")
        for command in ("npm test", "pnpm test"):
            payload = {"hook_event_name": "PreToolUse", "cwd": str(root), "tool_name": "Bash", "tool_input": {"command": command}}
            output = io.StringIO()
            hook(root, io.StringIO(json.dumps(payload)), output, sys.stderr)
            if output.getvalue():
                body = json.loads(output.getvalue())["hookSpecificOutput"]
                assert body["permissionDecision"] == "deny"
                print(f"2. Tool proposes `{command}` -> BLOCK\n   Source: .brain/lessons/project-tests.json\n   Correction: use pnpm test.")
            else:
                print(f"3. Tool proposes `{command}` -> no Brain decision; host permissions still apply.")
        print("\nNo model was called. No shell command was executed. Your project was not changed.")


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.verb == "demo":
            demo()
            return 0
        root = args.root.resolve() if args.root else find_root(Path.cwd())
        if not root.is_dir():
            raise LessonError("Project directory does not exist")
        if args.verb == "hook":
            return hook(root if args.root else None, sys.stdin, sys.stdout, sys.stderr)
        if args.verb == "init":
            init(root)
        elif args.verb == "learn":
            learn(root, args)
        elif args.verb == "recall":
            result = recall(root, args.tool, args.command, args.path, root if args.root else Path.cwd())
            print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else
                  context(result) if result["matches"] else "No matching lessons.")
            if result["problems"] and not args.json:
                print("Some rules are invalid; run brain-lessons check.", file=sys.stderr)
        elif args.verb == "list":
            lessons, problems = load_lessons(root)
            if args.json:
                print(json.dumps({"lessons": lessons, "problems": problems}, indent=2, ensure_ascii=False))
            else:
                for item in lessons:
                    print(f'{item["id"]}: {item["title"]} [{item["action"]}, {"enabled" if item["enabled"] else "disabled"}]')
                for problem in problems:
                    print(problem, file=sys.stderr)
                if not lessons:
                    print("No lessons found. Run brain-lessons learn to add one.")
            return int(bool(problems))
        elif args.verb == "check":
            result = check(root)
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(f'{result["lessons"]} lesson(s), {result["examples_checked"]} example(s), {len(result["problems"])} problem(s).')
                for problem in result["problems"]:
                    print(problem)
            return int(bool(result["problems"]))
        elif args.verb == "install":
            print(install(root))
        elif args.verb == "uninstall":
            print(uninstall(root))
        return 0
    except (LessonError, OSError) as exc:
        message = str(exc) if isinstance(exc, LessonError) else "Filesystem operation failed; check local permissions"
        print("brain-lessons: " + message, file=sys.stderr)
        return 1
