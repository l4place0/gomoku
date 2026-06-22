# anti-forget-l2-replay-buffer

## Summary

实现回放缓冲机制，保留历史自弈数据的子集并与当前轮数据混合训练，防止模型遗忘已学知识。

## Motivation

当前管线每轮完全替换自弈数据——shuffle 阶段删除旧的 shuffledddata，只用当前轮的 200K 局训练。这意味着每轮训练后，前一轮的所有数据完全丢失。研究报告指出 KataGo 的分布式训练项目使用数据窗口机制，而 Tablut AlphaZero 实验表明回放缓冲是缓解灾难性遗忘的关键技术。

## Scope

- `ml/automl_cli.py` — selfplay 完成后复制子集到 replay_buffer/；shuffle 阶段混合多个数据源
- `ml/data/replay_buffer/` — 新增目录，存储历史高价值数据
- 配置参数：`--replay-ratio`（默认 0.2）、`--replay-max-rounds`（保留最近 N 轮）

## Out of Scope

- shuffle.py 本身不需修改（已支持多目录输入 via `-dirs`）
- train.py 不需修改
- 黄金数据/课程机制（属于 Layer 5）

## Success Criteria

- replay_buffer/ 目录自动维护，大小可控
- shuffle 日志显示混合比例：80% 当前轮 + 20% 回放
- 训练 loss 曲线更平滑，无骤升（遗忘指标）
