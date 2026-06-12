## MODIFIED Requirements

### Requirement: 模型注册表持久化
系统 SHALL 维护 `model_registry.jsonl` 文件作为模型版本注册表。每行 SHALL 是一个合法 JSON 对象，记录单个模型的完整元数据。系统 SHALL 以 append-only 方式写入，不修改已有行。

#### Scenario: 注册新模型
- **WHEN** 一轮训练完成且模型导出成功
- **THEN** 系统在 `model_registry.jsonl` 末尾追加一行 JSON，包含 hash、parent、round、winrate、promoted、params、change、timestamp、file 字段

#### Scenario: 重启后注册表完整
- **WHEN** 系统重启并读取 `model_registry.jsonl`
- **THEN** 所有历史记录完整无损，可正确构建模型图谱

#### Scenario: 注册包含 SPRT 结果的模型
- **WHEN** 一轮训练完成且 PK 使用 SPRT 评估
- **THEN** 注册记录的 params 字段 SHALL 包含 tr_lr 字段，新增 sprt_result 字段包含 decision、llr、elo_diff、ci_lower、ci_upper
