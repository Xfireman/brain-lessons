"""Translate documented host tool inputs into portable lesson events."""
from .core import LessonError

ADAPTERS = ("codex", "claude-code")
CODEX_SHELL = {"Bash", "exec_command", "functions.exec_command"}


def text_field(value, name):
    text = value.get(name, "")
    if not isinstance(text, str):
        raise LessonError("Invalid tool field")
    return text


def working_directory(adapter, tool, value, working):
    if adapter == "codex" and tool in CODEX_SHELL and "workdir" in value:
        directory = text_field(value, "workdir")
        if directory:
            return (working / directory).resolve()
    return working


def patch_paths(patch):
    """Extract operation headers, not the file contents prefixed by +, - or space."""
    lines = patch.splitlines()
    if len(lines) < 3 or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise LessonError("Unrecognized patch envelope")
    operations = []
    current = None
    for line in lines[1:-1]:
        for kind in ("Add", "Update", "Delete"):
            prefix = f"*** {kind} File: "
            if line.startswith(prefix):
                path = line[len(prefix):]
                if not path:
                    raise LessonError("Empty patch path")
                current = kind
                operations.append(("Write" if kind == "Add" else "Edit", path))
                break
        else:
            prefix = "*** Move to: "
            if line.startswith(prefix):
                destination = line[len(prefix):]
                if current != "Update" or not destination:
                    raise LessonError("Invalid patch move")
                operations.append(("Edit", destination))
    if not operations:
        raise LessonError("Patch has no file operations")
    return operations


def normalize(adapter, tool, value, working):
    if adapter == "codex" and tool in CODEX_SHELL:
        field = "command" if "command" in value else "cmd"
        return [{"tool": "Bash", "command": text_field(value, field), "cwd": working}]
    if adapter == "codex" and tool in ("apply_patch", "functions.apply_patch"):
        field = "command" if "command" in value else "patch"
        operations = patch_paths(text_field(value, field))
        calls = []
        for logical_tool, path in operations:
            calls.extend([{"tool": logical_tool, "path": path, "cwd": working},
                          {"tool": "apply_patch", "path": path, "cwd": working}])
        return calls
    return [{"tool": tool, "command": text_field(value, "command"),
             "path": text_field(value, "file_path"), "cwd": working}]
