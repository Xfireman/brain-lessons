# Try one rule in your own project

The useful question is: does this make one repeated correction easier to maintain?
Try it in a small, non-sensitive local project first. Keep the project's normal
permissions and sandbox settings.

1. Follow the [installation steps](../README.md#use-it-in-a-project). Install the
   Codex hook and `brain-remember` skill, then review the hook in `/hooks`.
2. Pick one recurring command or path mistake. Use your own paths, not the demo's
   paths unless they actually exist in your project.
3. Ask `$brain-remember` to preview the correction, with one matching action and
   one nearby action that should still be allowed. Ask it to save after the scope
   looks right. Say explicitly if you want a block; otherwise use a reminder.
4. Ask Codex to show `check` and both `recall` results. Do not run a destructive
   command just to test a rule. To see actual host enforcement, use a harmless
   generated-file fixture; the [offline demo](demo.md) needs no host trust.
5. Work normally. After a week, decide whether to keep the rule, adjust it, or
   remove it. Feedback that the tool was unnecessary is useful too.

## Tell us what happened

Use the repository's **Trial feedback** issue template. Share only synthetic or
sanitized examples:

- OS, Codex interface/version, and Brain Lessons version.
- Your first sticking point: installation, trust, choosing a rule, or matching.
- The correction in ordinary language; a minimal matching and allowed example.
- Whether it helped during actual work, triggered incorrectly, or never triggered.
- After a week: still enabled, adjusted, or removed, and why.

Do not upload real conversations, secrets, internal paths, or proprietary code.
There is no telemetry. The maintainer learns about usage only through feedback
you choose to share. A download, clone, or passing test is not evidence of continued use.

## Undo

Run `brain-lessons uninstall codex --with-skill` in the project. It keeps your
lessons and unrelated settings. If you edited the installed skill, the installer
stops rather than deleting your edits. You can remove only the hook with
`brain-lessons uninstall codex` and keep the skill for manual rule authoring.

To stop a particular rule, set its JSON `enabled` field to `false`.
