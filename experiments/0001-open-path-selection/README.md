# 实验 0001 · 开放路径与选择（Open Path Selection）

> **状态：`DRAFT` —— 预注册草案与任务材料。实验未运行，本目录没有任何运行结果、运行清单或分析产物。**
> LFAW 方法状态保持 **`NOT_PROVEN`**：设计一个实验不构成任何有效性证据。

这是《生命会寻求自己的出路》的第一次自我应用：用最小可证伪的对照实验，直接检验 LFAW 任务契约（C 组）是否比详细施工 Prompt（B 组）和基本目标 Prompt（A 组）带来更高的独立验收任务成功率。

## 目录

| 文件 | 内容 | 可见性 |
| :--- | :--- | :--- |
| [`preregistration.md`](./preregistration.md) | 研究问题、假设、组设计、终点、判定规则、随机化、纪律与局限 | 公开 |
| [`tasks.yaml`](./tasks.yaml) | 12 个任务：来源、固定 commit、任务事实、验收方式、B 组方案 | **部分保密**（见下） |
| [`prompts/common-core.md`](./prompts/common-core.md) | 三组共享的任务事实骨架 + 通用边界 + 统一交付格式 | 公开（模板） |
| [`prompts/A-basic-goal.md`](./prompts/A-basic-goal.md) | A 组：基本目标 Prompt | 公开（模板） |
| [`prompts/B-prescribed-path.md`](./prompts/B-prescribed-path.md) | B 组：详细施工 Prompt | 公开（模板） |
| [`prompts/C-lfaw-contract.md`](./prompts/C-lfaw-contract.md) | C 组：LFAW 契约 Prompt | 公开（模板） |

## 信息流（执行时强制）

| 材料 | 进入哪组 Prompt | 说明 |
| :--- | :--- | :--- |
| `tasks.yaml` 的 `real_user_problem` / `starting_state` / `tools_and_resources` / `permission_boundaries` | **三组逐字一致**（注入 common-core） | 组间唯一差异在"任务指导"一节 |
| `tasks.yaml` 的 `b_prescribed_path` | **仅 B 组** | 实验前写好的合理人类方案 |
| C 组契约要素 | 仅 C 组 | 质疑预设 / 核对基线 / 自主选路 / 最小判别实验 / 不维持错误路线 / 严守权限 / 如实报告 |
| `tasks.yaml` 的 `independent_acceptance`（含 `hidden_reference`：上游修复 diff 等 Gold 材料） | **任何组都不注入** | 仅验收方在运行前用于脚本化验收与基线复现 |
| 其他组的 Prompt、过程、结果 | 互相隔离 | 每次运行为独立新会话 |

**组装约定：** Prompt 模板文件中第一个 `---` 之前的内容是模板文档（说明注入机制），组装时**不进入**组 Prompt；组 Prompt = `---` 之后的正文 + 对应注入（`{{COMMON_CORE}}`、`{{TASK_FACTS}}`、`{{PRESCRIBED_PATH}}`）。

## 任务集一览

- **LF001–LF007**：第三方库真实回归（[pallets/click](https://github.com/pallets/click) ×3、[Textualize/rich](https://github.com/Textualize/rich) ×3、[psf/requests](https://github.com/psf/requests) 性能回归 ×1），base commit 为上游修复 PR 合并提交的第一父提交；
- **LF008–LF011**：[ClaimLedger](https://github.com/Anhao1314/ClaimLedger)（作者仓库）开放 issue #10/#11/#12 与 `docs/refactor-design.md` 的四个真实工程任务；
- **LF012**：[RL-Sentinel](https://github.com/Anhao1314/RL-Sentinel) 规则回测召回根因分析——**明示候选**，验收方式待所有者确认，确认前不运行。

所有引用（issue / commit / PR）已于 2026-10-28 经 GitHub API 核查；核查方式与义务见预注册 §4.3、§4.4。

## 执行前检查单（由仓库所有者完成；本工作包不执行）

1. 确认模型与预算，填写 [`preregistration.md`](./preregistration.md) **附录 B** 冻结参数登记表；
2. 逐任务完成基线复现（预注册 §4.4）：隐藏验收判据在 base commit 上判为失败；
3. 决定候选任务 LF012 的处置（确认判据、替换或移出，记录于附录 C）；
4. 复核随机化顺序表（预注册附录 A，种子 `20261028`）；
5. 建立运行清单（`runs/`，执行时创建）与派生分析目录（`analysis/`，执行时创建）——**原始与派生分离**；
6. 全部就绪后按预注册执行；任何修改走附录 C amendments。

## 纪律速览

- 主要终点唯一：独立验收判定的任务成功；分析以 task 为配对单位，重复只作稳定性；
- 最高结论 `PROMISING`，不外推"普遍有效"；`NOT_SUPPORTED` 只针对本次设计；
- 严重权限或边界违规不可被成功率抵消；
- 负面结果与 `INCONCLUSIVE` 同权重保留；不得为 PASS 修改 Gold、测试、阈值或原始日志。
