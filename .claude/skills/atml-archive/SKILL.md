---
name: atml-archive
description: ML Archive workflow — fast path for simple plans, full 3-agent pipeline for complex ones. Archives to docs/ml/changes/archive/.
license: MIT
compatibility: Requires mlevo_cli.py and uv toolchain.
metadata:
  author: Antigravity
  version: "4.0"
---

# 🗃️ ATML Archive (v4) — Adaptive Archival

Two paths based on complexity. Archives to `docs/ml/changes/archive/`.

## Path Selection

```
                    ┌─────────────────────┐
                    │  How many rounds?    │
                    │  Any INVALID PKs?    │
                    └──────┬──────────────┘
                           │
                ┌──────────┴──────────┐
                │                     │
           ≤2 rounds              >2 rounds
           all VALID              or INVALID
                │                     │
                ▼                     ▼
        ┌──────────────┐     ┌──────────────┐
        │  Fast Path    │     │  Full Pipeline│
        │  (1 Agent)    │     │  (3 Agents)   │
        └──────────────┘     └──────────────┘
```

## Fast Path (simple plans)

For plans with ≤2 rounds AND all PK verdicts VALID:

### Step 1: Archive & Report

```bash
mlevo archive "<plan-name>"
mlevo report "<plan-name>" --json > facts.json
```

### Step 2: Write Conclusion

Based on facts.json, write `conclusion.md` in the archived plan directory.

**Rules:**
- Every number must come from facts.json
- No vague statements — exact percentages required
- Per-round template:

```markdown
### Round N
- 自博弈: [completed_games] / [planned_games]
- 训练: vloss=[值], pacc1=[值], p0loss=[值]
- PK: [completed_games] 局, [胜]-[负]-[平]
- PK 有效性: VALID
- Ledger 一致性: [MATCH | MISMATCH]
```

### Step 3: Update Knowledge

Update `docs/ml/specs/training-knowledge.md` with new insights.

### Step 4: Archive Change

```bash
# Move to archive with date prefix
mv docs/ml/changes/<name> docs/ml/changes/archive/$(date +%Y-%m-%d)-<name>
```

Done. No Verifier needed for simple plans.

## Full Pipeline (complex plans)

For plans with >2 rounds OR any INVALID PK verdicts:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Collector   │────▶│  Compiler   │────▶│  Verifier   │
│  (mlevo report)│     │  (write conclusion)│     │  (cross-check)│
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                          ┌────┴────┐
                                          │         │
                                        PASS     REJECT (max 3)
                                          │         │
                                          ▼         ▼
                                        Done     Human escalation
```

### Step 1: Archive & Collect

```bash
mlevo archive "<plan-name>"
mlevo report "<plan-name>" --json
```

Save output as `facts.json` in the archived directory. This is the authoritative source.

### Step 2: Compiler — Write conclusion.md

Based on `facts.json`, write `conclusion.md`.

**Hard rules:**
- Every number MUST come from facts.json
- No vague statements ("胜率偏低" → write exact percentage)
- INVALID PK verdicts MUST state the reason
- Anomalies from facts.json MUST appear in conclusion

**Per-round template:**
```markdown
### Round N
- 自博弈: [completed_games] / [planned_games]
- 训练: vloss=[值], pacc1=[值], p0loss=[值]
- PK: [completed_games] 局, [胜]-[负]-[平]
- PK 有效性: [VALID | INVALID — 原因] | [DEGRADED — 原因]
- Ledger 一致性: [MATCH | MISMATCH — 差异]
```

### Step 3: Verifier — Cross-check

Read original log files directly (NOT facts.json). Verify:

1. Every number in conclusion.md matches raw log value
2. No vague statements exist
3. All anomalies from logs are mentioned
4. PK verdicts match actual log state
5. Ledger consistency correctly reported

**Output — verdict.json:**
```json
{
  "verdict": "PASS | REJECT",
  "retries": N,
  "issues": [
    {
      "field": "R1 PK",
      "conclusion_says": "0/100 (0%)",
      "actual": "0/0 crash result, 19 games completed",
      "severity": "CRITICAL"
    }
  ]
}
```

### Step 4: Handle Verdict

- **PASS** → proceed to Step 5
- **REJECT** → pass verdict.json back to Compiler, loop to Step 3
- **After 3 REJECTs** → stop, output all verdict history, wait for human

### Step 5: Update Knowledge

Read `conclusion.md`, update `docs/ml/specs/training-knowledge.md` with new insights.

### Step 6: Archive Change

```bash
mv docs/ml/changes/<name> docs/ml/changes/archive/$(date +%Y-%m-%d)-<name>
```

## 🔗 Data Flow

```
/atml-apply                        /atml-archive
┌──────────────┐                  ┌──────────────────────────┐
│ model_registry│                  │ Fast:                    │
│ .jsonl        │                  │   mlevo archive + report │
│ (new model)   │                  │   → conclusion.md        │
└──────────────┘                  │   → update knowledge     │
                                  │                          │
                                  │ Full:                    │
                                  │   Collector → facts.json │
                                  │   Compiler → conclusion  │
                                  │   Verifier → verdict     │
                                  │   → update knowledge     │
                                  └──────────┬───────────────┘
                                             │
                                             ▼
                                  docs/ml/changes/archive/
                                  <date>-<name>/
                                  ├── proposal.md
                                  ├── design.md
                                  ├── tasks.md
                                  ├── training_plan.json
                                  ├── facts.json
                                  └── conclusion.md

                                  docs/ml/specs/
                                  training-knowledge.md ← updated
                                             │
                                             ▼
                                     next /atml-explore reads it
```

## 🔗 Related Commands

| Command | Purpose |
|---------|---------|
| `mlevo archive <name>` | Archive plan directory |
| `mlevo report <name> --json` | Extract structured facts from logs |
| `mlevo list` | List active and archived plans |
| `mlevo models --json` | Model registry |
| `mlevo graph --json` | DAG |
