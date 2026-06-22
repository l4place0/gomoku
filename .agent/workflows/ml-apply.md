---
description: Apply a round of ML training - run adaptive decision engine, get user confirmation, and run training.
---

# /ml-apply

Execute the next scheduled training round of an active plan.

## Action Guide

1. Run the Adaptive Decision Engine to calculate next round's parameters:
   ```bash
   uv run python mlevo_cli.py decide
   ```
2. Present the suggested parameters, the decision explanation (such as plateaus, failed promotions, or recovery), and any guardrail warnings.
3. Prompt the user for manual parameter edits or approval.
4. Execute training using `mlevo run`:
   ```bash
   uv run python mlevo_cli.py run --round <N>
   ```
