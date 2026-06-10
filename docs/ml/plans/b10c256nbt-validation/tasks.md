# b10c256nbt Validation Tasks

## R1: Smoke Test
- [ ] 运行自博弈 (sf_games=800, sf_visits=128, b10c256nbt)
- [ ] Shuffle 数据 (sh_samples=150000)
- [ ] 训练 (tr_lr=0.001, tr_batch=64, tr_epochs=1)
- [ ] PK 评估 (pk_games=100, pk_visits=128/128)
- [ ] 验证: vloss < 1.2, 无 OOM/NaN

## R2: Convergence Check
- [ ] 运行自博弈
- [ ] Shuffle 数据
- [ ] 训练
- [ ] PK 评估
- [ ] 验证: vloss < 1.0, pacc1 > 42%

## R3: Promotion Test
- [ ] 运行自博弈
- [ ] Shuffle 数据
- [ ] 训练
- [ ] PK 评估
- [ ] 验证: PK 胜率 > 58%
