# Tasks: Multi-Tier Fault Tolerance

- [x] 1. 新增 `run_subprocess_with_retry()` 函数（指数退避重试）
- [x] 2. `run_selfplay()` 使用重试逻辑
- [x] 3. `run_train()` 使用重试逻辑 + 检查点恢复检测
- [x] 4. 新增 `validate_selfplay_data()` 函数（NPZ 完整性验证）
- [x] 5. `run_shuffle()` 前调用数据验证
- [x] 6. `create_parser()` 添加 `--fault-tolerance` 参数
- [x] 7. 语法检查 + 验证
