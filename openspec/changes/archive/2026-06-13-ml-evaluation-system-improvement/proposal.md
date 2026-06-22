## Why

训练管线的 PK 评估系统存在三个互相强化的问题：`evaluate_promotion()` 是纯阈值判定（`winrate >= threshold`），没有统计检验；PK 局数默认 30-100 局，方差大导致好模型被误杀（如 mainline r8 以 52.2% 被拒）；学习率调度无记忆，成功晋升后 lr 又被调回去（v4-stabilize r7-8 用 0.0003 成功，r9 跳回 0.0005 失败）。这三个问题共同导致管线在连续失败后停滞，当前已停在 v4-stabilize r10。

## What Changes

- **SPRT 统计检验替代纯阈值判定**: 在 `evaluate_promotion()` 中实现 Sequential Probability Ratio Test，用更少局数做出更可靠的晋升/拒绝决策，支持 early stop
- **学习率调度记忆**: 在 model_registry 中记录每轮的 lr 和晋升结果，DecisionEngine 在成功晋升后锁定 lr 不回调，失败时可微降
- **推进 fix-pk-and-dual-model 完成**: 当前卡在 2/8，核心是 WorkerClient IPC 和 VCF solver 初始化修复
- **b10c256nbt 接入注册表**: 将 b10c256nbt 的训练数据和模型接入 model_registry，支持通过 mlevo 管理

## Capabilities

### New Capabilities

- `sprt-evaluation`: SPRT 统计检验评估系统 — 替代纯阈值判定，支持 early stop、置信区间、Elo 差异估计
- `lr-scheduling-memory`: 学习率调度记忆 — 记录 lr 历史，成功锁定、失败微降，防止 lr 来回跳动

### Modified Capabilities

- `model-registry`: 扩展 registry schema 支持记录 lr、pk_games、confidence_interval 等评估元数据
- `cli-headless-runner`: 集成 SPRT early stop 逻辑，PK 结果包含统计显著性指标

## Impact

- `ml/automl_cli.py`: `evaluate_promotion()` 重写为 SPRT；lr 调度逻辑加入 registry 查询
- `ml/model_registry.py`: schema 扩展，新增 lr/confidence/sprt_result 字段
- `ml/mlevo_cli.py`: DecisionEngine 适配 SPRT 结果和 lr 记忆
- `tools/headless_runner.py`: SPRT early stop 集成（依赖 fix-pk-and-dual-model 完成）
- `tools/ai_worker.py`: VCF solver 初始化修复（已在 fix-pk-and-dual-model 中）
- `ml/data/model_registry.jsonl`: 历史数据迁移，补充缺失字段
