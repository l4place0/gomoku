# policy-consolidation

## Summary

实现多时间尺度策略巩固（Policy Consolidation），用隐藏网络级联记住不同时间尺度的策略，无需任务边界知识。

## Motivation

报告 ref:36 (Kaplanis et al., ICML 2019) 描述的方法：用 cascade of hidden networks 同时记住 agent 在不同时间尺度的策略，通过正则化当前策略与自身历史来防止遗忘。比 replay buffer 更根本——不保留数据，而是保留知识。

## Scope

- 修改 `KataGomo/python/train.py` 的损失函数，添加策略巩固正则项
- 维护 slow_weights（指数移动平均）作为历史策略表示
- 损失 = 原始损失 + λ × KL(π_current || π_slow)
- λ 随训练步数自适应调整

## Success Criteria

- 训练 loss 曲线更平滑（无骤升骤降）
- 模型对早期学习的棋型保持识别能力
- 不显著增加训练时间（< 10% 开销）
