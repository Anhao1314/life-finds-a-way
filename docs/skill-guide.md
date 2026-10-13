# Life Finds a Way · Skill v0.2

这是现有 [研发宪章](../CHARTER.md) 的最小 Agent Skill 实现。开发者描述真实问题、目标与边界，模型自主选择路径，做必要验证并报告结果。Skill 版本 `0.2.0` 与宪章版本 `v1.0` 分开编号；本轮不修订宪章。

## 安装

取得本仓库包含 `skills/life-finds-a-way/` 的版本，在仓库根目录执行以下命令。PR 合并前请使用 `feat/v0.2-agent-skill` 分支；合并后可使用主分支。

```sh
git clone https://github.com/Anhao1314/life-finds-a-way.git
cd life-finds-a-way
# 仅在本轮 PR 尚未合并时执行：
git switch feat/v0.2-agent-skill
```

选择目标宿主，复制**整个目录**。以下命令适用于 macOS / Linux 的 shell；Windows 可按表中路径手动复制文件夹。

Codex（个人安装）：

```sh
skill_dest="$HOME/.agents/skills/life-finds-a-way"
test ! -e "$skill_dest" && test ! -L "$skill_dest" &&
  mkdir -p "$HOME/.agents/skills" &&
  cp -R skills/life-finds-a-way "$skill_dest"
```

Claude Code（个人安装）：

```sh
skill_dest="$HOME/.claude/skills/life-finds-a-way"
test ! -e "$skill_dest" && test ! -L "$skill_dest" &&
  mkdir -p "$HOME/.claude/skills" &&
  cp -R skills/life-finds-a-way "$skill_dest"
```

若目标已存在，命令会以非零状态退出，不覆盖已有内容。更新时先比较并备份旧目录，再替换。安装后新开会话；Codex 也可用 `/skills` 查找。未出现时检查目录是否多嵌套了一层、是否存在同名安装或被禁用。

| 宿主 | 个人目录 | 项目目录（相对目标项目根目录） | 显式调用 |
| --- | --- | --- | --- |
| Codex | `~/.agents/skills/life-finds-a-way/` | `.agents/skills/life-finds-a-way/` | `$life-finds-a-way` |
| Claude Code | `~/.claude/skills/life-finds-a-way/` | `.claude/skills/life-finds-a-way/` | `/life-finds-a-way` |

选择个人或项目作用域即可，避免在同一宿主重复安装。本包使用标准 frontmatter，允许宿主按描述自动选择；自动触发取决于宿主与模型，不保证每次触发。需要确定调用时使用上表的显式方式。

安装内容只有 `SKILL.md` 和 `references/CHARTER.md`，不依赖本仓库其他文件或运行时。Python 和下文验证依赖只供维护者运行格式测试，使用 Skill 不需要它们。

## 调用

先在宿主选择高级推理模型与适当推理配置，再发送自然语言任务。无需填完整表格；只需提供影响成功与授权的信息。例如在 Codex 中：

```text
$life-finds-a-way
CSV 导入遇到空行后会漏掉后续记录。目标是所有有效记录都能导入。
允许修改导入代码并运行本地 CPU 测试；不改公开接口，不调用付费服务，
不部署。请核对现有行为，自主选择修复路径，报告复现、验证和未解决项。
```

在 Claude Code 中将第一行换为 `/life-finds-a-way`，其余相同。更开放的任务可描述：

```text
搜索结果相关性差，但不确定是召回还是排序问题。请利用现有样本定位瓶颈，
选择最小验证。限 30 分钟本地 CPU 实验，不下载模型、不改冻结评测集；
不能得出结论时保留未知，不为提高分数改变历史阈值。
```

模型应在已有授权内推进，触及新权限或资源边界时暂停相关动作。Skill 是提示性指导，不能强制执行沙箱、预算、审批或模型选择；这些仍由宿主和使用者控制。对已有明确授权不重复索取批准，对失败与未知如实保留。

## 维护与格式验证

Python 3.11+ 与 Git；首次安装开发依赖需要联网。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/skills-ref validate skills/life-finds-a-way
.venv/bin/python -m unittest discover -s tests -v
```

测试使用固定源码版本的官方 `skills-ref` 检查实际 Skill，并补充 YAML 类型、短入口、宪章字节一致性、两个宿主目录中的独立复制与引用完整性检查。GitHub Actions 执行同样的核心验证。100 行是本仓库对入口的维护上限，不是开放规范的硬性要求。

`CHARTER.md` 是唯一维护源；`skills/life-finds-a-way/references/CHARTER.md` 是随包携带的完整副本。未来有依据地修订宪章后，用 `cp CHARTER.md skills/life-finds-a-way/references/CHARTER.md` 同步，保留历史快照并运行测试。

本轮结果与未验证项见 [验证记录](validation-v0.2.md)。格式通过不能证明模型理解、遵守边界或改善任务表现。后续行为实验只纳入已确认的高级推理模型，记录实际模型、推理配置、任务版本、基线、原始输出、失败和可测成本；采用相同条件比较启用与未启用 Skill 的结果，不改历史评分规则。这里没有新增评测运行框架。

## 规范依据

- [Agent Skills 规范](https://agentskills.io/specification)：目录、frontmatter 与引用规则。
- [Codex Skills 官方文档](https://developers.openai.com/codex/skills)：发现路径与显式调用。
- [Claude Code Skills 官方文档](https://code.claude.com/docs/en/skills)：发现路径与 slash 调用。
- [官方 skills-ref 源码版本](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379/skills-ref)：本轮格式验证器。

以上宿主约定于 2026-10-13 核对。宿主行为可能随版本改变；本轮没有将文件系统安装检查表述为客户端端到端验证。
