## 1. mlevo-propose 更新

- [x] 1.1 重写 Action Guide：加入 OpenSpec propose 流程（`openspec new change` → `mlevo new plan` → `--change` 关联）
- [x] 1.2 添加 `mlevo schema --json` 引用作为 Agent 自描述入口
- [x] 1.3 更新示例：展示完整的 propose → plan → decide 工作流

## 2. mlevo-apply 更新

- [x] 2.1 更新 `mlevo decide` 命令：加入 `--branch` 参数说明
- [x] 2.2 更新 `mlevo run` 命令：加入 `--branch`/`--preset`/`--change`/`--inject` 参数说明
- [x] 2.3 添加模型注册表自动记录说明：训练完成后自动写入 model_registry.jsonl
- [x] 2.4 添加 DAG 图谱更新说明：训练完成后图谱自动更新
- [x] 2.5 添加故障注入使用说明：`--inject oom/nan/crash` 测试错误恢复
- [x] 2.6 添加 `mlevo test --suite unit` 建议：训练前先验证管线
- [x] 2.7 添加 WebUI 监控提示：长时间训练时建议通过 WebUI 监控

## 3. mlevo-archive 更新

- [x] 3.1 更新归档流程：加入模型注册表归档说明
- [x] 3.2 关联 OpenSpec archive：`openspec archive` + `mlevo archive` 双重归档
- [x] 3.3 更新结论生成：引用模型注册表数据而非 ledger

## 4. mlevo-explore 更新

- [x] 4.1 数据源迁移：`evolution_ledger.json` → `model_registry.jsonl`
- [x] 4.2 硬件约束更新：GTX 1060 → GTX 1650Ti
- [x] 4.3 添加 DAG 分析命令：`mlevo graph --with-edges --json`
- [x] 4.4 添加模型查询命令：`mlevo models --branch/--min-winrate --json`
- [x] 4.5 添加历史追溯命令：`mlevo history --model <hash> --json`
- [x] 4.6 添加分支对比能力：对比不同分支的模型表现
- [x] 4.7 更新 Action Guide：引用新命令而非旧 ledger 读取

## 5. 验证

- [x] 5.1 运行 `mlevo test --suite all` 确认管线完整性
- [x] 5.2 逐个 skill 检查命令引用是否正确
