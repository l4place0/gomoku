## 1. Model Registry 基础

- [x] 1.1 创建 `model_registry.py`：定义 ModelRecord 数据类（hash, parent, round, branch, winrate, promoted, params, change, hypothesis, timestamp, file）
- [x] 1.2 实现 JSONL 读写：`append_record()`、`read_all()`、`find_by_hash()`、`find_by_branch()`
- [x] 1.3 实现 parent 关系校验：环检测（DFS 遍历祖先链）
- [x] 1.4 实现模型 hash 计算：SHA256 前 12 位 hex
- [x] 1.5 实现模型归档：`archive_model(src, hash)` 复制到 `models/{hash}.bin.gz`
- [x] 1.6 编写 model_registry 单元测试

## 2. DAG Engine

- [x] 2.1 创建 `dag_engine.py`：基于 model_registry 构建 DAG 图结构
- [x] 2.2 实现拓扑排序：返回按依赖顺序排列的模型列表
- [x] 2.3 实现分支创建：自动命名（`branch-{YYYYMMDD}-{param_slug}`）、校验 fork_from 存在
- [x] 2.4 实现边管理：创建边（关联 OpenSpec change）、查询边信息
- [x] 2.5 实现图谱导出：`export_graph()` 返回 nodes + edges JSON
- [x] 2.6 编写 dag_engine 单元测试

## 3. CLI 状态机重构

- [x] 3.1 重构 `mlevo_cli.py` 为子命令架构：argparse 子命令入口（status, run, branch, merge, pk, graph, models, model, migrate, recover, test, schema）
- [x] 3.2 实现 `mlevo schema --json`：输出所有子命令列表和参数描述
- [x] 3.3 实现 `mlevo status --json`：输出 pipeline_state、current_round、current_model
- [x] 3.4 实现状态机：状态文件持久化（`logs/pipeline_state.json`）、转换校验、非法转换拒绝
- [x] 3.5 实现 `mlevo progress --json`：读取训练进度（stage, pct, eta）
- [x] 3.6 实现 `mlevo recover --json`：崩溃恢复（保守策略：标记 failed → 重跑）
- [x] 3.7 实现全局 `--json` 输出：所有子命令统一 JSON 输出格式，错误时 exit code 非 0
- [x] 3.8 编写 CLI 状态机集成测试

## 4. Preset 参数系统

- [x] 4.1 定义 preset 配置：tiny/small/full 三档参数（sf_games, sf_visits, sh_samples, tr_epochs, pk_games）
- [x] 4.2 修改 `automl_cli.py`：支持 preset 参数覆盖训练计划
- [x] 4.3 实现 `mlevo run --preset tiny`：30 秒内完成全流程
- [x] 4.4 编写 preset 集成测试：验证 tiny 走完真实训练流程

## 5. 分支训练与合并

- [x] 5.1 实现 `mlevo branch --from {hash}`：创建分支、写入 registry
- [x] 5.2 实现 `mlevo run --branch {name}`：在指定分支上训练
- [x] 5.3 实现 `mlevo pk --branch-a --branch-b --games N`：PK 对决
- [x] 5.4 实现 `mlevo merge --winner {branch}`：合并到 mainline，archive 输家
- [x] 5.5 实现 `mlevo models --json`：按 branch/promoted/winrate 过滤
- [x] 5.6 实现 `mlevo model --hash {hash} --json`：单模型详情
- [x] 5.7 实现 `mlevo history --model {hash} --json`：祖先链追溯
- [x] 5.8 编写分支训练集成测试

## 6. 历史数据迁移

- [x] 6.1 实现 `mlevo migrate --from-ledger --json`：从 evolution_ledger.json 推导 parent 关系
- [x] 6.2 实现模型文件扫描和归档：将 torchmodels_toexport/ 中的模型按 hash 归档
- [x] 6.3 保留 evolution_ledger.json 为只读历史
- [x] 6.4 编写迁移测试：验证 10 轮数据迁移后图谱正确

## 7. 故障注入

- [x] 7.1 实现 `--inject oom`：模拟 OOM 错误
- [x] 7.2 实现 `--inject nan`：模拟 NaN loss
- [x] 7.3 实现 `--inject crash`：模拟进程崩溃
- [x] 7.4 编写故障注入测试：验证每种故障的恢复路径

## 8. WebUI 后端

- [x] 8.1 创建 `webui/` 目录结构：FastAPI 应用骨架
- [x] 8.2 实现 `GET /api/status`：调用 `mlevo status --json`
- [x] 8.3 实现 `GET /api/progress`：调用 `mlevo progress --json`
- [x] 8.4 实现 `GET /api/graph`：调用 `mlevo graph --with-edges --json`
- [x] 8.5 实现 `GET /api/models` 和 `GET /api/models/{hash}`
- [x] 8.6 实现 `POST /api/run`、`POST /api/branch`、`POST /api/merge`
- [x] 8.7 实现日志 API：读取 logs/ 目录，按 round/level 筛选
- [x] 8.8 编写 WebUI 后端 API 测试

## 9. WebUI 前端

- [x] 9.1 创建 React + Vite 项目骨架
- [x] 9.2 实现 Dashboard 组件：状态卡片、进度条、最近结果
- [x] 9.3 实现 ModelGraph 组件：D3.js DAG 渲染、节点/边交互
- [x] 9.4 实现 LogViewer 组件：日志列表、按 round/level 筛选
- [x] 9.5 实现 BranchManager 组件：分支列表、创建分支、发起 PK
- [x] 9.6 实现 API 调用层：fetch 封装、错误处理、轮询
- [x] 9.7 编写前端组件测试

## 10. 测试框架整合

- [x] 10.1 实现 `mlevo test --suite unit`：运行所有单元测试
- [x] 10.2 实现 `mlevo test --suite integration`：运行集成测试（tiny preset）
- [x] 10.3 实现 `mlevo test --suite webui-api`：运行 WebUI 后端测试
- [x] 10.4 实现 `mlevo test --suite webui-ui`：运行前端测试
- [x] 10.5 实现 `mlevo test --suite all`：全量测试 + 汇总报告 JSON
- [x] 10.6 实现 `mlevo test --inject all`：故障注入测试
