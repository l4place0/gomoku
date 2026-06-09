## Context

Gomoku 训练管线当前是线性轮次驱动：`run_training_loop.py` → `mlevo_cli.py` → `automl_cli.py`，模型覆盖式保存，无版本化。完成首轮 10 轮验证后，需要升级为 DAG 模型图谱 + CLI 状态机 + WebUI 监控的工程化架构。

当前代码结构：
- `mlevo_cli.py`：CLI 入口，DecisionEngine 自适应调参
- `automl_cli.py`：5 阶段管线（selfplay/shuffle/train/export/pk）
- `run_training_loop.py`：轮次循环驱动
- `logs/evolution_ledger.json`：10 轮训练记录
- `training_data/torchmodels_toexport/`：20 个 checkpoint 目录

## Goals / Non-Goals

**Goals:**
- 模型进化可追溯：每个模型有 hash、parent、关联 proposal
- CLI 是唯一状态管控者：Agent 通过 JSON 交互，不直接改文件
- 分支训练：从任意历史模型分叉，锦标赛合并
- WebUI 可视化：图谱 + 仪表板 + 日志
- 测试可自动化：Agent 一键跑测试，用户只做验收
- 历史数据可迁移：现有 10 轮数据无损迁入

**Non-Goals:**
- 不做 WebSocket 实时推送（REST 轮询足够）
- 不做模型蒸馏合并（仅锦标赛，蒸馏后续再加）
- 不做多 GPU 并行调度（预留接口，不实现）
- 不迁移训练计划到 YAML（JSON 保留，后期迁移）
- 不重构 KataGomo 底层训练代码

## Decisions

### D1: 模型注册表格式 — JSONL 文件

**选择**: `model_registry.jsonl`，每行一个 JSON 对象

**替代方案**:
- SQLite：查询能力强，但增加依赖，Agent 不便直接读
- JSON 单文件：简单但大了之后读写慢，且并发写入不安全

**理由**: JSONL 对 Agent 友好（逐行读取、grep 友好），无额外依赖，append-only 天然防并发冲突。

```
每行结构:
{"hash": "a1b2c3", "parent": null, "round": 1, "branch": "mainline",
 "winrate": 0.909, "promoted": true, "params": {...},
 "change": "build-mlevo-system", "hypothesis": "初始训练",
 "timestamp": "2026-06-05T15:00:00Z",
 "file": "models/a1b2c3.bin.gz"}
```

### D2: CLI 架构 — 子命令 + 状态机

**选择**: `mlevo` 单入口 + 子命令（`status`, `run`, `branch`, `merge`, `graph`, `test` 等），全局 `--json` 输出

**替代方案**:
- 多个独立脚本（`mlevo_run.py`, `mlevo_status.py`）：分散，不便发现
- HTTP 服务：过重，Agent 通过 shell 调用更自然

**理由**: 单入口 + 子命令是 CLI 标准模式，`--json` 让 Agent 可解析，`--schema` 让 Agent 自描述。

**状态机**:
```
states: idle | running | paused | crashed
transitions:
  idle → running    (mlevo run)
  running → idle    (完成)
  running → crashed (异常)
  crashed → idle    (mlevo recover)
  crashed → running (mlevo recover --resume)
```

非法转换 MUST 返回非零退出码 + JSON 错误信息。

### D3: 训练参数梯度 — preset 系统

**选择**: `--preset tiny|small|full` 三档配置

| preset | sf_games | sf_visits | sh_samples | tr_epochs | pk_games | 耗时 |
|--------|----------|-----------|------------|-----------|----------|------|
| tiny   | 5        | 8         | 100        | 1         | 4        | ~30s |
| small  | 50       | 32        | 1000       | 1         | 10       | ~5m  |
| full   | 训练计划  | 训练计划   | 训练计划    | 训练计划   | 训练计划  | ~60m |

**理由**: tiny 走真实代码路径（不 mock），Agent 可频繁测试；small 用于 CI；full 用于正式训练。

### D4: 分支策略 — 锦标赛 + archive

**选择**: 分支自动命名（`branch-{date}-{param_slug}`），PK 对决决定 mainline，输家 archive

**替代方案**:
- 用户命名：增加认知负担
- 知识蒸馏合并：实现复杂，效果不确定

**理由**: 自动命名减少决策负担，锦标赛简单有效，archive 保留历史不丢失。

### D5: 边与 OpenSpec change 关联

**选择**: 每次训练关联一个 OpenSpec change，change 的 proposal 构成 DAG 的边

**理由**: 边不只是"从 A 到 B"，还记录了"为什么"——假设、参数 diff、实验意图。这使得模型图谱成为实验知识图谱。

### D6: WebUI 技术栈 — React + FastAPI + REST

**选择**: React + Vite + D3.js 前端，FastAPI 纯 REST 后端

**替代方案**:
- WebSocket 实时推送：过度设计，训练轮次长，轮询足够
- 纯静态 HTML：DAG 可视化复杂度高，需要框架支持

**理由**: D3.js 灵活渲染 DAG 图谱，FastAPI 薄壳包装 CLI，REST 简单可靠。

### D7: 崩溃恢复 — 保守策略

**选择**: 崩溃 → 标记 round 为 failed → 重跑整个 round

**替代方案**:
- 精确恢复（从 stage checkpoint 续跑）：实现复杂，partial 数据可能污染

**理由**: 训练一轮 ~60 分钟，重跑代价可接受。精确恢复作为后期优化。

### D8: 测试隔离 — 临时目录

**选择**: 测试使用 `--tmpdir` 隔离，不污染 `training_data/`

**理由**: 测试和正式训练共用同一套代码路径，但数据隔离。tiny preset 产出的模型文件小（~1MB），清理无压力。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| JSONL 注册表随模型增多变大 | 每条 ~200B，1000 条才 200MB，不是问题 |
| 历史模型占磁盘空间 | 每模型 ~35MB，100 轮 ~3.5GB，可接受 |
| CLI 状态机在进程崩溃后状态不一致 | 写操作 atomic（先写 tmp 再 rename），启动时校验 |
| WebUI 和 Agent 并发调 CLI | CLI 操作加文件锁，排队执行 |
| tiny preset 路径和 full 不完全一致 | 同一套代码，参数不同，覆盖大部分逻辑 |
| 分支多了图谱可读性差 | WebUI 支持折叠/展开分支，后期加搜索过滤 |

## Migration Plan

1. 创建 `model_registry.jsonl`，从 `evolution_ledger.json` 推导 parent 关系
2. 将 `training_data/torchmodels_toexport/` 中的模型按 hash 归档到 `models/`
3. 保留 `evolution_ledger.json` 作为只读历史，新数据写入 registry
4. CLI 新增子命令，保留旧 `mlevo_cli.py` 接口兼容一段时间
5. WebUI 最后开发，依赖 CLI 稳定

## Open Questions

- 模型 hash 算法：SHA256(model.bin.gz) 还是用 KataGomo 内置的 sample count + date hash？
- 分支合并后，输家分支的 edge 如何标记（archived/rejected）？
- WebUI 部署方式：开发时 localhost，正式训练时是否需要远程访问？
