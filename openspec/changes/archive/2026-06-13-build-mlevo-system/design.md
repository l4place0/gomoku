## Context

当前 ML 训练由一个单体 SKILL (`automl-supervised-evolution`) 指导 Agent 行为，自适应规则以自然语言描述，没有代码执行保障。底层执行引擎 `automl_cli.py` (649 行) 实现了 selfplay → shuffle → train → export → pk 五阶段流水线，但缺少上层工作流管控。

参照项目中已有的 OpenSpec 系统 (`openspec` CLI + 4 个 SKILL + 4 个 Workflow)，构建平行的 MLEvo 系统。

## Goals / Non-Goals

**Goals:**
- 将 ML 进化计划变成结构化变更管理：每个计划有 proposal → design → plan → tasks 的完整 artifact 链
- 自适应决策规则从自然语言变成可执行、可测试的 Python 代码（嵌入 `mlevo_cli.py`）
- 研究报告的硬约束（参数下限、甜点区间）固化为 guardrail 检查
- Agent 初稿 + 人工修正的参数确认流程
- 每次进化计划归档后，训练知识沉淀到 `docs/ml/specs/`
- 4 个独立 SKILL 各司其职，与 OpenSpec 的 slash command 模式对齐

**Non-Goals:**
- 不重写 `automl_cli.py` 的执行逻辑（保留为底层引擎）
- 不构建 Web UI 或可视化面板
- 不实现全自动无人值守训练（保留人工确认节点）
- 不修改 KataGomo 本身的配置或代码

## Decisions

### Decision 1: 两层 CLI 架构

`mlevo_cli.py`（指挥官）管理工作流，`automl_cli.py`（士兵）执行单轮训练。

**选择**: `mlevo_cli.py` 通过 `subprocess` 调用 `automl_cli.py`，而不是 import 其函数。

**理由**: 保持两者独立部署和测试；`automl_cli.py` 已有稳定的 CLI 接口；避免循环依赖。

**替代方案**: 直接 import `automl_cli` 的函数 → 否决，因为会引入 DLL 和 CUDA 依赖到工作流管理层，破坏可测试性。

### Decision 2: 自适应决策引擎嵌入 CLI

**选择**: 将决策规则实现为 `mlevo_cli.py` 中的 `DecisionEngine` 类，包含：
- `rule_lr_decay()`: loss 平台期 → LR 减半（floor 0.0001）
- `rule_entropy_boost()`: 上轮未晋级 → sf_games ×1.2, sf_visits +16
- `rule_crash_recovery()`: NaN → rollback + LR 减半; OOM → batch 减半
- `guardrail_check()`: 研究报告硬约束检查（sf_games ≥ 100, pk_games ≥ 20, sh_samples ≥ 50000 等）

**理由**: 纯函数，无外部依赖，可用 pytest 100% 覆盖。

### Decision 3: 文档目录结构

```
docs/ml/
├── plans/                    ← 活跃进化计划
│   ├── <plan-name>/
│   │   ├── proposal.md       ← 目标/约束/验收线
│   │   ├── design.md         ← 技术决策/参数理由
│   │   ├── training_plan.json ← 执行参数（Agent初稿+人工修正）
│   │   ├── tasks.md          ← 轮次执行检查表
│   │   └── exploration.md    ← 探索分析（可选）
│   └── archive/              ← 已归档计划
│       └── YYYY-MM-DD-<name>/
│           ├── (全部 artifacts)
│           ├── conclusion.md
│           └── ledger_snapshot.json
├── specs/                    ← 持久化训练知识
│   └── training-knowledge.md
└── references/               ← 外部参考文档
    └── deep-research-report.md (symlink 或拷贝)
```

**理由**: 与 OpenSpec 的 `openspec/changes/` + `openspec/specs/` 完全同构，降低认知负担。

### Decision 4: mlevo CLI 命令集

| 命令 | 功能 | 类比 OpenSpec |
|---|---|---|
| `mlevo new plan "<name>"` | 创建计划目录 + scaffold artifacts | `openspec new change` |
| `mlevo list` | 列出所有计划 | `openspec list` |
| `mlevo status [--plan <name>]` | 查看计划状态 + 轮次进度 | `openspec status` |
| `mlevo decide --plan <name>` | 自适应推算下一轮参数 + 输出 JSON | _(无对应)_ |
| `mlevo run --plan <name> --round N` | 执行单轮训练（调用 automl_cli.py） | _(无对应)_ |
| `mlevo archive <name>` | 归档 + 知识沉淀 | `openspec` archive 流程 |

### Decision 5: SKILL 与 Workflow 映射

| SKILL | Workflow | 触发 |
|---|---|---|
| `.agent/skills/mlevo-explore/SKILL.md` | `.agent/workflows/ml-explore.md` | `/ml-explore` |
| `.agent/skills/mlevo-propose/SKILL.md` | `.agent/workflows/ml-propose.md` | `/ml-propose` |
| `.agent/skills/mlevo-apply/SKILL.md` | `.agent/workflows/ml-apply.md` | `/ml-apply` |
| `.agent/skills/mlevo-archive/SKILL.md` | `.agent/workflows/ml-archive.md` | `/ml-archive` |

### Decision 6: Agent 初稿 + 人工修正流程 (D3)

`mlevo decide` 输出的参数 JSON 包含：
- 基线参数（从 training_plan.json 当前阶段读取）
- 自适应调整（应用决策规则后的修改值）
- 决策理由链（每条规则为何触发/未触发）
- guardrail 警告（哪些参数低于硬约束）

Agent 在 `/ml-apply` 中调用 `mlevo decide`，将结果呈现给用户，用户修正后 Agent 使用修正后的参数调用 `mlevo run`。

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|---|---|---|
| `mlevo_cli.py` 与 `automl_cli.py` 参数不同步 | 传参错误 | `mlevo run` 严格透传 automl_cli 参数，不做翻译 |
| 研究报告 guardrail 值可能随硬件变化 | 错误的参数约束 | guardrail 值从 `docs/ml/specs/training-knowledge.md` 读取，可持续更新 |
| 4 个 SKILL 内容维护成本 | 过时的指导 | SKILL 只描述工作流姿态，具体参数知识在 `docs/ml/specs/` |
| 归档知识沉淀可能信息失真 | 错误经验传递 | 归档时人工确认结论 |
