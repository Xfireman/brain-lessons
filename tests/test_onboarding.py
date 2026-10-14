"""First-use workflow across real CLI processes and filesystem boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "src"
SKILL = ".agents/skills/brain-remember/SKILL.md"
UI = ".agents/skills/brain-remember/agents/openai.yaml"


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="brain onboarding ")
        self.root = Path(self.temporary.name)
        self.env = {**os.environ, "PYTHONPATH": str(SOURCE), "PYTHONDONTWRITEBYTECODE": "1"}

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args, input=None):
        return subprocess.run([sys.executable, "-m", "brain_lessons", "--root", str(self.root), *args],
                              cwd=self.root, env=self.env, input=input, text=True, capture_output=True, timeout=10)

    def rule_args(self):
        return ["learn", "generated-client", "--title", "Edit the schema", "--instruction",
                "Change schema/api.json, then regenerate.", "--tool", "Edit", "--tool", "Write",
                "--path", "src/generated/*", "--action", "block",
                "--sample-path", "src/generated/client.py", "--miss-path", "src/main.py"]

    def files(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_preview_checks_examples_without_any_project_write(self):
        result = self.cli(*self.rule_args(), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["lesson"]["action"], "block")
        self.assertEqual(preview["examples_checked"], 2)
        self.assertEqual(preview["problems"], [])
        self.assertEqual(self.files(), {})
        self.assertEqual(self.cli(*self.rule_args()).returncode, 0)
        self.assertEqual(json.loads((self.root / ".brain/lessons/generated-client.json").read_text()), preview["lesson"])
        self.assertEqual(self.cli("check").returncode, 0)

    def test_bad_or_missing_negative_example_cannot_pass_preview(self):
        args = self.rule_args()
        args[-1] = "src/generated/other.py"
        bad = self.cli(*args, "--dry-run")
        self.assertEqual(bad.returncode, 1, bad.stderr)
        self.assertTrue(json.loads(bad.stdout)["problems"])
        missing = self.cli(*self.rule_args()[:-2], "--dry-run")
        self.assertEqual(missing.returncode, 1, missing.stderr)
        self.assertTrue(json.loads(missing.stdout)["problems"])
        self.assertEqual(self.files(), {})

    def test_preview_does_not_claim_it_can_overwrite_an_existing_rule(self):
        self.assertEqual(self.cli(*self.rule_args()).returncode, 0)
        before = self.files()
        result = self.cli(*self.rule_args(), "--dry-run")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)["problems"])
        self.assertEqual(self.files(), before)

    def test_oversized_candidate_is_rejected_in_preview_and_save(self):
        args = ["learn", "large-rule", "--title", "Test command", "--instruction", "Use pnpm test.",
                "--command", "npm test"]
        for i in range(20):
            args.extend(["--sample-command", "npm test " + "x" * 1900 + str(i),
                         "--miss-command", "pnpm test " + "x" * 1900 + str(i)])
        for extra in (["--dry-run"], []):
            result = self.cli(*args, *extra)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("64 KiB", result.stderr)
            self.assertEqual(self.files(), {})

    def test_full_store_rejects_new_rule_without_disabling_existing_rules(self):
        self.assertEqual(self.cli(*self.rule_args()).returncode, 0)
        store = self.root / ".brain/lessons"
        value = json.loads((store / "generated-client.json").read_text())
        for i in range(499):
            value["id"] = f"existing-{i}"
            (store / f"existing-{i}.json").write_text(json.dumps(value))
        before = self.files()
        args = self.rule_args()
        args[1] = "one-too-many"
        for extra in (["--dry-run"], []):
            result = self.cli(*args, *extra)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("500", result.stderr)
            self.assertEqual(self.files(), before)
        check = self.cli("check", "--json")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertEqual(json.loads(check.stdout)["lessons"], 500)

    def test_install_bundle_is_idempotent_and_uninstall_keeps_rules_and_other_skills(self):
        self.assertEqual(self.cli(*self.rule_args()).returncode, 0)
        other = self.root / ".agents/skills/another/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("Another user's skill")
        result = self.cli("install", "codex", "--with-skill")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("/hooks", result.stdout)
        self.assertTrue((self.root / SKILL).is_file())
        self.assertTrue((self.root / UI).is_file())
        self.assertIn("codex_skill", json.loads((self.root / ".brain/installation.json").read_text()))
        before = self.files()
        self.assertEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.cli("uninstall", "codex", "--with-skill").returncode, 0)
        self.assertFalse((self.root / SKILL).exists())
        self.assertEqual(other.read_text(), "Another user's skill")
        self.assertTrue((self.root / ".brain/lessons/generated-client.json").is_file())
        self.assertEqual(json.loads((self.root / ".codex/hooks.json").read_text())["hooks"]["PreToolUse"], [])

    def test_user_skill_collision_does_not_install_any_hook(self):
        path = self.root / SKILL
        path.parent.mkdir(parents=True)
        path.write_text("User-owned instructions")
        before = self.files()
        self.assertNotEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        self.assertEqual(self.files(), before)

    def test_edited_skill_is_preserved_on_reinstall_and_uninstall(self):
        self.assertEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        path = self.root / SKILL
        path.write_text(path.read_text() + "\nMy customization\n")
        before = self.files()
        for verb in ("install", "uninstall"):
            result = self.cli(verb, "codex", "--with-skill")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.files(), before)

    def test_bundle_refuses_symlinked_skill_directory(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / ".agents").symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / ".codex/hooks.json").exists())

    def test_machine_specific_skill_is_ignored_by_git(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        result = self.cli("install", "codex", "--with-skill")
        self.assertEqual(result.returncode, 0, result.stderr)
        ignored = subprocess.run(["git", "check-ignore", SKILL, UI], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(ignored.returncode, 0, ignored.stderr)
        self.assertEqual(set(ignored.stdout.splitlines()), {SKILL, UI})

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses permissions")
    def test_failed_bundle_uninstall_restores_hook_and_skill(self):
        self.assertEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        directory = (self.root / UI).parent
        before = self.files()
        directory.chmod(0o555)
        try:
            self.assertNotEqual(self.cli("uninstall", "codex", "--with-skill").returncode, 0)
        finally:
            directory.chmod(0o755)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.cli("uninstall", "codex", "--with-skill").returncode, 0)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses permissions")
    def test_failed_bundle_write_rolls_back_and_can_retry(self):
        path = self.root / ".agents/skills/brain-remember"
        path.mkdir(parents=True)
        path.chmod(0o555)
        before = self.files()
        try:
            result = self.cli("install", "codex", "--with-skill")
            self.assertNotEqual(result.returncode, 0)
        finally:
            path.chmod(0o755)
        self.assertEqual(self.files(), before)
        self.assertEqual(self.cli("install", "codex", "--with-skill").returncode, 0)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root bypasses permissions")
    def test_failed_nested_install_keeps_parent_rule_scope(self):
        self.assertEqual(self.cli("learn", "parent-test-rule", "--title", "Use pnpm",
                                 "--instruction", "Use pnpm test.", "--command", "npm test",
                                 "--sample-command", "npm test", "--action", "block").returncode, 0)
        child = self.root / "child"
        skill_directory = child / ".agents/skills/brain-remember"
        skill_directory.mkdir(parents=True)
        payload = json.dumps({"hook_event_name": "PreToolUse", "cwd": str(child),
                              "tool_name": "Bash", "tool_input": {"command": "npm test"}})
        before = self.cli("hook", "--adapter", "codex", input=payload)
        self.assertEqual(json.loads(before.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        original_paths = {p.relative_to(self.root) for p in self.root.rglob("*")}
        skill_directory.chmod(0o555)
        try:
            failed = subprocess.run([sys.executable, "-m", "brain_lessons", "--root", str(child),
                                     "install", "codex", "--with-skill"], env=self.env,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(failed.returncode, 1, failed.stderr)
        finally:
            skill_directory.chmod(0o755)
        self.assertEqual({p.relative_to(self.root) for p in self.root.rglob("*")}, original_paths)
        after = self.cli("hook", "--adapter", "codex", input=payload)
        self.assertEqual(json.loads(after.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_upgrade_existing_codex_hook_and_leave_claude_untouched(self):
        self.assertEqual(self.cli("install", "codex").returncode, 0)
        self.assertEqual(self.cli("install", "claude-code").returncode, 0)
        old_hook = (self.root / ".codex/hooks.json").read_bytes()
        claude = (self.root / ".claude/settings.local.json").read_bytes()
        self.assertEqual(self.cli("install", "codex", "--with-skill").returncode, 0)
        self.assertEqual((self.root / ".codex/hooks.json").read_bytes(), old_hook)
        self.assertEqual(self.cli("uninstall", "codex", "--with-skill").returncode, 0)
        self.assertEqual((self.root / ".claude/settings.local.json").read_bytes(), claude)

    def test_generated_demo_reports_real_hook_decisions_without_project_changes(self):
        result = self.cli("demo", "--scenario", "generated-client", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["checks"]["examples_checked"], 2)
        self.assertEqual(data["checks"]["problems"], [])
        self.assertEqual([c["decision"] for c in data["calls"]], ["deny", "none"])
        self.assertIn("schema/api.json", data["calls"][0]["reason"])
        self.assertFalse(data["model_called"])
        self.assertFalse(data["tools_executed"])
        self.assertEqual(self.files(), {})


if __name__ == "__main__":
    unittest.main()
