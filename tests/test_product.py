"""Real CLI boundaries: persistence, matching, hook protocol, and safe install."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src"


def lesson(identity="project-tests", action="remind", **changes):
    value = {
        "schema_version": 1, "id": identity, "title": "Project test command",
        "instruction": "This project uses pnpm test.", "action": action,
        "enabled": True,
        "match": {"tools": ["Bash"], "commands": ["npm test"], "paths": []},
        "examples": {
            "match": [{"tool": "Bash", "command": "npm test"}],
            "miss": [{"tool": "Bash", "command": "git status"}],
        },
    }
    value.update(changes)
    return value


class ProductTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain product ")
        self.root = Path(self.tmp.name)
        self.env = {**os.environ, "PYTHONPATH": str(SOURCE), "PYTHONDONTWRITEBYTECODE": "1"}

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args, input=None, cwd=None):
        return subprocess.run(
            [sys.executable, "-m", "brain_lessons", "--root", str(self.root), *args],
            input=input, text=True, capture_output=True, cwd=cwd or self.root,
            env=self.env, timeout=10,
        )

    def save(self, value, filename=None):
        directory = self.root / ".brain" / "lessons"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (filename or value["id"] + ".json")
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def recall(self, *args):
        p = self.cli("recall", "--json", *args)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def payload(self, command="npm test", **changes):
        value = {"hook_event_name": "PreToolUse", "cwd": str(self.root),
                 "tool_name": "Bash", "tool_input": {"command": command}}
        value.update(changes)
        return json.dumps(value)

    def test_init_and_learn_persist_without_overwrite(self):
        p = self.cli("init")
        self.assertEqual(p.returncode, 0, p.stderr)
        args = ("learn", "project-tests", "--title", "Project tests", "--instruction",
                "Use pnpm test.", "--tool", "Bash", "--command", "npm test",
                "--sample-command", "npm test", "--miss-command", "git status", "--action", "block")
        self.assertEqual(self.cli(*args).returncode, 0)
        target = self.root / ".brain/lessons/project-tests.json"
        before = target.read_bytes()
        self.assertNotEqual(self.cli(*args).returncode, 0)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.cli("init").returncode, 0)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(self.cli("check").returncode, 0)

    def test_commands_tools_and_negative_examples(self):
        self.save(lesson())
        found = self.recall("--tool", "Bash", "--command", "npm test -- --runInBand")
        self.assertEqual([x["id"] for x in found["matches"]], ["project-tests"])
        self.assertEqual(found["matches"][0]["source"], ".brain/lessons/project-tests.json")
        self.assertEqual(self.recall("--tool", "Read", "--command", "npm test")["matches"], [])
        self.assertEqual(self.recall("--tool", "Bash", "--command", "git status")["matches"], [])

    def test_path_matching_is_relative_and_cannot_escape(self):
        self.save(lesson("docker", match={"tools": ["Edit"], "commands": [],
                                          "paths": ["Dockerfile", "**/Dockerfile"]},
                         examples={"match": [{"tool": "Edit", "path": "Dockerfile"}], "miss": []}))
        self.assertEqual(len(self.recall("--tool", "Edit", "--path", str(self.root / "api/Dockerfile"))["matches"]), 1)
        self.assertEqual(self.recall("--tool", "Edit", "--path", "../Dockerfile")["matches"], [])
        self.assertEqual(self.recall("--tool", "Edit", "--path", "Dockerfile.dev")["matches"], [])

    def test_disabled_lesson_is_not_injected(self):
        self.save(lesson(enabled=False))
        self.assertEqual(self.recall("--tool", "Bash", "--command", "npm test")["matches"], [])

    def test_block_takes_priority_over_reminder_cap(self):
        for identity in ["a", "b", "c", "d"]:
            self.save(lesson(identity))
        self.save(lesson("z-block", "block"))
        result = self.recall("--tool", "Bash", "--command", "npm test")
        self.assertEqual(result["decision"], "block")
        self.assertEqual(result["matches"][0]["id"], "z-block")
        self.assertEqual(result["omitted"], 2)

    def test_invalid_schema_and_filename_mismatch_are_visible(self):
        self.save(lesson(schema_version=99))
        self.save(lesson("different"), "wrong-name.json")
        p = self.cli("check", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(len(json.loads(p.stdout)["problems"]), 2)

    def test_sample_regression_fails_check(self):
        self.save(lesson(examples={"match": [{"tool": "Bash", "command": "git status"}], "miss": []}))
        p = self.cli("check", "--json")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("project-tests", p.stdout)

    def test_missing_positive_example_is_not_certified(self):
        self.save(lesson(examples={"match": [], "miss": []}))
        self.assertNotEqual(self.cli("check").returncode, 0)

    def test_rule_symlink_is_rejected_without_reading_target(self):
        p = self.save(lesson())
        outside = self.root / "outside.json"
        outside.write_text("PRIVATE_TARGET_SENTINEL")
        p.unlink()
        p.symlink_to(outside)
        out = self.cli("check", "--json")
        self.assertNotEqual(out.returncode, 0)
        self.assertNotIn("PRIVATE_TARGET_SENTINEL", out.stdout + out.stderr)

    def test_reminder_hook_returns_context_but_never_allows(self):
        self.save(lesson())
        p = self.cli("hook", input=self.payload())
        self.assertEqual(p.returncode, 0, p.stderr)
        body = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(body["hookEventName"], "PreToolUse")
        self.assertIn("pnpm test", body["additionalContext"])
        self.assertNotIn("permissionDecision", body)

    def test_block_hook_denies_and_corrected_command_passes(self):
        self.save(lesson(action="block"))
        p = self.cli("hook", input=self.payload())
        body = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(body["permissionDecision"], "deny")
        self.assertIn("pnpm test", body["permissionDecisionReason"])
        self.assertEqual(self.cli("hook", input=self.payload("pnpm test")).stdout, "")

    def test_hook_never_echoes_sensitive_command_or_transcript(self):
        self.save(lesson(action="block"))
        raw = self.payload("npm test --credential PRIVATE_INPUT_SENTINEL", transcript_path="PRIVATE_TRANSCRIPT_SENTINEL")
        p = self.cli("hook", input=raw)
        self.assertNotIn("PRIVATE_INPUT_SENTINEL", p.stdout + p.stderr)
        self.assertNotIn("PRIVATE_TRANSCRIPT_SENTINEL", p.stdout + p.stderr)
        self.assertEqual(sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file()),
                         [".brain/lessons/project-tests.json"])

    def test_malformed_hook_is_nonblocking_and_does_not_echo(self):
        for raw in ["PRIVATE_BAD_INPUT", "[]", '{"tool_input": "PRIVATE_BAD_INPUT"}']:
            p = self.cli("hook", input=raw)
            self.assertEqual(p.returncode, 0)
            self.assertEqual(p.stdout, "")
            self.assertNotIn("PRIVATE_BAD_INPUT", p.stderr)
            self.assertTrue(p.stderr)

    def test_hook_ignores_other_events_and_outside_workspace(self):
        self.save(lesson(action="block"))
        self.assertEqual(self.cli("hook", input=self.payload(hook_event_name="PostToolUse")).stdout, "")
        self.assertEqual(self.cli("hook", input=self.payload(cwd=str(self.root.parent))).stdout, "")

    def test_install_is_idempotent_and_uninstall_preserves_user_edits(self):
        settings = self.root / ".claude/settings.local.json"
        settings.parent.mkdir()
        unrelated = {"matcher": "Read", "hooks": [{"type": "command", "command": "echo existing"}]}
        settings.write_text(json.dumps({"permissions": {"allow": ["Read"]}, "hooks": {"PreToolUse": [unrelated]}}))
        p = self.cli("install", "claude-code")
        self.assertEqual(p.returncode, 0, p.stderr)
        first = settings.read_bytes()
        self.assertEqual(self.cli("install", "claude-code").returncode, 0)
        self.assertEqual(first, settings.read_bytes())
        value = json.loads(settings.read_text())
        self.assertEqual(len(value["hooks"]["PreToolUse"]), 2)
        self.assertIn(unrelated, value["hooks"]["PreToolUse"])
        value["env"] = {"USER_SETTING": "preserved"}
        settings.write_text(json.dumps(value))
        self.assertEqual(self.cli("uninstall", "claude-code").returncode, 0)
        remaining = json.loads(settings.read_text())
        self.assertEqual(remaining["hooks"]["PreToolUse"], [unrelated])
        self.assertEqual(remaining["env"], {"USER_SETTING": "preserved"})
        self.assertEqual(remaining["permissions"], {"allow": ["Read"]})

    def test_installed_command_handles_spaces_and_runs_real_protocol(self):
        self.save(lesson(action="block"))
        self.assertEqual(self.cli("install", "claude-code").returncode, 0)
        config = json.loads((self.root / ".claude/settings.local.json").read_text())
        command = config["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        p = subprocess.run(command, shell=True, input=self.payload(), text=True, capture_output=True,
                           env=self.env, cwd=self.root, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_install_refuses_symlinked_config_directory(self):
        external = self.root / "external"
        external.mkdir()
        (self.root / ".claude").symlink_to(external, target_is_directory=True)
        self.assertNotEqual(self.cli("install", "claude-code").returncode, 0)
        self.assertEqual(list(external.iterdir()), [])

    def test_unsafe_rule_id_cannot_write_outside_store(self):
        p = self.cli("learn", "../../escape", "--title", "x", "--instruction", "x", "--command", "x")
        self.assertNotEqual(p.returncode, 0)
        self.assertFalse((self.root / "escape.json").exists())

    def test_installed_hook_cannot_be_shadowed_by_project_module(self):
        self.save(lesson(action="block"))
        self.assertEqual(self.cli("install", "claude-code").returncode, 0)
        config = json.loads((self.root / ".claude/settings.local.json").read_text())
        command = config["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        (self.root / "brain_lessons.py").write_text('print("PROJECT_MODULE_EXECUTED")\n')
        p = subprocess.run(command, shell=True, input=self.payload(), text=True, capture_output=True,
                           env=self.env, cwd=self.root, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("PROJECT_MODULE_EXECUTED", p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_decoder_failure_does_not_disable_valid_block(self):
        self.save(lesson(action="block"))
        bad = self.root / ".brain/lessons/bad.json"
        for value in ["9" * 5000, "[" * 1100 + "0" + "]" * 1100]:
            with self.subTest(kind=value[:1]):
                bad.write_text(value)
                result = self.cli("check", "--json")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertEqual(len(json.loads(result.stdout)["problems"]), 1)
                p = self.cli("hook", input=self.payload())
                self.assertEqual(json.loads(p.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertTrue(p.stderr)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses directory permissions")
    def test_failed_install_can_be_retried_after_permission_repair(self):
        directory = self.root / ".claude"
        directory.mkdir()
        directory.chmod(0o555)
        try:
            self.assertNotEqual(self.cli("install", "claude-code").returncode, 0)
        finally:
            directory.chmod(0o755)
        p = self.cli("install", "claude-code")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.cli("uninstall", "claude-code").returncode, 0)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses directory permissions")
    def test_unreadable_store_is_not_certified_as_empty(self):
        self.save(lesson(action="block"))
        directory = self.root / ".brain/lessons"
        directory.chmod(0)
        try:
            result = self.cli("check", "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(json.loads(result.stdout)["problems"])
            p = self.cli("hook", input=self.payload())
            self.assertTrue(p.stderr)
        finally:
            directory.chmod(0o755)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses directory permissions")
    def test_failed_uninstall_preserves_hook_and_can_be_retried(self):
        self.save(lesson(action="block"))
        self.assertEqual(self.cli("install", "claude-code").returncode, 0)
        settings = self.root / ".claude/settings.local.json"
        original = json.loads(settings.read_text())
        directory = self.root / ".brain"
        directory.chmod(0o555)
        try:
            self.assertNotEqual(self.cli("uninstall", "claude-code").returncode, 0)
        finally:
            directory.chmod(0o755)
        self.assertEqual(json.loads(settings.read_text()), original)
        self.assertEqual(self.cli("uninstall", "claude-code").returncode, 0)

    def test_explicit_root_interprets_relative_preview_paths_in_that_project(self):
        self.save(lesson("docker", match={"tools": ["Edit"], "commands": [], "paths": ["Dockerfile"]}))
        p = self.cli("recall", "--json", "--tool", "Edit", "--path", "Dockerfile", cwd=self.root.parent)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual([x["id"] for x in json.loads(p.stdout)["matches"]], ["docker"])

    def test_invalid_unicode_rule_is_isolated_and_normal_unicode_survives(self):
        self.save(lesson(action="block", title="项目规则 🧠", instruction="本项目使用 pnpm test。"))
        self.save(lesson("bad-unicode", title="\ud800"))
        result = self.cli("check", "--json")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(json.loads(result.stdout)["problems"]), 1)
        p = self.cli("hook", input=self.payload())
        self.assertEqual(p.returncode, 0, p.stderr)
        body = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(body["permissionDecision"], "deny")
        self.assertIn("项目规则 🧠", body["permissionDecisionReason"])

    def test_demo_does_not_modify_callers_project(self):
        p = self.cli("demo")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("BLOCK", p.stdout)
        self.assertIn("pnpm test", p.stdout)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
