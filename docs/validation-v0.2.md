# v0.2 第一轮验证记录

日期：2026-10-13。仓库基线：`5a01e9c`（main）。范围：最小 Skill 的文件格式、安装包完整性和维护检查，不包含模型效果实验。

## 已执行

本地环境：macOS，Python 3.12.14。开发依赖见 `requirements-dev.txt`；官方 `skills-ref` 固定在 `69ef37e9424c0a7ea9dd2293b559e43ec8176379`。依赖仅供测试，不随 Skill 安装。

| 检查 | 结果 | 证据范围 |
| --- | --- | --- |
| 官方 `skills-ref validate skills/life-finds-a-way` | `PASS` | 实际目录、必需字段、命名、frontmatter 合规 |
| `python -m unittest discover -s tests -v` | `PASS`，5 项测试 | 官方验证、真实 YAML 类型、入口长度、宪章一致性、独立安装完整性 |
| Codex / Claude Code 目录复制检查 | `PASS` | 在临时目录分别复制到 `.agents/skills/` 与 `.claude/skills/`；文件字节一致，入口引用仍位于包内且可读取 |
| 本机 skill-creator 的 `quick_validate.py` | `PASS` | 辅助检查，输出 `Skill is valid!`；不是 CI 的必需依赖 |
| `git diff --exit-code origin/main -- CHARTER.md history` | `PASS` | 宪章原文与历史快照未修改 |

核心命令的实际输出摘要：

```text
Valid skill: skills/life-finds-a-way
test_charter_is_an_exact_copy ... ok
test_entrypoint_stays_small ... ok
test_official_reference_validator ... ok
test_standalone_installations ... ok
test_standard_yaml_types ... ok
Ran 5 tests in 0.007s
OK
```

入口为 43 行，安装包仅含入口及原文参考两份文件。入口的 100 行限制是本仓库维护约定。CI 配置执行官方验证与同一组测试；远端实际执行状态以 PR Checks 为准，不从本地通过推定远端通过。

## 已知限制与未证明项

- `NOT_PROVEN`：尚未在 Codex 或 Claude Code 中开展独立的加载、显式调用、自动触发或行为端到端测试。安装路径与调用方式已对照官方文档，复制检查不等于客户端运行成功。
- `NOT_PROVEN`：尚未进行启用 / 未启用 Skill 的同条件比较，不能声称成功率、可靠性或资源效率提升。测试数和文件格式不是模型能力指标。
- `NOT_PROVEN`：未验证模型能否始终遵守停止与授权边界。提示词无法替代宿主权限、沙箱、预算限制与人工验收；也不能可靠识别或选择宿主模型。
- 当前没有模型行为实验，故没有可报告的实验模型、推理配置或模型调用成本。后续仅针对已确认的高级推理模型验证，不能将未知配置或轻量模型结果纳入该范围。
- 本轮仅进行了本地 CPU 格式测试与开发依赖下载，没有 GPU 训练、模型下载或额外模型 API 实验。整体耗时、token 与费用未独立计量，标为未知。
- 安装命令面向 macOS / Linux；Windows 手动目录安装尚未实测。宪章副本有维护成本，由字节一致性测试防止漂移。
- 提交前完整 `git diff --cached --check` 返回非零，原因是宪章副本保留了原文 13 处 Markdown 硬换行双空格。未修改原文来消除提示；排除该逐字副本后的变更空白检查通过。

建议本轮按“最小可分发 Skill + 格式证据”验收；将客户端实际调用与配对效果实验作为后续独立验证，不据此宣布能力提升。
