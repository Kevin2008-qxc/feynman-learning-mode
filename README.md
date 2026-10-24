# 费曼学习模式

面向国内 Agent 优先设计的便携费曼学习 Skill。用户当老师，AI 扮演一个好奇但会提出合理错误猜测的新手，通过单点追问帮助用户发现知识缺口。

## 优先支持

| Agent | 用户级安装位置 | 项目级安装位置 | 触发方式 |
|---|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/feynman/` | `.workbuddy/skills/feynman/` | 按描述自动触发，或在已安装 Skill 中选择 |
| DeepSeek Harness | `~/.dsh/skills/feynman/` | `.dsh/skills/feynman/` | `/feynman` 或按描述自动触发 |
| CodeBuddy | `~/.codebuddy/skills/feynman/` | `.codebuddy/skills/feynman/` | 按描述自动触发，或在 `/skills` 中确认已加载 |
| Codex | `~/.codex/skills/feynman/` | `.agents/skills/feynman/` | `$feynman` 或自然语言 |
| 共享 Agent Skills | `~/.agents/skills/feynman/` | `.agents/skills/feynman/` | 由宿主决定 |

核心 Skill 只使用通用的 `name`、`description` 和 Markdown 指令，不依赖网络、MCP、API Key 或特定宿主的专有字段。`agents/openai.yaml` 仅用于 Codex 界面，不会进入国内 Agent 的便携 ZIP。

## 安装

先克隆仓库：

```bash
git clone https://github.com/Kevin2008-qxc/feynman-learning-mode.git
cd feynman-learning-mode
```

统一安装器默认安装到用户级 Skill 目录：

```bash
python scripts/install_skill.py workbuddy
python scripts/install_skill.py deepseek-harness
python scripts/install_skill.py codebuddy
```

查看支持列表：

```bash
python scripts/install_skill.py --list
```

安装到当前项目：

```bash
python scripts/install_skill.py workbuddy --scope project
python scripts/install_skill.py deepseek-harness --scope project
python scripts/install_skill.py codebuddy --scope project
```

指定其他项目目录：

```bash
python scripts/install_skill.py codebuddy --scope project --project-dir D:\MyProject
```

安装器默认拒绝覆盖已有 Skill。明确需要更新时使用：

```bash
python scripts/install_skill.py workbuddy --force
```

它只替换目标目录中的 `feynman` Skill，不修改 Agent 配置、凭据或用户数据。

## WorkBuddy ZIP

WorkBuddy 支持从 ZIP 上传。构建便携包：

```bash
python scripts/package_skill.py
```

生成：

```text
dist/feynman-skill-portable.zip
```

ZIP 根目录直接包含 `SKILL.md`，不会多套一层 `feynman/`，也不包含 Codex 专属元数据。可在以下位置上传：

```text
WorkBuddy → 专家 · 技能 · 连接器 → 技能
→ 添加技能 → 上传技能 → 选择 ZIP
```

首个公开 Release 会附带同名 ZIP，通常不需要自行构建。

## 为什么不一样

许多费曼式工具由 AI 解释概念，再让用户复述。本项目反过来：

- 用户负责讲解；
- AI 每轮只提出一个可纠正的错误猜测或一个追问；
- 用户通过纠正 AI 暴露自己的知识断点；
- AI 不主动抢走完整答案，也不一次抛出问题清单；
- 连续卡住三轮后提供换例子、最小提示或暂停的选择；
- 结束模式后生成简短验收和迁移检查；
- 遇到危险操作时暂停角色扮演，优先给出安全提醒。

## 使用

```text
费曼：卷积
```

```text
费曼，我来讲 PID 为什么能减小稳态误差。
```

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

仓库不会附带 Codex、CC Switch、DeepSeek、CodeBuddy 或 WorkBuddy 的配置文件。安装时只复制 `feynman/` Skill 目录，不需要提供 API Key。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖：

- 触发范围与排除条件；
- 单点追问和错误猜测标记；
- 安全与运行时隐私边界；
- 退出验收与迁移检查；
- 可移植 frontmatter；
- WorkBuddy 便携 ZIP 结构；
- DeepSeek Harness、CodeBuddy、WorkBuddy 安装路径；
- 防止无授权覆盖已有 Skill；
- UTF-8 编码与上下文体积。

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
│   ├── install_skill.py
│   └── package_skill.py
├── .gitattributes
├── .gitignore
├── LICENSE
└── README.md
```

## 兼容性依据

- [WorkBuddy Skills 文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
- [WorkBuddy Skill ZIP 打包说明](https://github.com/sandbaseai/workbuddy-skill/blob/main/docs/quickstart.md)
- [DeepSeek Harness Skill 文件系统源码](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem)
- [CodeBuddy CLI Skills 文档](https://www.codebuddy.ai/docs/zh/cli/skills)

## License

[MIT](LICENSE)
