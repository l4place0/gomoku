## ADDED Requirements

### Requirement: 测试分层体系
系统 SHALL 支持四层测试：单元测试（纯逻辑，<1s）、集成测试（tiny preset 真实训练，<60s）、WebUI 测试（前后端组件，<30s）、E2E 验收（full preset，用户手动触发）。Agent SHALL 能通过 `mlevo test --suite all --json` 一键执行前三层。

#### Scenario: 执行全部自动测试
- **WHEN** 用户执行 `mlevo test --suite all --json`
- **THEN** 依次执行 unit、integration、webui-api、webui-ui 测试，返回汇总报告

#### Scenario: 单独执行单元测试
- **WHEN** 用户执行 `mlevo test --suite unit --json`
- **THEN** 仅执行单元测试，返回结果

### Requirement: 单元测试覆盖
单元测试 SHALL 覆盖：model_registry（注册、hash 唯一、parent 关系、环检测）、dag_engine（拓扑排序、分支创建、无环校验）、decision_engine（参数调整、早停触发）。每个测试 SHALL 在 1 秒内完成。

#### Scenario: 模型注册表单元测试
- **WHEN** 执行 model_registry 相关单元测试
- **THEN** 验证注册、检索、过滤、环检测等所有场景

#### Scenario: DAG 引擎单元测试
- **WHEN** 执行 dag_engine 相关单元测试
- **THEN** 验证拓扑排序、分支创建、无环校验等所有场景

### Requirement: 集成测试使用真实训练
集成测试 SHALL 使用 `--preset tiny` 执行真实训练流程（不 mock），验证 selfplay→shuffle→train→export→pk 全流程。测试 SHALL 使用临时目录隔离数据。

#### Scenario: tiny 训练全流程
- **WHEN** 执行集成测试
- **THEN** 走完完整训练流程，验证模型文件生成、registry 更新、winrate 输出

#### Scenario: 测试数据隔离
- **WHEN** 集成测试执行
- **THEN** 所有训练数据写入临时目录，不污染正式 `training_data/`

### Requirement: 故障注入测试
系统 SHALL 支持 `--inject oom|nan|crash` 参数模拟训练故障。故障注入 SHALL 触发对应的错误处理路径，验证崩溃恢复机制。

#### Scenario: OOM 故障注入
- **WHEN** 执行 `mlevo run --round 1 --preset tiny --inject oom --json`
- **THEN** 模拟 OOM 错误，验证状态变为 crashed，恢复策略正确

#### Scenario: NaN 故障注入
- **WHEN** 执行 `mlevo run --round 1 --preset tiny --inject nan --json`
- **THEN** 模拟 NaN loss，验证错误捕获和恢复建议

### Requirement: WebUI 后端测试
WebUI 后端测试 SHALL 验证所有 REST API 端点的输入输出合规性。测试 SHALL 使用 tiny preset 的真实训练数据。

#### Scenario: API 状态端点测试
- **WHEN** 测试 `GET /api/status`
- **THEN** 返回 200 + 合法 JSON，包含 pipeline_state 字段

#### Scenario: API 运行端点测试
- **WHEN** 测试 `POST /api/run` 带 `{"preset": "tiny"}`
- **THEN** 返回训练结果 JSON，包含 winrate 和 promoted 字段

### Requirement: WebUI 前端测试
WebUI 前端测试 SHALL 验证 React 组件的渲染和交互。测试 SHALL 覆盖 Dashboard（状态卡片、进度条）、ModelGraph（节点渲染、点击交互）、LogViewer（日志列表、筛选）。

#### Scenario: 图谱组件渲染测试
- **WHEN** ModelGraph 组件接收到模型数据
- **THEN** 正确渲染节点数量和边数量

#### Scenario: 仪表板组件测试
- **WHEN** Dashboard 组件接收到状态数据
- **THEN** 正确显示 round、winrate、pipeline_state

### Requirement: 测试报告输出
所有测试 SHALL 输出结构化 JSON 报告，包含 passed、failed、skipped 计数和耗时。失败的测试 SHALL 包含错误详情。

#### Scenario: 测试报告格式
- **WHEN** 执行 `mlevo test --suite all --json`
- **THEN** 输出 `{"unit": {"passed": N, "failed": N, "time": "Xs"}, "integration": {...}, ...}`
