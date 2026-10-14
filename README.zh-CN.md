# Brain Lessons

**把“这件事我已经说过了”，变成下次能用上的项目规则。**

保存一次纠错，在相关工具调用时召回，并附上来源。可以提醒 AI，也可以明确阻止一个已知错误的命令。

本地文件 · 不调用模型 · 无运行时依赖 · Python 3.10+

[English](README.md) · [规则格式](docs/rules.md) · [隐私与边界](SECURITY.md)

```text
你：“这个项目用 pnpm test。”

新会话里，AI 提出：
  npm test     → 阻止
                 project-tests.json：应使用 pnpm test

随后提出：
  pnpm test    → Brain 不作决定，宿主权限照常生效
```

上面是确定性的 hook 示例，不是模型行为实测。下面的离线演示可以复现这个决策过程。

## 先跑起来

克隆或下载本仓库，在仓库目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/brain-lessons demo
```

演示创建临时项目，调用真实 hook 处理器；不会调用模型、执行示例命令或修改你的项目。

继续在自己的项目使用时，先把刚安装的 CLI 加到当前终端 PATH，再切换目录：

```sh
export PATH="$PWD/.venv/bin:$PATH"
cd /path/to/your/project
brain-lessons init
```

hook 使用期间请保留该虚拟环境。无须安装 Obsidian、复制别人整套知识库或提供 API key。

## 保存第一条纠错

```sh
brain-lessons learn project-tests \
  --title "使用本项目的测试命令" \
  --instruction "本项目使用 pnpm test，未配置 npm test。" \
  --tool Bash \
  --command "npm test" \
  --sample-command "npm test -- --watch" \
  --miss-command "pnpm test" \
  --action block

brain-lessons check
brain-lessons recall --tool Bash --command "npm test"
```

规则保存在 `.brain/lessons/project-tests.json`。你可以直接编辑、经审核后随项目提交，或把 `enabled` 改成 `false` 停用。同名规则不会被静默覆盖。

默认动作为 `remind`，只有显式选择 `block` 才阻止。先用 `recall` 看触发结果，再安装集成。

## 接入 Claude Code

在规则所属项目执行：

```sh
brain-lessons install claude-code
```

安装器只合并项目 `.claude/settings.local.json` 中自己的一条 `PreToolUse` hook，保留其他 hook 和配置。重新开始 Claude Code 会话，在 `/hooks` 中核对后使用。

撤销集成：

```sh
brain-lessons uninstall claude-code
```

撤销只移除自己的 hook，保留规则。自动安装当前支持 macOS 和 Linux。

**提醒与阻止不同。** `remind` 注入补充上下文，不保证当前调用停止，也不保证模型遵守；`block` 返回宿主协议的 `deny` 决策。Brain 不返回 `allow`，不会替宿主放行权限。CLI 与协议有自动测试，真实模型行为需要单独实测。

其他 AI 工具可以显式调用 CLI；本版不宣称已完成其他宿主的原生自动集成。

## 它适合什么

总是适用的规则继续写在常规项目指引里。Brain 用来保存需要在某个命令或文件操作时想起来的教训。每次匹配都能看到规则来源，也能用自己编写的正反样例核对触发条件。

它不会收集会话，不会后台分析你的工作，不会自动把内容上传到 Brain 服务。只有你明确保存的纠错才成为规则。

## 使用边界

- 命令按连续 shell token 匹配，不是完整 shell 解释器；别名、变量、脚本和其他工具可能绕过匹配，也可能误中参数。不能当成安全沙箱。
- 路径按项目相对 glob 匹配。工具过滤与触发条件同时满足才命中。
- 损坏规则会被 hook 跳过，`check` 会报问题；坏输入不返回决定。不能用它替代正式的权限控制。
- 最多展示三条匹配规则，阻止优先，并显示省略数量；全部规则用 `list` 查看。
- **本地存储不等于模型本地运行。** 被选中的规则会进入宿主上下文，也可能进入其会话记录。规则里不要写凭证或不应提供给该宿主的内容。
- 当前是早期版本，没有宣称提升效率、节省 token 或减少错误的量化数据。

## 开发与贡献

```sh
python3 -B -m unittest discover -s tests -v
```

欢迎提供可公开的合成教训及正反例。提交 issue 时，不要上传真实会话、公司配置或凭证。
