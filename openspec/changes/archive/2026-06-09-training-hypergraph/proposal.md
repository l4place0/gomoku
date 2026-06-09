## Why

当前模型图谱是扁平 DAG：所有训练轮次（R1-R10）在同一层级，缺乏"计划"维度的组织。随着训练计划增多（已有 5 个计划），图谱变得混乱，无法直观看出计划之间的传承关系。

需要引入两层图谱结构：
- **内层**：单个训练计划内的轮次链（已有）
- **外层**：训练计划之间的超图关系（新增）

## What Changes

- **新增 plan_registry.jsonl**：外层超图数据结构，记录每个训练计划的元数据和传承关系
- **超边设计（方案 C）**：`from_model`（模型继承）+ `hypothesis`（设计假设）
- **WebUI 图谱改造**：支持两层可视化——外层超图 + 内层轮次链
- **CLI 新命令**：`mlevo plans` 查看计划图谱，`mlevo plan --name` 查看计划详情

## Capabilities

### New Capabilities

- `training-hypergraph`: 两层训练图谱——外层超图（计划级）+ 内层 DAG（轮次级），超边包含模型继承和设计假设

### Modified Capabilities

- `ml-training`: 模型注册表增加 plan 级元数据，WebUI 图谱支持两层可视化

## Impact

- **新增文件**: `plan_registry.jsonl`、`plan_registry.py`
- **修改文件**: `mlevo_cli.py`（新命令）、`webui/app.py`（新 API）、`webui/frontend/`（图谱改造）
- **数据兼容**: 现有 model_registry.jsonl 不变，新增 plan_registry.jsonl
