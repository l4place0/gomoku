---
name: atml-explore
description: ML Explore stance — interactive exploration of training state, model performance, and bottlenecks. Reads from docs/ml/ and ml/data/.
license: MIT
compatibility: Requires mlevo_cli.py and uv toolchain.
metadata:
  author: Antigravity
  version: "3.0"
---

# 🔍 ATML Explore (v3) — Interactive Exploration

Interactive exploration of training state. Three phases: auto-collect → interactive drill-down → summarize.

## 🧭 The Stance

- **Analytical**: Parse model registry, DAG, training logs. Analyze convergence and overfitting.
- **Resource-Aware**: GTX 1650Ti constraints (4GB VRAM) — evaluate parameter feasibility.
- **Interactive**: Present overview, then let the user direct the investigation.
- **Grounded**: Every claim must come from data. No vague impressions.

## 📂 Data Sources (must read from these, not invent)

| Source | Path | Type |
|--------|------|------|
| Model registry | `ml/data/model_registry.jsonl` | JSONL, one model per line |
| DAG engine | via `mlevo graph --with-edges --json` | CLI output |
| Training logs | `ml/data/logs/round_*_train.log` | Raw text |
| PK logs | `ml/data/logs/round_*_pk.log` | Raw text |
| Evolution ledger | `ml/data/logs/evolution_ledger.json` | JSON |
| Pipeline state | `ml/data/logs/pipeline_state.json` | JSON |
| Training knowledge | `docs/ml/specs/training-knowledge.md` | Markdown |
| Active plans | `docs/ml/plans/*/training_plan.json` | JSON |
| Research refs | `docs/ml/references/*.md` | Markdown |

## 🏃‍♂️ Action Guide

### Phase 1: Auto-Collect (forced, no interaction)

Execute ALL of the following before entering Phase 2. Do not skip any.

```bash
# 1. Pipeline state
mlevo status --json

# 2. Full DAG
mlevo graph --with-edges --json

# 3. All models
mlevo models --json

# 4. Training knowledge (read file directly)
# → docs/ml/specs/training-knowledge.md

# 5. Recent logs (read last 3 rounds directly)
# → ml/data/logs/round_{N}_train.log
# → ml/data/logs/round_{N}_pk.log

# 6. Active plan config (if exists)
# → docs/ml/plans/*/training_plan.json
```

After collecting, generate a **dashboard overview** for the user:

```
=== ATML Explore Dashboard ===
Pipeline: idle | Plan: v3-anti-overfit | Round: 7
Models: 12 total, 5 promoted, 7 failed
Best: ac884021b92a (winrate 0.72)
LR trend: 0.002 → 0.0004 (decaying)
Consecutive failures: 2
Plateau detected: yes (3 rounds, loss diff < 0.05)
===============================
```

### Phase 2: Interactive Exploration (loop)

After presenting the dashboard, wait for the user. Do NOT auto-proceed.

The user may:
- **"深入模型 X"** → `mlevo history --model <hash> --json` + read related logs
- **"对比分支 A 和 B"** → `mlevo models --branch A --json` + `mlevo models --branch B --json`
- **"看第 N 轮日志"** → read `ml/data/logs/round_N_train.log` directly
- **"为什么 loss 爆炸"** → read train log, search for NaN/OOM patterns, check training-knowledge.md
- **"lr 为什么这么低"** → `mlevo lr-history --json` + read DecisionEngine strategy
- **"training-knowledge 里怎么说"** → read `docs/ml/specs/training-knowledge.md`
- **"假设 lr 太低了"** → verify by checking loss trend, compare with knowledge base sweet spots
- Free-form question → use available data to investigate

Each user request → execute relevant commands → present results → wait for next request.

Loop until user says they're done (e.g. "够了", "进入 propose", "就这样").

**Available tools in Phase 2:**

CLI commands:
| Command | When to use |
|---------|-------------|
| `mlevo graph --with-edges --json` | DAG overview |
| `mlevo models --branch <name> --json` | Filter by branch |
| `mlevo models --min-winrate <N> --json` | Filter by winrate |
| `mlevo models --promoted True --json` | Only promoted models |
| `mlevo history --model <hash> --json` | Model ancestry chain |
| `mlevo lr-history --json` | LR evolution over rounds |
| `mlevo show-strategy --json` | Current DecisionEngine strategy |
| `mlevo status --json` | Pipeline state |
| `mlevo progress --json` | Training progress |

Direct file reads:
| File | When to use |
|------|-------------|
| `docs/ml/specs/training-knowledge.md` | Historical insights |
| `docs/ml/plans/*/training_plan.json` | Plan configuration |
| `ml/data/logs/round_*_train.log` | Loss curves, errors |
| `ml/data/logs/round_*_pk.log` | PK results, IPC failures |
| `ml/data/model_registry.jsonl` | Raw model records |

### Phase 3: Summarize & Output

When the user signals exploration is complete:

1. Update `docs/ml/insights.json` (overwrite):

```json
{
  "timestamp": "<ISO-8601>",
  "source": "docs/ml/ + ml/data/",
  "dashboard": {
    "pipeline_state": "idle",
    "current_plan": "v3-anti-overfit",
    "current_round": 7,
    "total_models": 12,
    "promoted": 5,
    "failed": 7,
    "best_model": "ac884021b92a",
    "best_winrate": 0.72
  },
  "analysis": {
    "convergence": "plateau | improving | diverging",
    "overfitting_risk": "low | medium | high",
    "lr_trend": "stable | decaying | recovering",
    "consecutive_failures": 0,
    "plateau_rounds": 0
  },
  "bottlenecks": [
    {
      "type": "lr_plateau | pk_failure | overfitting | oom | nan",
      "description": "specific description with numbers",
      "severity": "low | medium | high",
      "evidence": "round N: loss diff = 0.02, lr = 0.0004",
      "suggested_action": "concrete action"
    }
  ],
  "exploration_notes": "user's key observations from Phase 2",
  "recommendations": [
    "actionable recommendation 1",
    "actionable recommendation 2"
  ]
}
```

2. Output action suggestion:
   - If bottlenecks found: "建议进入 `/atml-propose` 创建新计划解决上述问题"
   - If all good: "当前训练状态健康，可继续执行 `/atml-apply` 跑下一轮"
   - If user had specific question: answer it directly

## 📝 Example Session

```
User: /atml-explore

Agent: [Phase 1 — auto-collecting...]
  → mlevo status --json → idle, plan=v3, round=7
  → mlevo graph --with-edges --json → 12 models, 3 branches
  → mlevo models --json → 5 promoted, 7 failed
  → read training-knowledge.md → 4 sweet spots, 3 guardrails
  → read round 5-7 logs → loss plateau detected

Agent: [Dashboard]
  === ATML Explore Dashboard ===
  Pipeline: idle | Plan: v3-anti-overfit | Round: 7
  Models: 12 total, 5 promoted, 7 failed
  Best: ac884021b92a (winrate 0.72)
  LR trend: 0.002 → 0.0004 (decaying)
  Consecutive failures: 2
  Plateau: yes (rounds 5-7, loss diff < 0.03)
  ===============================

  探索方向？
  a) 深入看最近失败的 2 轮
  b) 对比 mainline 和 exp-lr 分支
  c) 查看 lr 衰减历史
  d) 你的问题

User: c

Agent: [mlevo lr-history --json]
  Round 1: lr=0.002 (baseline)
  Round 2: lr=0.002 (promoted, locked)
  Round 3: lr=0.001 (plateau decay)
  Round 4: lr=0.001 (promoted, locked)
  Round 5: lr=0.0005 (plateau decay)
  Round 6: lr=0.00035 (failure decay)
  Round 7: lr=0.00025 (failure decay)

  LR 从 0.002 衰减了 8x，已接近 lr_floor (0.0001)。
  training-knowledge.md sweet spot #2 建议 lr 不低于 0.0005。

User: 那 lr 是不是太低了？

Agent: 确认。当前 lr=0.00025 低于 training-knowledge 中的历史最佳区间 [0.0005, 0.002]。
  连续 2 轮失败 + plateau 触发了双重衰减。建议重置 lr 到 0.001 附近重新探索。

User: 好，够了，进入 propose

Agent: [Phase 3 — writing insights.json]
  → docs/ml/insights.json 已更新
  建议进入 `/atml-propose`，重点关注：
  1. 重置 lr 到 0.001
  2. 增加 sf_games 到 800 提升数据多样性
```
