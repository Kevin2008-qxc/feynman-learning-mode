# 费曼学习模式

一个遵循 Agent Skills 开放格式的费曼学习 Skill：用户当老师，AI 扮演一个好奇但会提出合理错误猜测的新手，通过单点追问帮助用户发现知识缺口。

## 为什么不一样

许多费曼式工具由 AI 解释概念，再让用户复述。本项目反过来：

- 用户负责讲解；
- AI 每轮只提出一个可纠正的错误猜测或一个追问；
- 用户通过纠正 AI 暴露自己的知识断点；
- AI 不主动抢走完整答案，也不一次抛出问题清单；
- 连续卡住三轮后提供换例子、最小提示或暂停的选择；
- 结束模式后生成简短验收和迁移检查；
- 遇到危险操作时暂停角色扮演，优先给出安全提醒。

## 多 Agent 兼容

核心 Skill 只使用跨平台通用的 `name`、`description` 和 Markdown 指令，不依赖网络、MCP、脚本或 Codex 专属字段。`agents/openai.yaml` 只负责 Codex 的界面名称和默认提示；其他宿主可以安全忽略它。

截至 2026-10-24，推荐安装位置如下。各 Agent 的路径可能随版本变化，安装前应以其当前文档为准。

| Agent | 用户级安装位置 | 项目级安装位置 | 调用方式 |
|---|---|---|---|
| Codex | `~/.codex/skills/feynman/` 或 `~/.agents/skills/feynman/` | `.agents/skills/feynman/` | `$feynman` 或自然语言 |
| WorkBuddy | `~/.workbuddy/skills/feynman/` | `.workbuddy/skills/feynman/` | 已安装 Skill 中选择，或使用费曼触发语 |
| DeepSeek Harness | `~/.dsh/skills/feynman/` 或 `~/.agents/skills/feynman/` | `.dsh/skills/feynman/` 或 `.agents/skills/feynman/` | `/feynman` 或自然语言 |
| Claude Code | `~/.claude/skills/feynman/` | `.claude/skills/feynman/` | `/feynman` 或自然语言 |
| Cursor | `~/.cursor/skills/feynman/` 或 `~/.agents/skills/feynman/` | `.cursor/skills/feynman/` 或 `.agents/skills/feynman/` | 自然语言；不同版本也支持斜杠调用 |
| GitHub Copilot / VS Code | `~/.agents/skills/feynman/` 或宿主指定目录 | `.github/skills/feynman/` 或 `.agents/skills/feynman/` | 自然语言或斜杠调用 |

若不希望记住各平台目录，可以优先安装到共享的 `~/.agents/skills/feynman/`；支持该约定的宿主会直接发现它。

### Codex

#### Windows PowerShell

```powershell
git clone https://github.com/Kevin2008-qxc/feynman-learning-mode.git
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
Copy-Item -Recurse -Force ".\feynman-learning-mode\feynman" "$env:USERPROFILE\.codex\skills\"
```

#### macOS / Linux

```bash
git clone https://github.com/Kevin2008-qxc/feynman-learning-mode.git
mkdir -p ~/.codex/skills
cp -R ./feynman-learning-mode/feynman ~/.codex/skills/
```

### WorkBuddy

WorkBuddy 可以导入 ZIP，或从本地技能目录发现 Skill。先构建符合 WorkBuddy 要求的压缩包：

```bash
python scripts/package_skill.py
```

生成的 `dist/feynman-skill.zip` 会把 `SKILL.md` 放在压缩包根目录，而不是多套一层 `feynman/`。然后在 WorkBuddy 中打开“专家 · 技能 · 连接器 → 技能 → 添加技能 → 上传技能”，选择该 ZIP。

也可以直接复制目录：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.workbuddy\skills" | Out-Null
Copy-Item -Recurse -Force ".\feynman-learning-mode\feynman" "$env:USERPROFILE\.workbuddy\skills\"
```

### DeepSeek Harness

DeepSeek Harness 原生支持目录形式的 `SKILL.md`。将 `feynman` 目录复制到 `~/.dsh/skills/` 或共享的 `~/.agents/skills/`，然后使用 `/feynman` 或直接以“费曼”开始任务。

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.dsh\skills" | Out-Null
Copy-Item -Recurse -Force ".\feynman-learning-mode\feynman" "$env:USERPROFILE\.dsh\skills\"
```

不同 Agent 的入口不同，但核心触发语一致：

```text
费曼：卷积
```

## 使用

```text
费曼：卷积
```

```text
费曼，我来讲 PID 为什么能减小稳态误差。
```

在 Codex 中还可以使用 `$feynman`；DeepSeek Harness 和部分其他宿主可使用 `/feynman`。

只输入“费曼”时，AI 会先询问今天想教什么。

结束学习：

```text
结束费曼
```

请求答案并退出角色：

```text
你说正确答案
```

普通问题“费曼学习法是什么”不会触发角色扮演。

## 隐私边界

这个 Skill 不依赖网络、API Key、MCP 或外部服务。默认不读取无关文件，不把学习内容写入文件，也不自动写入长期记忆；只有用户明确要求时才执行这些操作。

仓库不会附带 Codex、CC Switch、DeepSeek 或 GitHub 的配置文件。安装时只复制 `feynman/` Skill 目录，不需要提供 API Key，也不依赖 GitHub Actions Secret。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试检查触发范围、单点追问、错误猜测标记、安全与隐私边界、退出验收、UI 元数据、上下文体积和 UTF-8 编码。

测试还会验证可移植 frontmatter，以及 WorkBuddy ZIP 中的 `SKILL.md` 是否位于压缩包根目录。

## 目录结构

```text
feynman-learning-mode/
├── feynman/
│   ├── SKILL.md
│   └── agents/
│       └── openai.yaml
├── tests/
│   ├── test_feynman_skill.py
│   └── test_portability.py
├── scripts/
│   └── package_skill.py
├── .gitattributes
├── .gitignore
└── LICENSE
```

## 兼容性依据

- [WorkBuddy Skills 文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
- [DeepSeek Harness Skill 能力源码说明](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill)
- [Cursor Agent Skills 文档](https://cursor.com/docs/skills)

## License

[MIT](LICENSE)
