"""Optional Codex skill installation and an offline, reproducible first lesson."""
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

from .core import LessonError, check, safe_path
from .hooks import MANIFEST, SETTINGS, hook, install, read_object, uninstall, write_object

SKILL_DIR = ".agents/skills/brain-remember"
SKILL_FILES = ("SKILL.md", "agents/openai.yaml", ".gitignore")


def skill_contents():
    resources = Path(__file__).resolve().parent / "data/brain-remember"
    command = shlex.join([sys.executable, "-I", str(Path(__file__).resolve().with_name("entry.py"))])
    return {name: (resources / ("gitignore" if name == ".gitignore" else name)).read_text(encoding="utf-8").replace("{{BRAIN_LESSONS_COMMAND}}", command).encode("utf-8")
            for name in SKILL_FILES}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def manage_codex(root, *, remove):
    paths = {name: safe_path(root, f"{SKILL_DIR}/{name}") for name in SKILL_FILES}
    manifest_path = safe_path(root, MANIFEST)
    settings_path = safe_path(root, SETTINGS["codex"])
    manifest = read_object(manifest_path)
    owned = manifest.get("codex_skill")
    if owned is not None:
        if not isinstance(owned, dict) or set(owned) != set(SKILL_FILES):
            raise LessonError("Invalid Codex skill ownership record; files unchanged")
        for name, path in paths.items():
            if not path.is_file() or digest(path.read_bytes()) != owned[name]:
                raise LessonError("Managed Codex skill was edited or removed; preserve your edits and resolve the conflict before retrying")
    elif not remove and any(path.exists() for path in paths.values()):
        raise LessonError("An unowned brain-remember skill exists; refusing to overwrite it")
    contents = {} if remove else skill_contents()
    tracked = [settings_path, manifest_path, *paths.values()]
    before = {path: path.read_bytes() if path.exists() else None for path in tracked}
    missing_directories = set()
    for path in tracked:
        directory = path.parent
        while directory != root:
            if not directory.exists():
                missing_directories.add(directory)
            directory = directory.parent
    try:
        message = uninstall(root, "codex") if remove else install(root, "codex")
        current = read_object(manifest_path)
        if remove and owned is not None:
            for path in paths.values():
                path.unlink()
            current.pop("codex_skill", None)
        elif not remove:
            for name, data in contents.items():
                if before[paths[name]] != data:
                    write_bytes(paths[name], data)
            current["codex_skill"] = {name: digest(data) for name, data in contents.items()}
        if set(current) <= {"schema_version"}:
            if manifest_path.exists():
                manifest_path.unlink()
        elif current != read_object(manifest_path):
            write_object(manifest_path, current)
    except (OSError, LessonError):
        # Restore only changed files. This also handles upgrading a hook-only install.
        for path, data in reversed(list(before.items())):
            now = path.read_bytes() if path.exists() else None
            if now != data:
                if data is None:
                    path.unlink()
                else:
                    write_bytes(path, data)
        # An empty .brain is still a project-root marker. Leaving it behind after
        # a failed nested install would suppress rules from the parent project.
        for directory in sorted(missing_directories, key=lambda p: len(p.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError as exc:
                if exc.errno not in (errno.ENOENT, errno.ENOTEMPTY, errno.EEXIST):
                    raise
        raise
    if remove:
        return message + " Managed brain-remember skill removed if present; lessons and other skills kept."
    return message + "\nSkill installed: .agents/skills/brain-remember. In Codex, use $brain-remember followed by your correction."


def generated_demo(*, as_json=False):
    with tempfile.TemporaryDirectory(prefix="brain-generated-demo-") as temporary:
        root = Path(temporary).resolve()
        rule = {"schema_version": 1, "id": "generated-client", "title": "Edit the schema, then regenerate",
                "instruction": "Do not edit src/generated/ directly. Change schema/api.json, then regenerate the client.",
                "action": "block", "enabled": True,
                "match": {"tools": ["Edit", "Write"], "commands": [], "paths": ["src/generated/*"]},
                "examples": {"match": [{"tool": "Write", "path": "src/generated/client.py"}],
                             "miss": [{"tool": "Write", "path": "src/main.py"}]}}
        directory = root / ".brain/lessons"
        directory.mkdir(parents=True)
        (directory / "generated-client.json").write_text(json.dumps(rule), encoding="utf-8")
        calls = []
        for path in ("src/generated/client.py", "src/main.py"):
            patch = f"*** Begin Patch\n*** Add File: {path}\n+value = 1\n*** End Patch"
            payload = {"hook_event_name": "PreToolUse", "cwd": str(root), "tool_name": "apply_patch", "tool_input": {"command": patch}}
            output, errors = io.StringIO(), io.StringIO()
            hook(root, io.StringIO(json.dumps(payload)), output, errors, adapter="codex")
            if errors.getvalue():
                raise LessonError("Demo hook failed")
            decision = json.loads(output.getvalue())["hookSpecificOutput"] if output.getvalue() else {}
            calls.append({"path": path, "decision": decision.get("permissionDecision", "none"),
                          "reason": decision.get("permissionDecisionReason", "")})
        result = {"scenario": "generated-client", "model_called": False, "tools_executed": False,
                  "checks": check(root), "calls": calls}
        if result["checks"]["problems"] or [c["decision"] for c in calls] != ["deny", "none"]:
            raise LessonError("Demo did not produce the expected decisions")
        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print("BRAIN LESSONS / GENERATED CLIENT\n")
            print("1. Save: don't edit src/generated/; change schema/api.json instead.")
            print("2. Check: 1 rule, 2 examples, 0 problems.")
            print("3. apply_patch -> src/generated/client.py: DENY")
            print("   Source: .brain/lessons/generated-client.json\n   Fix: change schema/api.json, then regenerate.")
            print("4. apply_patch -> src/main.py: no Brain decision; host permissions still apply.")
            print("\nScripted offline replay using the actual hook handler. No model or tool execution. Your project was not changed.")
