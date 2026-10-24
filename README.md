# 费曼概念强化

面向国内 AI 软件优先设计的基础概念强化 Skill。用户当老师，AI 扮演一个好奇但会提出合理错误猜测的新手，通过单点追问和按需图解帮助用户真正讲清一个概念。

## 优先支持

| Agent | 用户级安装位置 | 项目级安装位置 | 触发方式 |
|---|---|---|---|
| WorkBuddy | `~/.workbuddy/skills/feynman/` | `.workbuddy/skills/feynman/` | 按描述自动触发，或在已安装 Skill 中选择 |
| 豆包工作 | 客户端“上传技能” | 不适用 | 输入 `/` 或 `@` 选择，或按描述自动触发 |
| DeepSeek Harness | `~/.dsh/skills/feynman/` | `.dsh/skills/feynman/` | `/feynman` 或按描述自动触发 |
| ZCode | `~/.zcode/skills/feynman/` | `.zcode/skills/feynman/` | `$feynman`、斜杠菜单或按描述自动触发 |
| Kimi Code CLI | `~/.kimi/skills/feynman/` | `.kimi/skills/feynman/` | `/skill:feynman` 或按描述自动触发 |
| CodeBuddy | `~/.codebuddy/skills/feynman/` | `.codebuddy/skills/feynman/` | 按描述自动触发，或在 `/skills` 中确认已加载 |
| Codex | `~/.codex/skills/feynman/` | `.agents/skills/feynman/` | `$feynman` 或自然语言 |
| 共享 Agent Skills | `~/.agents/skills/feynman/` | `.agents/skills/feynman/` | 由宿主决定 |

核心 Skill 只使用通用的 `name`、`description` 和 Markdown 指令，不依赖网络、MCP、API Key 或特定宿主的专有字段。`agents/openai.yaml` 仅用于 Codex 界面，不会进入国内 Agent 的便携 ZIP。

“豆包工作”支持本地导入；“Kimi”一行专指支持 `SKILL.md` 的 Kimi Code CLI，不代表 Kimi 普通聊天客户端一定支持本地 Skill 目录。

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
python scripts/install_skill.py zcode
python scripts/install_skill.py kimi
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
python scripts/install_skill.py zcode --scope project
python scripts/install_skill.py kimi --scope project
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

## 客户端上传：WorkBuddy 与豆包工作

WorkBuddy 支持从 ZIP 上传。构建便携包：

```bash
python scripts/package_skill.py
```

生成：

```text
dist/feynman-skill-portable.zip
```

ZIP 根目录直接包含 `SKILL.md`，不会多套一层 `feynman/`，也不包含 Codex 专属元数据。

WorkBuddy 上传位置：

```text
WorkBuddy → 专家 · 技能 · 连接器 → 技能
→ 添加技能 → 上传技能 → 选择 ZIP
```

豆包工作上传位置：

```text
豆包客户端 → 插件 · 技能 · 伙伴 → 技能
→ + 添加 → 上传技能 → 选择 ZIP 或解压后的文件夹
```

如果当前豆包版本不接收 ZIP，就解压后上传根目录包含 `SKILL.md` 的 `feynman` 文件夹。安装后可在输入框输入 `/` 或 `@` 查找 `费曼学习`，也可以直接描述学习需求让系统匹配。

首个公开 Release 会附带同名 ZIP，通常不需要自行构建。

## 为什么不一样

许多费曼式工具由 AI 解释概念，再让用户复述。本项目反过来：

- 用户负责讲解；
- AI 每轮只提出一个可纠正的错误猜测或一个追问；
- 用户通过纠正 AI 暴露自己的知识断点；
- AI 不主动抢走完整答案，也不一次抛出问题清单；
- 连续卡住三轮后提供换例子、最小提示或暂停的选择；
- 根据理解断点自适应配图，不按轮次机械出图，也不重复绘制同一关系；
- 函数、切线、极限误差带、积分区域、向量和圆可用本地数学构图引擎绘制，无需依赖 GeoGebra 在线服务；
- 核心概念讲清后，只沿一个前置、辨析、后果、应用或边界关系向外延伸一步；
- 医学、生物医学和相关化学主题会加载专门适配层，使用结构—功能—损伤—后果链条；
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
- 条件式可视化提示及无绘图工具时的回退方案；
- 基础概念范围、自适应用图与单步知识延伸；
- GeoGebra 风格的坐标轴、函数曲线、点、线段、向量、圆、切线和区间阴影；
- 安全与运行时隐私边界；
- 退出验收与迁移检查；
- 可移植 frontmatter；
- WorkBuddy 便携 ZIP 结构；
- DeepSeek Harness、CodeBuddy、WorkBuddy、ZCode、Kimi Code 安装路径；
- 防止无授权覆盖已有 Skill；
- UTF-8 编码与上下文体积。

## 目录结构

```text
feynman-learning-mode/
├── feynman/
│   ├── SKILL.md
│   ├── agents/
│   │   └── openai.yaml
│   ├── assets/
│   │   └── medical/
│   │       ├── ATTRIBUTION.md
│   │       ├── openstax/
│   │       │   └── lymphatic-system-anatomy.jpg
│   │       └── reactome/
│   │           ├── immune-system-overview.svg
│   │           ├── immune-system-overview.png
│   │           ├── innate-immune-system.svg
│   │           ├── innate-immune-system.png
│   │           ├── adaptive-immune-system.svg
│   │           └── adaptive-immune-system.png
│   ├── references/
│   │   ├── chart-spec.md
│   │   ├── math-figures.md
│   │   ├── medical-concepts.md
│   │   ├── medical-mechanisms.md
│   │   ├── mindmaps.md
│   │   └── visual-hints.md
│   └── scripts/
│       ├── render_chart.py
│       ├── render_math_figure.py
│       └── render_mindmap.py
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
- [豆包工作技能帮助](https://www.doubao.com/work/docs/zh-cn/articles/081010973544-skills)
- [DeepSeek Harness Skill 文件系统源码](https://github.com/deepseek-ai/deepseek-harness/tree/master/packages/skill/skill-filesystem)
- [CodeBuddy CLI Skills 文档](https://www.codebuddy.ai/docs/zh/cli/skills)
- [ZCode Skill 文档](https://zcode.z.ai/en/docs/skill)
- [Kimi Code CLI Agent Skills 文档](https://www.kimi-cli.com/en/customization/skills.html)

## License

[MIT](LICENSE) 覆盖本项目原创代码与文档。`feynman/assets/medical/` 下的医学图像保留原许可：OpenStax 解剖图为 CC BY 3.0，Reactome 通路图为 CC BY 4.0。完整来源、署名和修改记录见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) 与 [医学资产署名](feynman/assets/medical/ATTRIBUTION.md)。本仓库不包含 BioGDP 原图或模板。
