# Tasks: Replay Buffer

- [x] 1. `automl_cli.py create_parser()` 添加 `--replay-ratio` 和 `--replay-max-rounds` 参数
- [x] 2. 实现 `_fill_replay_buffer()` 函数：selfplay 完成后采样数据到 replay_buffer/
- [x] 3. 实现 `_cleanup_replay_buffer()` 函数：FIFO 淘汰超出轮次
- [x] 4. `run_selfplay()` 结束时调用 `_fill_replay_buffer()`
- [x] 5. `run_shuffle()` 修改 datadir 构建逻辑，混合当前轮 + replay 目录
- [x] 6. 语法检查验证
