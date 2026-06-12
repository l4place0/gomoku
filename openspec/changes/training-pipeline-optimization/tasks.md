## 1. VRAM 基准测试

- [x] 1.1 实测当前 selfplay 的 VRAM 占用（nnMaxBatchSize=64/96/128）
- [x] 1.2 实测当前 training 的 VRAM 占用（batch=64/96/128）
- [x] 1.3 实测 selfplay + training 并行时的总 VRAM 占用
- [x] 1.4 确定并行时的 VRAM 预算分配方案

## 2. FP16 启用

- [x] 2.1 在 native_selfplay_15.cfg 中设置 cudaUseFP16=true
- [x] 2.2 在 automl_cli.py 中启用 --tr-fp16 参数
- [x] 2.3 实测 FP16 selfplay 的 VRAM 节省百分比
- [x] 2.4 实测 FP16 training 的稳定性（监控 GradScaler loss scale）
- [x] 2.5 如果 FP16 不稳定，实现自动回退到 FP32 的逻辑

## 3. nnMaxBatchSize 调优

- [x] 3.1 实现 benchmark 模式：测试 nnMaxBatchSize=64/96/128 的 nnEvals/s
- [x] 3.2 确定 GTX 1650 Ti 上的最优 nnMaxBatchSize
- [x] 3.3 更新 native_selfplay_15.cfg 使用最优值

## 4. Shuffle/Export 异步化

- [ ] 4.1 实现 shuffle 后台服务：监听 selfplay 数据目录，新数据到达时自动触发 shuffle
- [ ] 4.2 实现 export 后台服务：监听 training checkpoint，更新时自动触发 export
- [ ] 4.3 从串行流水线中移除 shuffle 和 export 阶段
- [ ] 4.4 实现后台服务的启动和关闭管理

## 5. 流水线并行化

- [x] 5.1 重构 automl_cli.py：将 selfplay 和 training 改为独立子进程
- [x] 5.2 实现进程并行启动逻辑
- [x] 5.3 实现 VRAM 监控和超限自动降级
- [x] 5.4 实现进程崩溃检测和清理
- [x] 5.5 添加 --serial 参数支持串行模式（向后兼容）

## 6. 配置更新

- [x] 6.1 更新 native_selfplay_15.cfg：添加 policySurpriseDataWeight=0.5
- [x] 6.2 更新 automl_cli.py：添加 nnMaxBatchSize 参数
- [ ] 6.3 更新 mlevo_cli.py DecisionEngine：适配 FP16 和 batch size 逻辑

## 7. 集成测试

- [x] 7.1 端到端测试：并行流水线跑 1 轮，验证结果正确
- [x] 7.2 性能对比：并行 vs 串行的单轮耗时
- [x] 7.3 稳定性测试：连续跑 3 轮，验证无崩溃
- [x] 7.4 训练质量验证：对比并行前后的 loss 和胜率
