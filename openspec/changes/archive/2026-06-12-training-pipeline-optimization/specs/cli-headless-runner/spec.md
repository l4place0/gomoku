## MODIFIED Requirements

### Requirement: automl_cli 流水线控制
automl_cli.py SHALL 将当前的串行流水线改为并行流水线。SHALL 在 selfplay 启动后立即启动 training（使用上一轮数据）。SHALL 将 shuffle 和 export 改为后台服务。

#### Scenario: 串行改并行
- **WHEN** 执行 `mlevo run --round N`
- **THEN** selfplay 和 training 并行运行，shuffle/export 后台运行

#### Scenario: 向后兼容
- **WHEN** 使用 `--serial` 参数
- **THEN** 恢复串行执行模式（用于调试）

### Requirement: nnMaxBatchSize 调优
automl_cli.py SHALL 支持通过参数指定 nnMaxBatchSize。SHALL 在 benchmark 模式下自动测试 64/96/128 并选择最优值。

#### Scenario: 手动指定
- **WHEN** 使用 `--nn-max-batch-size 96`
- **THEN** selfplay 配置使用 nnMaxBatchSize=96

#### Scenario: Benchmark 自动选择
- **WHEN** 使用 `--benchmark-batch-size`
- **THEN** 测试 64/96/128，选择 nnEvals/s 最高的值

### Requirement: Policy surprise weighting
native_selfplay_15.cfg SHALL 启用 policySurpriseDataWeight=0.5 以提高数据效率。

#### Scenario: Policy surprise 启用
- **WHEN** selfplay 运行时
- **THEN** 惊讶位置获得更高的训练权重
