# Launch drafts

These are drafts for the maintainer to post after the version containing
`brain-remember` is publicly available. No messages have been sent. Do not claim
user counts, productivity gains, or testimonials that have not been observed.

## Invite a developer you know

我做了一个 Codex 小工具 brain-lessons，想找几位经常用 Codex 写代码的人试一下。

它适合这样的情况：你反复说“不要直接改生成文件，应该改 schema”，但希望这条规矩能在匹配的工具调用前被检查。
现在可以用 `$brain-remember` 描述规矩，让 Codex 生成规则、检查正反例，再按你的选择提醒或阻止。

普通偏好继续用记忆或 AGENTS.md 就行。这个工具主要处理能用命令或路径判断的约束，不是安全沙箱，也不会自动收集聊天。

仓库和演示：https://github.com/Xfireman/brain-lessons

如果你愿意，选一条自己项目的规矩试用，告诉我第一个卡点和有没有误拦。
一周后再告诉我你是否还留着它。不用提供公司代码、真实会话或密钥；觉得没有必要也请直说。

## Short public post

把“别直接改生成文件”，变成 Codex 动手时会触发的检查。

brain-lessons 把明确录入的项目纠正保存为本地 JSON：
用一句话交给 `$brain-remember` → 检查命中和允许例子 → 在匹配的工具调用前提醒或阻止。
规则可审阅、可停用，hook 可撤销。Python 标准库运行时，不需要额外模型 API key。

这是早期项目，适合具体命令和路径约束。普通偏好用指令即可，复杂权限问题仍交给正式权限控制。
欢迎反馈安装卡点、误匹配，以及它什么时候比直接维护 AGENTS.md 更省事。

https://github.com/Xfireman/brain-lessons

## Show HN draft

Title: Show HN: Brain Lessons – check project corrections before Codex tool calls

I built a small local tool for a recurring coding-agent problem: repeating a
concrete project correction such as "edit the schema, not the generated client."

Brain Lessons stores explicit rules as JSON. An optional Codex skill helps author
them from a sentence, checks a matching and a nearby allowed example, and shows
the scope. A project hook then reminds the agent or denies matching tool calls.
Claude Code can use the same rule store through a separate hook.

The README includes a runnable offline replay. It uses the actual hook handler,
without a model or executing the proposed tools. The runtime is Python's standard
library, with no account, database, or telemetry.

This is an alpha. It is not a security sandbox, and ordinary preferences are often
better in AGENTS.md or memory. I would like feedback on first-use friction and
which corrections are actually worth turning into checks.

https://github.com/Xfireman/brain-lessons

Post only when people can run the linked version. Follow the current
[Show HN guidelines](https://news.ycombinator.com/showhn.html). Do not ask for votes.

## First trial cycle

Aim for five independent trials as a small learning exercise, not a growth forecast.
Record consented feedback privately; never publish participant identities by default.
Check installation success, creation of a useful first rule, false positives, and
whether the rule remains enabled one week later. Invite follow-up only with consent.

Review GitHub unique visitors and referring sources separately from successful
trials and continued use. Traffic updates lag; release downloads include maintainer
checks. If visitors do not try it, improve the example. If installation fails, fix
setup. If installed users remove it, understand why before adding features.

The preview image is [assets/social-preview.png](assets/social-preview.png).
Upload it in GitHub repository settings when publishing the release.
