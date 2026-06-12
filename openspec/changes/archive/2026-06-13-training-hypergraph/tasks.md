## 1. 计划注册表

- [x] 1.1 创建 `plan_registry.py`：定义 PlanRecord 数据类
- [x] 1.2 实现 JSONL 读写：append、read_all、find_by_name、update
- [x] 1.3 实现 CLI 命令 `mlevo plans --json`
- [x] 1.4 实现 CLI 命令 `mlevo plan --name <name> --json`（含内层图谱）

## 2. 数据迁移

- [x] 2.1 从现有训练计划创建初始 plan_registry.jsonl
- [x] 2.2 从 model_registry.jsonl 推导计划间传承关系

## 3. WebUI 改造

- [x] 3.1 新增 API `GET /api/plans` 和 `GET /api/plans/{name}`
- [x] 3.2 改造 ModelGraph 组件：外层超图渲染
- [x] 3.3 实现点击展开：外层节点 → 内层 DAG
- [x] 3.4 超边渲染：显示 from_model 和 hypothesis

## 4. 验证

- [x] 4.1 运行 `mlevo test --suite unit` 确认基础逻辑
- [x] 4.2 运行 `mlevo test --suite webui-api` 确认 API
- [x] 4.3 前端组件测试
