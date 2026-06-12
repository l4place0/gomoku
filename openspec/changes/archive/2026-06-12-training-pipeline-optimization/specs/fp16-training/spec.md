## ADDED Requirements

### Requirement: Selfplay 推理启用 FP16
native_selfplay_15.cfg SHALL 设置 `cudaUseFP16 = true` 以减少 selfplay 推理的 VRAM 占用。

#### Scenario: FP16 selfplay 正常运行
- **WHEN** selfplay 使用 FP16 推理
- **THEN** VRAM 占用减少 30-40%，推理结果与 FP32 一致

### Requirement: Training 启用 FP16
automl_cli.py SHALL 传 `-use-fp16` 参数给 train.py。SHALL 在 FP16 训练时监控 GradScaler 的 loss scale factor。

#### Scenario: FP16 训练稳定
- **WHEN** 使用 FP16 训练且 lr >= 0.001
- **THEN** GradScaler 自动处理 NaN，loss scale factor 稳定

#### Scenario: FP16 训练不稳定
- **WHEN** loss scale factor 反复 backoff（连续 5 次以上）
- **THEN** 自动回退到 FP32 训练，记录警告

### Requirement: FP16 VRAM 节省验证
benchmark SHALL 对比 FP32 和 FP16 的 VRAM 占用。SHALL 输出 VRAM 节省百分比。

#### Scenario: VRAM 节省达标
- **WHEN** FP16 训练的 VRAM 占用 < FP32 的 70%
- **THEN** 标记 FP16 VRAM 节省验证通过
