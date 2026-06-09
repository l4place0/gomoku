## Why

首轮 10 轮训练验证了管线可行性（4 轮晋升，最终 winrate 54%），但当前架构存在三个核心问题：

1. **线性模型无家系**：模型覆盖式保存，无 parent 关系，无法追溯进化路径
2. **CLI 不是状态机**：硬编码路径、人类可读输出、Agent 无法安全地与 CLI 交互管控状态
3. **无可视化手段**：人类用户无法直观掌握训练进度和模型进化脉络

## What Changes

**DAG 模型图谱（节点 + 边）**
- 节点 = 模型状态（hash, winrate, params, timestamp），存储于 `model_registry.jsonl`
- 边 = 训练决策（OpenSpec proposal, 假设, 参数 diff, 结果），与 OpenSpec change 自然关联
- 支持分支训练（自动命名）、锦标赛合并、archive 已完成分支
- 默认串行执行，预留多 GPU 并行能力

**CLI 状态机（Headless Architecture）**
- CLI 是唯一的状态写入者，Agent 是纯决策者
- 状态机：`idle → running → idle/failed`，非法转换必须报错
- 所有输出结构化 JSON，暴露 `--json` 和 `--schema` 接口
- 训练支持 `--preset tiny/small/full` 参数梯度，tiny 用于 Agent 自动测试（~30s）
- 崩溃恢复：保守策略（标记 failed → 重跑整个 round）

**WebUI 训练控制台**
- React + Vite + D3.js 前端，FastAPI 纯 REST 后端（无 WebSocket）
- 仪表板（进度/指标）、图谱视图（模型 DAG + 边信息）、日志浏览器
- 后端是 CLI 的薄壳，所有操作走 CLI

**历史数据迁移**
- 现有 10 轮 ledger 自动推导 parent 关系，迁入 `model_registry.jsonl`
- 所有历史模型按 hash 归档，不再覆盖

**测试框架**
- 单元测试（纯逻辑）+ 集成测试（tiny 真实训练）+ WebUI 测试（前后端）+ E2E 验收（full）
- 故障注入：`--inject oom/nan/crash` 测试错误恢复
- 测试隔离：临时目录，不污染正式数据
- Agent 一键执行 `mlevo test --suite all --json`，你只做最终验收

## Capabilities

### New Capabilities

- `model-registry`: 模型版本注册表 — hash 寻址、parent 关系、元数据索引、模型检索与回溯、历史数据迁移
- `dag-engine`: 训练 DAG 引擎 — 节点(模型)+边(proposal)定义、分支创建/合并、拓扑排序、无环校验
- `headless-cli`: CLI 状态机框架 — 状态转换管控、结构化 JSON 输出、schema 自描述、preset 参数梯度、崩溃恢复
- `training-webui`: WebUI 训练控制台 — 仪表板、模型进化图谱可视化（含边信息）、日志浏览器
- `test-framework`: 测试框架 — 单元/集成/WebUI/E2E 分层、故障注入、测试隔离、Agent 自动执行

### Modified Capabilities

- `ml-training`: 训练流程从线性轮次改为 DAG 节点执行，模型保存从覆盖改为版本化，关联 OpenSpec proposal 作为边

## Impact

- **代码**：重构 `mlevo_cli.py`（状态机）、`automl_cli.py`（preset 支持）、`run_training_loop.py`（DAG 驱动）；新增 `model_registry.py`、`dag_engine.py`、`webui/`、`tests/`
- **数据格式**：新增 `model_registry.jsonl`；`evolution_ledger.json` 保留但不再作为主数据源
- **依赖**：FastAPI + uvicorn（WebUI 后端）、React + Vite + D3.js（WebUI 前端）
- **存储**：历史模型不再删除（每模型 ~35MB），预计额外 ~350MB
- **兼容性**：现有 10 轮数据可迁移，训练计划 JSON 保留，后期迁移到 YAML
