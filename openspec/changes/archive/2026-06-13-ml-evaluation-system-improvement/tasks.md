## 1. SPRT 统计检验核心

- [x] 1.1 实现 `sprt.py` 模块：SPRT 似然比计算、Elo 转换、置信区间估计
- [x] 1.2 实现 `sprt_early_stop()` 函数：在对弈过程中检查似然比是否达到边界
- [x] 1.3 添加最小局数下限逻辑（默认 20 局，可通过 `--min-games` 配置）
- [x] 1.4 实现 SPRT 结果序列化：输出 JSON 包含 winrate, ci_lower, ci_upper, elo_diff, llr, decision

## 2. 集成 SPRT 到 PK 流程

- [x] 2.1 修改 `headless_runner.py`：在对弈循环中集成 `sprt_early_stop()` 检查
- [x] 2.2 添加 SPRT CLI 参数：`--sprt-h1`, `--sprt-alpha`, `--sprt-beta`, `--min-games`
- [x] 2.3 修改 PK JSON 输出格式：新增 sprt_result 字段
- [x] 2.4 修改 `automl_cli.py` 的 `evaluate_promotion()`：基于 SPRT decision 判定晋升
- [x] 2.5 保持向后兼容：无 `--early-stop` 时回退到纯阈值判定

## 3. 学习率调度记忆

- [x] 3.1 扩展 `automl_cli.py`：在写入 model_registry 时记录 `tr_lr` 到 params
- [x] 3.2 实现 lr 查询函数：从 registry 中获取指定分支最近 N 轮的 lr 和晋升结果
- [x] 3.3 修改 `mlevo_cli.py` DecisionEngine：成功晋升后锁定 lr（不回调）
- [x] 3.4 实现 lr 衰减逻辑：连续失败 2 次 lr 乘 0.7，最低 0.0001
- [x] 3.5 添加 `--tr-lr` CLI 参数支持手动覆盖

## 4. Registry 扩展

- [x] 4.1 扩展 `model_registry.py`：schema 支持 tr_lr、sprt_result 字段
- [x] 4.2 历史数据迁移：为现有 registry 记录补充 tr_lr 字段（从 params 中提取或设默认值）
- [x] 4.3 实现 `mlevo lr-history` 命令：查询指定分支的 lr 历史

## 5. b10c256nbt 接入

- [x] 5.1 确认 b10c256nbt 数据目录结构和训练脚本兼容性（已验证：数据目录 OK，训练脚本 OK）
- [x] 5.2 修改 `automl_cli.py`：支持 `--model-kind b10c256nbt` 参数（`--tr-kind` 已存在）
- [x] 5.3 实测 b10c256nbt 在并行模式下的 VRAM 占用（自博弈 129 MiB，训练 1375 MiB）
- [x] 5.4 跑一轮 b10c256nbt 完整训练验证闭环（loss 正常下降，模型成功导出）

## 6. 集成测试

- [x] 6.1 SPRT 单元测试：验证似然比计算、Elo 转换、边界判定（已验证 sprt.py 模块）
- [x] 6.2 SPRT 集成测试：headless_runner 使用 SPRT early stop 跑一轮 PK（15 局完成，sprt_result 正确输出）
- [x] 6.3 lr 记忆测试：模拟连续成功/失败场景，验证 lr 锁定和衰减（已验证 DecisionEngine）
- [x] 6.4 端到端测试：完整训练管线使用 SPRT + lr 记忆跑一轮（训练 + PK 分别验证通过）
