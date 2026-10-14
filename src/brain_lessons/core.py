"""Read local rule data and match tool calls. Never execute lesson content."""
import fnmatch
import json
import os
from pathlib import Path
import re
import shlex

MAX_RULE_BYTES = 65536
MAX_LESSONS = 500
MAX_SHOWN = 3
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")


class LessonError(ValueError):
    pass


def safe_path(root: Path, relative: str) -> Path:
    """Reject symlink components below an already resolved project root."""
    path = root
    for part in Path(relative).parts:
        if part in ("..", "/"):
            raise LessonError("Path must stay inside the project")
        path = path / part
        if path.is_symlink():
            raise LessonError("Symlinked project configuration is not supported")
    return path


def find_root(cwd: Path) -> Path:
    start = cwd.resolve()
    for path in (start, *start.parents):
        if (path / ".brain").exists() or (path / ".brain").is_symlink():
            return path
        if (path / ".git").exists():
            return path
    return start


def clean_text(value, field, maximum, *, multiline=False):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise LessonError(f"Invalid {field}")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise LessonError(f"Invalid Unicode in {field}") from None
    allowed = "\n\t" if multiline else ""
    if any((ord(c) < 32 and c not in allowed) or ord(c) == 127 for c in value):
        raise LessonError(f"Control characters in {field}")
    return value


def text_list(value, field, *, maximum=20):
    if not isinstance(value, list) or len(value) > maximum:
        raise LessonError(f"Invalid {field} list")
    return [clean_text(x, field, 256) for x in value]


def command_tokens(command: str):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    return list(lexer)


def validate(value, filename=None):
    if not isinstance(value, dict) or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise LessonError("Expected schema_version 1")
    identity = value.get("id")
    if not isinstance(identity, str) or not ID.fullmatch(identity):
        raise LessonError("Use a lowercase alphanumeric lesson id with optional hyphens")
    if filename is not None and filename != identity + ".json":
        raise LessonError("Filename must equal lesson id plus .json")
    clean_text(value.get("title"), "title", 120)
    clean_text(value.get("instruction"), "instruction", 1200, multiline=True)
    if value.get("action") not in ("remind", "block"):
        raise LessonError("Action must be remind or block")
    if type(value.get("enabled")) is not bool:
        raise LessonError("Enabled must be a boolean")
    match = value.get("match")
    if not isinstance(match, dict):
        raise LessonError("Missing match object")
    tools = text_list(match.get("tools"), "tools")
    if not tools or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t) for t in tools):
        raise LessonError("Supply at least one tool name")
    commands = text_list(match.get("commands"), "commands")
    paths = text_list(match.get("paths"), "paths")
    if not commands and not paths:
        raise LessonError("Supply a command phrase or path glob")
    for command in commands:
        try:
            tokens = command_tokens(command)
        except ValueError:
            raise LessonError("Unbalanced quoting in command phrase") from None
        if not tokens:
            raise LessonError("Empty command phrase")
    for pattern in paths:
        if pattern.startswith(("/", "~")) or ".." in pattern.split("/") or "\\" in pattern:
            raise LessonError("Path globs must be project-relative with forward slashes")
    examples = value.get("examples")
    if not isinstance(examples, dict):
        raise LessonError("Missing examples object")
    for outcome in ("match", "miss"):
        cases = examples.get(outcome)
        if not isinstance(cases, list) or len(cases) > 50:
            raise LessonError("Invalid example list")
        for case in cases:
            if not isinstance(case, dict):
                raise LessonError("Invalid example")
            clean_text(case.get("tool"), "example tool", 80)
            if not (case.get("command") or case.get("path")):
                raise LessonError("An example needs a command or path")
            for field in ("command", "path"):
                if field in case:
                    clean_text(case[field], "example " + field, 2048, multiline=field == "command")
    return value


def load_lessons(root: Path):
    lessons, problems = [], []
    try:
        directory = safe_path(root, ".brain/lessons")
    except LessonError as exc:
        return [], [str(exc)]
    try:
        with os.scandir(directory) as entries:
            files = sorted(Path(entry.path) for entry in entries if entry.name.endswith(".json"))
    except FileNotFoundError:
        return [], []
    except NotADirectoryError:
        return [], ["Lesson store must be a directory"]
    except OSError:
        return [], ["Cannot list lesson store"]
    if len(files) > MAX_LESSONS:
        return [], [f"More than {MAX_LESSONS} lessons; split the project rule set"]
    for path in files:
        # Do not print filenames from invalid/untrusted data in hook diagnostics.
        label = path.name if ID.fullmatch(path.stem) else "invalid filename"
        try:
            if path.is_symlink() or not path.is_file():
                raise LessonError("Lesson must be a regular file, not a symlink")
            with path.open("rb") as source:
                raw = source.read(MAX_RULE_BYTES + 1)
            if len(raw) > MAX_RULE_BYTES:
                raise LessonError("Lesson exceeds 64 KiB")
            value = validate(json.loads(raw), path.name)
            lessons.append(value)
        except (OSError, UnicodeError, ValueError, RecursionError) as exc:
            reason = str(exc) if isinstance(exc, LessonError) else "Unreadable or invalid JSON"
            problems.append(f"{label}: {reason}")
    return lessons, problems


def relative_path(root: Path, path: str, cwd=None):
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = (cwd or root) / candidate
    try:
        return candidate.resolve().relative_to(root).as_posix()
    except (ValueError, OSError, RuntimeError):
        return None


def matches(lesson, root: Path, tool: str, command="", path="", cwd=None, *, include_disabled=False):
    if not include_disabled and not lesson["enabled"]:
        return False
    match = lesson["match"]
    if tool not in match["tools"]:
        return False
    if command and match["commands"]:
        try:
            tokens = command_tokens(command)
        except ValueError:
            tokens = []
        for phrase in match["commands"]:
            expected = command_tokens(phrase)
            if any(tokens[i:i + len(expected)] == expected for i in range(len(tokens) - len(expected) + 1)):
                return True
    relative = relative_path(root, path, cwd)
    if relative is not None:
        return any(fnmatch.fnmatchcase(relative, pattern) for pattern in match["paths"])
    return False


def recall(root, tool, command="", path="", cwd=None):
    lessons, problems = load_lessons(root)
    hits = [x for x in lessons if matches(x, root, tool, command, path, cwd)]
    hits.sort(key=lambda x: (x["action"] != "block", x["id"]))
    decision = "block" if any(x["action"] == "block" for x in hits) else ("remind" if hits else "none")
    shown = [{"id": x["id"], "title": x["title"], "instruction": x["instruction"],
              "action": x["action"], "source": f'.brain/lessons/{x["id"]}.json'} for x in hits[:MAX_SHOWN]]
    return {"decision": decision, "matches": shown, "omitted": max(0, len(hits) - MAX_SHOWN), "problems": problems}


def context(result):
    parts = ["Brain Lessons: project rules selected for this tool call."]
    for lesson in result["matches"]:
        parts.append(f'[{lesson["action"]}] {lesson["title"]} ({lesson["source"]})\n{lesson["instruction"]}')
    if result["omitted"]:
        parts.append(f'{result["omitted"]} additional matching lesson(s) omitted; run brain-lessons list --json to review all rules.')
    return "\n\n".join(parts)


def check(root):
    lessons, problems = load_lessons(root)
    checked = 0
    for lesson in lessons:
        if not lesson["examples"]["match"]:
            problems.append(f'{lesson["id"]}: no positive example; add one before relying on this rule')
        for outcome, expected in (("match", True), ("miss", False)):
            for i, case in enumerate(lesson["examples"][outcome], 1):
                checked += 1
                actual = matches(lesson, root, case["tool"], case.get("command", ""), case.get("path", ""), include_disabled=True)
                if actual != expected:
                    problems.append(f'{lesson["id"]}: {outcome} example {i} failed')
    return {"lessons": len(lessons), "examples_checked": checked, "problems": problems}
