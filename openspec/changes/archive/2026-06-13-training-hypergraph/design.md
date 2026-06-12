## Context

当前模型图谱是扁平 DAG（model_registry.jsonl），所有轮次在同一层级。随着训练计划增多，需要引入两层结构：外层超图（计划级）+ 内层 DAG（轮次级）。

## Goals / Non-Goals

**Goals:**
- 外层超图记录计划之间的传承关系（模型继承 + 设计假设）
- 内层 DAG 保持不变（轮次级模型关系）
- WebUI 支持两层可视化
- CLI 支持计划级查询

**Non-Goals:**
- 不引入复杂的超图框架（用两层 DAG 模拟）
- 不自动推断计划关系（手动或半自动标注）
- 不改变现有 model_registry.jsonl 结构

## Decisions

### D1: 数据结构——plan_registry.jsonl

```json
{
  "plan": "v3-anti-overfit",
  "best_model": "a9648e349aad",
  "best_winrate": 0.57,
  "rounds_completed": 1,
  "rounds_total": 5,
  "from_plan": "v1-gtx1650ti",
  "from_model": "ac884021b92a",
  "hypothesis": "反过拟合：epochs=1, lr=0.001",
  "model_kind": "b10c128",
  "timestamp": "2026-06-07",
  "status": "active"
}
```

### D2: 超边设计（方案 C）

超边包含两个属性：
- `from_model`：从哪个模型继承（可自动追踪）
- `hypothesis`：设计假设（从 OpenSpec proposal 提取）

### D3: WebUI 两层可视化

```
外层视图（默认）：
  节点 = 训练计划（显示 best_model, best_winrate）
  边 = 超边（from_model + hypothesis）
  点击节点 → 展开内层视图

内层视图（展开后）：
  节点 = 训练轮次（已有）
  边 = 训练参数（已有）
```

### D4: CLI 新命令

- `mlevo plans --json`：列出所有训练计划
- `mlevo plan --name <name> --json`：查看计划详情（含内层图谱）

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| plan_registry.jsonl 需要手动维护 | 初期手动，后期自动化 |
| 两层可视化增加前端复杂度 | 先做简单版本，逐步优化 |
| 现有数据迁移 | 不迁移，新计划才录入 |
