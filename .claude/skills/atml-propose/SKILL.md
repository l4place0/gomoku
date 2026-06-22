---
name: atml-propose
description: ML Propose workflow — read explore insights, create training plan and change artifacts under docs/ml/changes/.
license: MIT
compatibility: Requires mlevo_cli.py and uv toolchain.
metadata:
  author: Antigravity
  version: "3.0"
---

# 📅 ATML Propose (v3) — Single-Scaffold Plan Creation

Read explore insights, create change artifacts under `docs/ml/changes/<name>/`. One directory, no duplication.

## 🏃‍♂️ Action Guide

### Step 1: Read Context (forced)

Read the following before creating anything:

1. `docs/ml/insights.json` — explore 输出的结构化分析（如果存在）
2. `docs/ml/specs/training-knowledge.md` — 历史训练经验
3. `mlevo schema --json` — CLI 能力
4. `mlevo automl-help --json` — 可用训练参数
5. `mlevo models --json` — 当前模型状态

### Step 2: Create Change Directory

```bash
mkdir -p docs/ml/changes/<name>
```

Single directory for everything. No openspec, no duplicate scaffolds.

### Step 3: Write Artifacts

Create all files under `docs/ml/changes/<name>/`:

**proposal.md** — why this plan:
- Problem statement (from insights.json bottlenecks)
- Goal (what success looks like)
- Scope (what's included, what's not)
- Link to training-knowledge.md relevant sweet spots

**design.md** — how:
- Parameter choices and rationale (reference insights.json analysis)
- Training strategy (data amount, lr schedule, pk config)
- Risk assessment (what could go wrong)
- Code changes needed (if any)

**tasks.md** — execution steps:
- Ordered list of training rounds
- Each round: parameters, expected outcome, success criteria

**training_plan.json** — ML config:
```json
{
  "name": "<plan-name>",
  "description": "one-line summary",
  "baseline": {
    "sf_games": 600,
    "sf_visits": 128,
    "tr_lr": 0.001,
    "tr_epochs": 2,
    "pk_games": 40,
    "tr_batch": 64
  },
  "stages": [],
  "created": "<ISO-8601>",
  "insights_ref": "docs/ml/insights.json"
}
```

### Step 4: Present & Confirm

Show the user:
1. Summary of insights.json bottlenecks being addressed
2. Key parameter choices and why
3. How many rounds planned

Ask for feedback before proceeding to apply.

## 🔗 Data Flow

```
/explore                          /propose
┌──────────────┐                 ┌──────────────────────┐
│ insights.json│────────────────▶│ docs/ml/changes/<n>/ │
│ (结构化分析)  │                 │ ├── proposal.md       │
└──────────────┘                 │ ├── design.md         │
                                 │ ├── tasks.md          │
docs/ml/specs/                   │ └── training_plan.json│
training-knowledge.md───────────▶│                      │
(历史经验)                        └──────────────────────┘
```

## 📝 Example

```bash
# 1. Read context
cat docs/ml/insights.json
cat docs/ml/specs/training-knowledge.md
mlevo automl-help --json

# 2. Create change
mkdir -p docs/ml/changes/v4-lr-reset

# 3. Write artifacts
# → docs/ml/changes/v4-lr-reset/proposal.md
# → docs/ml/changes/v4-lr-reset/design.md
# → docs/ml/changes/v4-lr-reset/tasks.md
# → docs/ml/changes/v4-lr-reset/training_plan.json

# 4. Present to user for confirmation
# 5. Ready for /atml-apply
```
