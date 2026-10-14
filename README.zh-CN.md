# Brain Lessons

**把反复纠正 AI 的项目规矩，变成动手时会触发的检查。**

例如“修改 schema 后再生成客户端”“使用本项目的测试命令”：Brain Lessons 会在匹配的工具调用时提供相关要求；你明确选择 `block` 时，还能让宿主拒绝这次操作。

它把规则保存、动作匹配、样例检查和宿主接入做成了一个小工具。**当前是早期的规则执行组件**，规则需要明确录入，不会自动从聊天中学习。

Codex 优先 · 兼容 Claude Code · 本地文件 · 不调用模型 · Python 3.10+

[English](README.md) · [规则格式](docs/rules.md) · [隐私与边界](SECURITY.md)

## 它能帮你解决什么

假设 `src/generated/` 是根据 `schema/api.json` 生成的客户端代码。直接修改生成文件，下次重新生成时改动就会丢失。你已经解释过这条规矩，但 AI 又准备对生成文件打补丁。

保存对应规则并启用集成后：

```text
Codex 准备用 apply_patch 修改 src/generated/client.py
  → Brain 命中 generated-client 规则
  → 宿主拒绝这次补丁操作
  → AI 收到原因和规则来源：
    “应修改 schema/api.json，再重新生成客户端。”
```

它提供的收益是：对这个已知错误增加一项可重复检查。AI 收到提示后仍需要选择正确的下一步。你也可以使用 `remind` 模式，只提供相关说明，允许当前调用继续。

这个例子只检查匹配的工具调用，不能阻止所有改文件的方法，例如通过任意 shell 脚本写文件就不在这项文件规则的检查范围内。

## 和直接告诉 Codex“记住”有什么区别

对于偏好和一般要求，**直接告诉 Codex 记住，通常更方便**。记忆和 `AGENTS.md` 本来也可以持久保存；能不能保存下来，并不是 Brain 的独特价值。

- **普通记忆或项目指引**：向模型提供要求，再由模型理解并遵守。
- **Brain 的 `block` 规则**：在工具执行边界由程序检查。hook 已安装、受信任且启用时，宿主会拒绝匹配的调用。
- **Brain 的 `remind` 规则**：在相关动作发生时补充提醒，不保证模型遵守，也不会阻止当前调用。

你也可以直接让 Codex 编写等效的 hook 或检查。Brain 的价值是把这套工作整理成统一格式、可重复验证、可安装撤销的组件；它没有赋予 Codex 独占的新能力。

## 什么时候值得用

同一种错误反复出现，而且触发命令或文件模式能够明确描述时，它比较合适：

- **在相关动作上检查**：例如直接修改生成文件，或执行一个已知错误的命令。
- **看得见依据**：展示命中了哪条规则及其来源；用 `check` 验证你编写的正反样例。
- **便于维护和复用**：规则是普通 JSON，可以审阅、版本管理；核对适用条件后再用于其他项目。
- **减少重复接入工作**：同一规则库可用于 Codex 和 Claude Code，两者独立安装与撤销。

“以后用中文回复”、偶尔的一次提醒、需要判断的“做事更谨慎”，先用普通记忆或项目指引就好。如果你已经维护了等效的 hook 和检查，沿用现有方案可能更简单。

Brain 本身不需要 API key、数据库或后台服务。你的编程助手仍使用原来的配置，被选中的规则也会进入该宿主的上下文，详见[隐私边界](SECURITY.md)。

**当前实际流程**：你或 AI 明确写入规则，安装后的 hook 在工具调用时加载匹配项。它不会收集会话、自动提取纠错，也不包含完整的个人知识系统。目前没有量化证据声称它能提升多少效率、节省多少 token 或减少多少错误。

## 先体验机制

克隆或下载本仓库，在仓库目录执行：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/brain-lessons demo
```

离线 demo 使用更简单的测试命令示例：阻止 `npm test`，对 `pnpm test` 不作决定。它在临时项目中调用 Codex 适配器，不调用模型、不实际执行这些命令，也不修改你的项目。它演示的是规则机制，不是 AI 自动学习的录像。

## 在实际项目中使用

顺序是：**保存一条规则 → 预览匹配结果 → 安装并信任一次 → 照常工作**。后续修改规则会在下一次工具调用时加载，无须重新安装集成。

### 1. 让项目能调用 CLI

继续在自己的项目使用时，先把刚安装的 CLI 加到当前终端 PATH，再切换目录：

```sh
export PATH="$PWD/.venv/bin:$PATH"
cd /path/to/your/project
brain-lessons init
```

hook 使用期间请保留该虚拟环境。无须安装 Obsidian、复制别人整套知识库或提供 API key。

如果 Codex 提示找不到 `brain-lessons`，把安装目录下 `.venv/bin/brain-lessons` 的绝对路径交给它；桌面应用不一定继承当前终端的 PATH。

### 2. 自己录入，或让 Codex 代你录入

你不必亲自敲每条 `learn` 命令。项目中已能调用 CLI 后，可以这样对 Codex 说：

> 请使用已安装的 `brain-lessons` CLI 保存一条项目规则：阻止直接用补丁修改 `src/generated/`。真源是 `schema/api.json`，应先修改 schema 再生成客户端。加入一个应该命中和一个不应命中的例子，运行 `brain-lessons check`，把保存的规则和生效范围展示给我。

这是让 Codex 操作现有 CLI 的明确请求，不是产品内置的自动学习功能。只说“记住这件事”不会自动创建 Brain 规则。接入或依赖规则前，先检查生成的匹配范围；示例路径应按你的项目调整。

等效的手动命令是：

```sh
brain-lessons learn generated-client \
  --title "生成客户端应通过 schema 更新" \
  --instruction "src/generated/ 由 schema/api.json 生成。请修改 schema，再重新生成客户端。" \
  --tool Edit --tool Write \
  --path "src/generated/*" \
  --sample-path "src/generated/client.py" \
  --miss-path "src/main.py" \
  --action block

brain-lessons check
brain-lessons recall --tool Edit --path src/generated/client.py
```

规则保存在 `.brain/lessons/generated-client.json`。若这是项目的第一条规则，`check` 应显示两个样例、零问题；`recall` 应显示这条阻止规则及其来源，不会真的执行编辑。你可以直接修改该文件、审阅后随项目提交，或把 `enabled` 改成 `false` 停用。同名规则不会被静默覆盖。

默认动作为 `remind`，只有显式选择 `block` 才阻止。先用 `recall` 看触发结果，再安装集成。

### 3. 为这个项目接入一次 Codex

在规则所属项目执行：

```sh
brain-lessons install codex
```

安装器只合并项目 `.codex/hooks.json` 中自己的一条 `PreToolUse` hook，保留其他 hook 和配置。支持 Codex 命令调用与 `apply_patch`，包括多文件补丁、删除和移动前后的路径。

在该项目重新开始 Codex 会话。项目必须受信任、hooks 必须启用，并且需要你在 **`/hooks` 中审阅和信任这条 hook**。如果此前关闭过 hooks，可用 `codex --enable hooks` 启动 CLI。安装器不会替你授予信任，也不会修改全局 Codex 配置；hook 定义更新后需重新审阅。

完成信任后，照常与 Codex 对话和写代码。每次编辑前不用再手动运行 Brain 命令，宿主会调用 hook，只有定义好的匹配条件才会触发规则。

撤销集成：

```sh
brain-lessons uninstall codex
```

撤销只移除 Codex 的这条 hook，保留规则。自动安装当前支持 macOS 和 Linux。

**提醒与阻止不同。** `remind` 注入补充上下文，不保证当前调用停止，也不保证模型遵守；`block` 返回宿主协议的 `deny` 决策。Brain 不返回 `allow`，不会替宿主放行权限。CLI 与协议有自动测试，真实模型行为需要单独实测。

官方协议见 [Codex hooks](https://learn.chatgpt.com/docs/hooks)。

## Claude Code 兼容入口

```sh
brain-lessons install claude-code
# 仅撤销 Claude Code 集成：
brain-lessons uninstall claude-code
```

Claude Code 使用 `.claude/settings.local.json`。两种宿主共享教训库，但安装和卸载互不影响。安装后重新开始会话并检查 `/hooks`。其他 AI 工具仍可显式调用 CLI。

## 使用边界

- 命令按连续 shell token 匹配，不是完整 shell 解释器；别名、变量、脚本和其他工具可能绕过匹配，也可能误中参数。不能当成安全沙箱。
- Codex 文件规则检查 `apply_patch`，不会分析任意 shell 命令间接修改的文件；后续 `write_stdin` 输入不会再次触发原命令的执行前检查。
- 路径按项目相对 glob 匹配。工具过滤与触发条件同时满足才命中。
- 损坏规则会被 hook 跳过，`check` 会报问题；坏输入不返回决定。不能用它替代正式的权限控制。
- 最多展示三条匹配规则，阻止优先，并显示省略数量；全部规则用 `list` 查看。
- **本地存储不等于模型本地运行。** 被选中的规则会进入宿主上下文，也可能进入其会话记录。规则里不要写凭证或不应提供给该宿主的内容。
- 当前是早期版本，没有宣称提升效率、节省 token 或减少错误的量化数据。

## 开发与贡献

原生验收使用 **macOS 上的 Codex CLI 0.162.1** 与本机合成响应服务：关闭规则时，样例命令和补丁确实执行；开启规则时，Codex 阻止指定命令和补丁，正常命令仍可执行，提醒进入下一次模型请求。这验证真实宿主行为，不调用付费模型。其他 Codex 界面需要兼容的 hook 运行时，并能访问安装后的 Python 程序。

```sh
python3 -B -m unittest discover -s tests -v
```

PATH 中已有 Codex CLI 0.162.1 时，可运行真实宿主验收：

```sh
python3 -B tests/native_codex.py
```

该测试使用隔离的 Codex 主目录，只信任已审阅的测试 hook 精确哈希，模型响应来自本机回环服务。它不使用你的登录、不改真实 Codex 配置，也不衡量模型能力。CI 会单独运行这项验收。

原生 CI 在 macOS 上运行，保留 Codex 默认的工作区文件沙箱和工具网络隔离。Linux 运行 CLI 集成测试；托管 Ubuntu worker 无法启动 Codex 的 bubblewrap 命名空间，因此本版尚未通过 Linux 原生拦截验收。测试不会放宽沙箱或静默切换后端。正常产品安装不会修改任何沙箱或网络设置。

欢迎提供可公开的合成教训及正反例。提交 issue 时，不要上传真实会话、公司配置或凭证。
