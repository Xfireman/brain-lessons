"""Claude Code's documented PreToolUse protocol and project-local installer."""
import copy
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile

from .adapters import normalize, working_directory
from .core import LessonError, context, find_root, recall_many, safe_path

MAX_PAYLOAD = 262144
SETTINGS = {"codex": ".codex/hooks.json", "claude-code": ".claude/settings.local.json"}
MANIFEST = ".brain/installation.json"
SLOT = {"codex": "codex_entry", "claude-code": "entry"}


def hook(root, stdin, stdout, stderr, adapter="claude-code"):
    try:
        raw = stdin.read(MAX_PAYLOAD + 1)
        if len(raw) > MAX_PAYLOAD:
            raise LessonError("Oversized hook payload")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise LessonError("Invalid hook object")
        event = payload.get("hook_event_name")
        if event and event != "PreToolUse":
            return 0
        value = payload.get("tool_input")
        tool, cwd = payload.get("tool_name"), payload.get("cwd")
        if event != "PreToolUse" or not isinstance(value, dict) or not isinstance(tool, str) or not isinstance(cwd, str):
            raise LessonError("Invalid hook fields")
        working = Path(cwd).resolve()
        working = working_directory(adapter, tool, value, working)
        if not working.is_dir():
            raise LessonError("Invalid working directory")
        project = root or find_root(working)
        if not working.is_relative_to(project):
            return 0
        # A hook installed in a parent project must not inject into a nested repo.
        if find_root(working) != project:
            return 0
        result = recall_many(project, normalize(adapter, tool, value, working))
        if result["problems"]:
            print("brain-lessons: invalid local rules; run brain-lessons check", file=stderr)
        if not result["matches"]:
            return 0
        output = {"hookEventName": "PreToolUse"}
        if result["decision"] == "block":
            output.update(permissionDecision="deny", permissionDecisionReason=context(result))
        else:
            output["additionalContext"] = context(result)
        print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False), file=stdout)
    except (ValueError, OSError, RuntimeError):
        # Payloads can contain credentials. Never include input or exception text.
        print("brain-lessons: could not process hook input; no decision returned", file=stderr)
    return 0


def read_object(path):
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            data = handle.read(1048577)
        if len(data) > 1048576:
            raise LessonError("Configuration exceeds 1 MiB")
        value = json.loads(data)
    except (OSError, ValueError):
        raise LessonError("Cannot read existing configuration; leave it unchanged and fix its JSON first") from None
    if not isinstance(value, dict):
        raise LessonError("Existing configuration must be a JSON object")
    return value


def write_object(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def hook_groups(settings):
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise LessonError("Existing hooks must be an object")
    groups = hooks.setdefault("PreToolUse", [])
    if not isinstance(groups, list):
        raise LessonError("Existing PreToolUse hooks must be a list")
    return groups


def install(root, adapter="claude-code"):
    if os.name != "posix":
        raise LessonError("Automatic hook installation currently supports macOS and Linux only")
    settings_path = safe_path(root, SETTINGS[adapter])
    manifest_path = safe_path(root, MANIFEST)
    settings = read_object(settings_path)
    manifest = read_object(manifest_path)
    groups = hook_groups(settings)
    entry_script = str(Path(__file__).resolve().with_name("entry.py"))
    command = shlex.join([sys.executable, "-I", entry_script, "--root", str(root), "hook", "--adapter", adapter])
    matcher = "^(Bash|apply_patch)$" if adapter == "codex" else "Bash|Read|Edit|Write|MultiEdit"
    entry = {"matcher": matcher, "hooks": [{"type": "command", "command": command, "timeout": 5}]}
    previous = manifest.get(SLOT[adapter])
    if previous == entry and entry in groups:
        return "Already installed; settings unchanged."
    if previous is not None:
        if previous not in groups:
            raise LessonError("Managed hook was edited or removed; restore it or remove .brain/installation.json before reinstalling")
        groups.remove(previous)
    if entry in groups:
        raise LessonError("An identical unowned hook already exists; refusing to claim it")
    groups.append(entry)
    # Roll back ownership if the settings write fails, so a retry is safe.
    manifest_existed = manifest_path.exists()
    updated_manifest = {**manifest, "schema_version": 1, SLOT[adapter]: entry}
    write_object(manifest_path, updated_manifest)
    try:
        write_object(settings_path, settings)
    except OSError:
        if manifest_existed:
            write_object(manifest_path, manifest)
        else:
            manifest_path.unlink()
        raise
    if adapter == "codex":
        return "Installed in .codex/hooks.json. Start a new Codex session in this trusted project, then review and trust the exact hook in /hooks. Hooks must be enabled."
    return "Installed in .claude/settings.local.json. Start a new Claude Code session and review /hooks."


def uninstall(root, adapter="claude-code"):
    settings_path = safe_path(root, SETTINGS[adapter])
    manifest_path = safe_path(root, MANIFEST)
    if not manifest_path.exists():
        return "No managed installation found; settings unchanged."
    manifest = read_object(manifest_path)
    previous = manifest.get(SLOT[adapter])
    if previous is None:
        return "No managed hook for this adapter; settings unchanged."
    if not isinstance(previous, dict):
        raise LessonError("Invalid installation record; settings unchanged")
    settings = read_object(settings_path)
    original_settings = copy.deepcopy(settings)
    groups = hook_groups(settings)
    if previous not in groups:
        raise LessonError("Managed hook changed; refusing to remove user edits")
    groups.remove(previous)
    write_object(settings_path, settings)
    updated_manifest = {key: value for key, value in manifest.items() if key != SLOT[adapter]}
    try:
        if set(updated_manifest) <= {"schema_version"}:
            manifest_path.unlink()
        else:
            write_object(manifest_path, updated_manifest)
    except OSError:
        write_object(settings_path, original_settings)
        raise
    return "Removed the managed hook. Lessons and other settings were kept."
