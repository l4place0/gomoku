## 1. 训练计划创建

- [x] 1.1 创建 `v3-anti-overfit` 训练计划
- [x] 1.2 配置反过拟合参数（epochs=1, lr=0.001, games=400）
- [x] 1.3 创建 OpenSpec change 关联

## 2. 开局随机化

- [x] 2.1 创建 opening_seeds.json（30 条平衡种子）
- [x] 2.2 创建 select_opening.py（随机选种子 + 写 cfg）
- [x] 2.3 集成到 automl_cli.py（selfplay 前自动调用）

## 3. 执行训练

- [ ] 3.1 创建分支 v3-anti-overfit（从 round 7 模型分叉）
- [ ] 3.2 执行 Round 1
- [ ] 3.3 执行 Round 2
- [ ] 3.4 执行 Round 3
- [ ] 3.5 执行 Round 4
- [ ] 3.6 执行 Round 5

## 4. 验证

- [ ] 4.1 检查每轮 winrate 趋势
- [ ] 4.2 检查训练 loss 收敛
- [ ] 4.3 对比 R8-R10 的过拟合表现
