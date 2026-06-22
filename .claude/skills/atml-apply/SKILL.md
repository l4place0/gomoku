---
name: atml-apply
description: ML Apply workflow — read training plan, auto-decide parameters, execute training round. Auto mode: only confirm on guardrail warnings.
license: MIT
compatibility: Requires mlevo_cli.py and uv toolchain.
metadata:
  author: Antigravity
  version: "3.0"
---

# 🔄 ATML Apply (v3) — Auto-Mode Training Execution

Read training plan, decide parameters, execute round. Default is auto mode — only interrupt user on guardrail warnings.

## 🏃‍♂️ Action Guide

### Step 1: Read Plan (forced)

```bash
# 1. Find the active change
ls docs/ml/changes/   # or user specifies a plan name

# 2. Read training plan
cat docs/ml/changes/<name>/training_plan.json

# 3. Read design for context
cat docs/ml/changes/<name>/design.md

# 4. Discover available parameters
mlevo automl-help --json
```

### Step 2: Decide Parameters

```bash
mlevo decide --plan <name> --json
```

Output contains: `decided_parameters`, `decision_reasons`, `guardrail_warnings`.

### Step 3: Auto/Confirm Decision

Check `guardrail_warnings`:

- **No warnings** → Auto mode: skip confirmation, proceed directly to Step 4
- **Warnings present** → Show warnings to user, ask for confirmation:
  - "guardrail 检测到以下问题：sf_games=50 低于推荐值 100。继续？"
  - User confirms → proceed
  - User adjusts → use adjusted params

### Step 4: Execute Training

```bash
mlevo run --round <N> --plan <plan> --branch <name> \
  --params '{"sf_games": 600, "sf_visits": 128, "tr_lr": 0.001, ...}' --json
```

- `--params` is JSON passthrough: underscores auto-convert to CLI dashes
- Boolean `true` → flag only (no value), `false` → omit flag
- `--preset tiny/small` for quick validation, `--params` overrides any preset value

### Step 5: Check Results

After training completes:

```bash
mlevo status --json
mlevo graph --with-edges --json
mlevo models --branch <name> --json
```

Model auto-recorded to `ml/data/model_registry.jsonl`.

### Step 6: WebUI Monitor

For long training: remind user about `http://localhost:3000` for live monitoring.

## 🔄 Multi-Round Loop

For running multiple rounds in sequence:

```
Round 1: decide → (auto) → run → check
Round 2: decide → (auto) → run → check
Round 3: decide → (warning!) → confirm → run → check
...
```

Auto mode means rounds run back-to-back without asking. Only guardrail warnings pause the loop.

## 📝 Example: Auto Mode

```bash
# Read plan
cat docs/ml/changes/v4-lr-reset/training_plan.json

# Decide
mlevo decide --plan v4-lr-reset --json
# → {"decided_parameters": {...}, "guardrail_warnings": []}
# No warnings → auto proceed

# Execute (no confirmation needed)
mlevo run --round 1 --plan v4-lr-reset --branch mainline \
  --params '{"sf_games": 800, "sf_visits": 128, "tr_lr": 0.001}' --json

# Check
mlevo status --json
mlevo models --branch mainline --json
```

## 📝 Example: Guardrail Warning

```bash
mlevo decide --plan v4-lr-reset --json
# → {"decided_parameters": {"sf_games": 50}, "guardrail_warnings": ["sf_games (50) below recommended 100"]}

# Warning present → ask user
# "sf_games=50 低于推荐值 100，继续还是调整？"
```

## 📝 Fault Injection (Testing)

```bash
# Test OOM recovery
mlevo run --round 1 --preset tiny --inject oom --json
# → {"status": "failed", "error": "OOM", "recovery": "reduce_batch"}

# Recover
mlevo recover --json
```

## 🔗 Related Commands

| Command | Purpose |
|---------|---------|
| `mlevo decide --plan <name> --json` | Compute adaptive parameters |
| `mlevo run --round N --plan <name>` | Execute training round |
| `mlevo status --json` | Pipeline state |
| `mlevo progress --json` | Training progress |
| `mlevo graph --with-edges --json` | DAG view |
| `mlevo models --branch <name> --json` | Branch models |
| `mlevo test --suite all` | Run full test suite |
| `mlevo recover --json` | Recover from crash |
