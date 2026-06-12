## ADDED Requirements

### Requirement: 学习率记录
系统 SHALL 在每轮训练的 model_registry 记录中保存实际使用的学习率值。

#### Scenario: 记录 lr 到 registry
- **WHEN** 一轮训练完成并写入 model_registry.jsonl
- **THEN** 记录的 params 字段 SHALL 包含 `tr_lr` 字段，值为该轮实际使用的学习率

### Requirement: 学习率锁定
DecisionEngine SHALL 在模型成功晋升后锁定当前 lr，下一轮不再回调。

#### Scenario: 成功晋升后 lr 锁定
- **WHEN** 模型以 lr=X 成功晋升
- **THEN** 下一轮训练 SHALL 使用 lr=X，不高于 X

#### Scenario: 手动覆盖 lr
- **WHEN** 用户通过 CLI 参数 `--tr-lr 0.0003` 指定 lr
- **THEN** 系统使用用户指定的值，忽略锁定逻辑

### Requirement: 学习率衰减
DecisionEngine SHALL 在连续失败时自动降低 lr。

#### Scenario: 连续失败 2 次
- **WHEN** 同一父模型连续 2 次训练失败
- **THEN** 下一轮 lr SHALL 乘以 0.7

#### Scenario: lr 最低阈值
- **WHEN** lr 衰减后低于 0.0001
- **THEN** lr SHALL 保持在 0.0001，不再衰减

### Requirement: 学习率历史查询
系统 SHALL 支持查询指定分支的 lr 历史。

#### Scenario: 查询 lr 历史
- **WHEN** 用户执行 `mlevo lr-history --branch v4-stabilize --json`
- **THEN** 系统返回该分支每轮的 lr 值和对应的晋升结果
