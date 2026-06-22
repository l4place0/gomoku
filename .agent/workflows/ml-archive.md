---
description: Archive a completed ML evolution plan - compile metrics, snap ledger, and save persistent knowledge.
---

# /ml-archive

Finalize and archive a completed ML evolution plan.

## Action Guide

1. Invoke the CLI command to move the plan directory to archives and compile conclusions:
   ```bash
   uv run python mlevo_cli.py archive "<name>"
   ```
2. Present `conclusion.md` containing round success rates, win rates, and parameter metrics to the user.
3. Update `docs/ml/specs/training-knowledge.md` to persist the learned optimal hyperparameters.
