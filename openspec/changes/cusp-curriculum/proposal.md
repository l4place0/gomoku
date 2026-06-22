# cusp-curriculum

## Summary

实现 CuSP (Curriculum Self-Play) 框架的反灾难性利用机制，确保模型在渐进探索新棋型时不遗忘已掌握的目标。

## Motivation

报告 ref:39 (Du, Abbeel, Grover) 的 CuSP 框架：多 agent 自弈课程生成，通过 "anti-catastrophic exploitation" 平衡探索与保留。当前 L5 的 golden data 是简化版——只保留高价值位置，CuSP 更系统化地管理"已解目标"和"待解目标"。

## Scope

- 维护"已解目标"数据库（模型已掌握的棋型/开局/中盘模式）
- 新一轮 selfplay 生成的棋局如果涉及已解目标，检查模型是否仍能正确应对
- 如果已解目标表现退化，将这些位置加入训练数据（类似 replay buffer 但更智能）
- 课程难度自适应：基于当前能力水平选择对手强度

## Success Criteria

- 已解目标的识别率不随训练轮次下降
- 课程难度自动适应模型能力
- 训练效率不低于当前方案
