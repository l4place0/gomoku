# adaptive-curriculum

## Summary

实现自适应课程生成：基于 SPIRAL 的自动对手课程 + SPICE 的 corpus grounding + Vocabulary Dropout 的多样性维护。

## Motivation

报告中的三个互补方法：
- SPIRAL (ref:14)：完全在线多轮多 agent 自弈 RL，自动课程选择更强对手
- SPICE (ref:15)：从 corpus 挖掘生成多样化推理任务，防止多样性坍塌
- Vocabulary Dropout (ref:17)：对 proposer 的输出 logits 施加随机 mask，防止锁定到固定序列

## Scope

- 自适应对手选择：selfplay 时从历史模型池中按能力匹配对手（而非只用当前 best）
- 多样性监控：跟踪 selfplay 检索的开局/棋型分布，检测多样性坍塌
- 多样性注入：当检测到多样性下降时，强制使用随机开局或增加 Dirichlet 噪声权重

## Success Criteria

- selfplay 开局分布的熵值保持稳定（不单调下降）
- 模型在多种开局下均有合理表现
- 检索多样性指标在 WebUI 可视化
