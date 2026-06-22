# Design: ATML Workflow v3 Refactor

## 架构决策

### 1. opsx 与 atml 职责分离

| 管辖范围 | 工具 | 文档位置 |
|----------|------|----------|
| 全代码库架构变更 | opsx (openspec CLI) | openspec/ |
| 训练层工作流 | atml (mlevo CLI) | docs/ml/ |

两者独立运行，互不依赖。atml 不调用 `openspec new change`，opsx 不关心训练参数。

### 2. 目录结构

```
docs/ml/                           ← atml 管辖
├── changes/                       ← 变更提案（替代原 openspec/changes/ 中的 atml 内容）
│   ├── <name>/                    ← 活跃变更
│   │   ├── proposal.md
│   │   ├── design.md
│   │   ├── tasks.md
│   │   └── training_plan.json
│   └── archive/                   ← 已归档变更
├── specs/
│   ├── atml-skills/spec.md        ← 技能规格（从 openspec/specs/ 迁移）
│   └── training-knowledge.md      ← 训练知识库（闭环核心）
├── plans/                         ← 运行时训练数据（保留）
└── references/                    ← 研究报告（保留）

ml/data/                           ← 运行时数据
├── model_registry.jsonl
├── logs/
└── models/
```

### 3. Explore 交互式设计

```
Phase 1: 强制采集（无交互）
  → mlevo status/graph/models
  → 读取 training-knowledge.md
  → 读取最近 N 轮日志
  → 输出 dashboard

Phase 2: 循环探索（用户驱动）
  → 用户选择方向 → Agent 执行 → 呈现结果 → 等待下一步
  → 直到用户说"够了"

Phase 3: 结构化输出
  → 覆盖写入 docs/ml/insights.json
  → 行动建议
```

### 4. 数据流闭环

```
explore → insights.json → propose → changes/<name>/ → apply → model_registry
                                                                        ↓
explore ← training-knowledge.md ← archive ← changes/archive/<date>-<name>/
```

training-knowledge.md 是闭环关键：archive 写入 → explore 强制读取 → propose 参考。

### 5. Archive 自适应路径

```
≤2 轮 + 全 VALID → 快速路径（1 Agent）
  mlevo archive + mlevo report → conclusion.md → update knowledge

>2 轮 或 INVALID → 完整路径（3 Agents）
  Collector → facts.json → Compiler → conclusion.md → Verifier → verdict
  最多 3 次 REJECT，超过后人工介入
```

### 6. Apply Auto 模式

```
mlevo decide → guardrail_warnings?
  [] → 直接执行 mlevo run（不打断用户）
  [...] → 展示警告，请求确认后执行
```

## 代码改动

### mlevo_cli.py

- 新增 `CHANGES_DIR = PROJECT_ROOT / "docs" / "ml" / "changes"`
- `PLANS_DIR` 保留为 legacy（运行时数据）
- `ARCHIVE_DIR` 改为 `CHANGES_DIR / "archive"`
- `get_plan_dir()`、`find_plan()`、`cmd_new()`、`cmd_list()`、`cmd_report()` 全部改用 CHANGES_DIR

### 测试

- `test_mlevo.py`：import CHANGES_DIR 替代 PLANS_DIR，monkeypatch 更新
