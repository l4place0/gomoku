## MODIFIED Requirements

### Requirement: 训练流程
训练流程 SHALL 从线性轮次驱动改为 DAG 节点执行。每个训练轮次 SHALL 创建一个模型节点（写入 model_registry.jsonl）和一条边（关联 OpenSpec change）。训练完成后模型 SHALL 按 hash 归档到 `models/` 目录，不再覆盖 `model.bin.gz`。

#### Scenario: DAG 模式训练
- **WHEN** 执行 `mlevo run --round 11 --change "my-change" --json`
- **THEN** 训练完成后：1) 模型按 hash 归档 2) registry 追加节点记录 3) registry 追加边记录 4) `model.bin.gz` 更新为新模型的符号链接或副本

#### Scenario: 训练失败也记录
- **WHEN** 训练完成但 winrate < 晋升阈值
- **THEN** 模型仍归档、registry 仍记录（promoted=false），不丢弃

### Requirement: 模型保存策略
模型保存 SHALL 从覆盖式改为版本化。每次训练产出的模型 SHALL 按 hash 归档到 `models/{hash}.bin.gz`。`KataGomo/models/model.bin.gz` SHALL 始终指向当前 mainline 最新 promoted 模型（符号链接或副本）。

#### Scenario: 历史模型不丢失
- **WHEN** 连续训练 10 轮
- **THEN** `models/` 目录下有 10 个模型文件（按 hash 命名），`model.bin.gz` 指向最新 promoted 的模型

#### Scenario: 模型文件可追溯
- **WHEN** 用户执行 `mlevo model --hash a1b2c3 --json`
- **THEN** 返回该模型的元数据和文件路径

### Requirement: Preset 参数支持
训练流程 SHALL 支持 `--preset tiny|small|full` 参数覆盖训练计划中的默认参数。tiny 模式用于快速测试，small 模式用于 CI，full 模式用于正式训练。

#### Scenario: tiny preset 快速验证
- **WHEN** 执行 `mlevo run --round 1 --preset tiny --json`
- **THEN** 使用最小参数（sf_games=5 等）完成全流程，30 秒内出结果
