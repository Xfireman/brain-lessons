# Brain Lessons

**把反复纠正 AI 的项目规矩，变成动手时会触发的检查。**

例如“修改 schema 后再生成客户端”“使用本项目的测试命令”：Brain Lessons 会在匹配的工具调用时提供相关要求；你明确选择 `block` 时，还能让宿主拒绝这次操作。

它把规则保存、动作匹配、样例检查和宿主接入做成了一个小工具。**当前是早期的规则执行组件**，规则需要明确录入，不会自动从聊天中学习。

Codex 优先 · 兼容 Claude Code · 本地文件 · 不调用模型 · Python 3.10+

[English](README.md) · [规则格式](docs/rules.md) · [隐私与边界](SECURITY.md)

![离线演示：保存纠正、检查样例、阻止命中的补丁](docs/assets/generated-client.gif)

*真实 hook 决策的离线回放；没有调用模型或执行工具。*

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
.venv/bin/brain-lessons demo --scenario generated-client
```

演示会保存生成文件规则、检查正反例，并将两种补丁送进真实的 Codex hook 处理器。它不调用模型、不实际执行补丁、不修改你的文件。[复现说明](docs/demo.md)。

## 在实际项目中使用

顺序是：**安装一次 → 用一句话描述纠正 → 看清匹配范围 → 照常工作**。

### 1. 一起安装 hook 和 Codex 技能

继续在刚才安装 CLI 的仓库目录执行：

```sh
export PATH="$PWD/.venv/bin:$PATH"
cd /path/to/your/project
brain-lessons init
brain-lessons install codex --with-skill
```

这会添加项目 `.codex/hooks.json` 中的一条 hook，以及 `.agents/skills/brain-remember/` 下的技能，保留已有的其他配置。技能记录了安装时 Python 的准确路径，Codex 无须继承终端 PATH；请保留该虚拟环境。Brain Lessons 不需要额外的模型 API key。

在这个项目开启新的 Codex 会话，启用 hooks，并在 **`/hooks` 中审阅和信任这条 hook**；项目本身也必须受信任。此前关闭过 hooks 时，可用 `codex --enable hooks` 启动 CLI。安装器不代授信任，不修改全局配置。

原来只安装过 hook 的用户，也运行同一条安装命令升级。手工改过的技能会提示冲突，不会被覆盖。生成的技能含本机程序路径，自带 `.gitignore`，每台机器重新安装即可；可以单独分享经过审阅的 `.brain/lessons/*.json`。

### 2. 在 Codex 中用一句话保存规矩

按项目调整路径，然后说：

```text
$brain-remember 保存一条拦截规则：禁止直接修改 src/generated/，
应该改 schema/api.json 再生成。允许修改 src/main.py。
展示匹配范围，并检查正反例。
```

技能会读取必要的项目上下文，生成范围明确的候选规则，先用 `learn --dry-run` 检查正反例，再按你的授权保存并验证。如果你说“只预览，不保存”，就停在候选阶段；路径不清楚时会先澄清。

显式写 `$brain-remember` 是明确的入口。Codex 也可以按描述自动选择技能，但能否自发选中取决于模型。它是 AI 协助录入，不会后台收集整段聊天。“回复简短一点”等普通偏好继续放在指令或记忆中。

也可以手动生成同一条候选规则：

```sh
brain-lessons learn generated-client \
  --title "生成客户端应通过 schema 更新" \
  --instruction "src/generated/ 由 schema/api.json 生成。请修改 schema，再重新生成客户端。" \
  --tool Edit --tool Write \
  --path "src/generated/*" \
  --sample-path "src/generated/client.py" \
  --miss-path "src/main.py" \
  --action block --dry-run
```

此时只输出候选 JSON、样例检查结果和问题，不保存文件。确认范围后，去掉同一条命令末尾的 `--dry-run` 执行，再检查：

```sh
brain-lessons check
brain-lessons recall --tool Edit --path src/generated/client.py
brain-lessons recall --tool Edit --path src/main.py
```

空教训库应得到一条规则、两个样例、零问题；第一个预览应命中阻止规则，第二个不命中。规则保存在 `.brain/lessons/generated-client.json`。同名规则不会被静默覆盖。默认是 `remind`，只有明确选择 `block` 才阻止。

### 3. 照常工作，需要时可以撤销

hook 生效后，宿主自动检查匹配的调用。改规则在下一次调用生效，无须重新安装；hook 定义改变则需要重新审阅信任。生成路径规则覆盖 Codex 的 `apply_patch`，包括多文件补丁和移动两端；不会分析任意 shell 命令写入的文件。

```sh
brain-lessons uninstall codex --with-skill
```

撤销移除自己的 hook 和未被修改的技能文件，保留教训、其他 hook 和其他技能。手工改过的技能保留并提示冲突。不加 `--with-skill` 时，保持原来的仅管理 hook 的行为。

`remind` 注入上下文；`block` 对命中的调用返回宿主 `deny` 决策。Brain 不替宿主放行权限，也不保证所有未来行为。官方说明见 [Codex hooks](https://learn.chatgpt.com/docs/hooks) 和 [技能发现机制](https://learn.chatgpt.com/docs/build-skills)。安装支持 macOS、Linux；目前只有 macOS 完成原生宿主验收。

**第一次试用？** 按[试用说明](docs/try-it.zh-CN.md)完成一条自己的规则，再反馈哪里卡住、哪里误拦，或者为什么普通指令已经够用。

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
