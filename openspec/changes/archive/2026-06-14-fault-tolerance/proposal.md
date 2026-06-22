# fault-tolerance

## Summary

为训练管线添加多层容错机制：进程级自动重启、检查点级崩溃恢复、数据级完整性验证。

## Motivation

当前管线无容错——selfplay/train 进程崩溃直接返回 `StageResult(False)`，整个轮次失败。报告描述 Ray Train 三层容错（worker 进程 / worker 节点 / job driver），DLRover 的 flash checkpoint 可秒级恢复。我们的单机管线不需要分布式容错，但进程崩溃恢复和数据完整性检查是低成本高回报的改进。

## Scope

- **进程级**：selfplay/train 阶段添加自动重试（最多 3 次），每次重试降低参数（如减少 sf_games）
- **检查点级**：train 崩溃后自动从最近 checkpoint 恢复，而非从头训练
- **数据级**：shuffle 前验证 selfplay NPZ 文件完整性（大小 > 0、可读取）
- **管线级**：`run_pipeline()` 失败后自动回退到 serial 模式重试

## Success Criteria

- selfplay 崩溃后自动重试 3 次（参数递减）
- train 崩溃后从 checkpoint 恢复（而非重新训练）
- 损坏的 NPZ 文件被自动跳过并警告
- 管线整体成功率从 ~80% 提升到 ~95%
