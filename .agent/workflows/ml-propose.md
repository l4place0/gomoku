---
description: Propose a new ML evolution plan - scaffolds proposal, design, tasks, and initial training_plan.json.
---

# /ml-propose

Propose a new ML evolution plan and create the scaffold plan directory.

## Action Guide

1. Prompt user for target plan details (e.g. plan name, model architecture kind, and rounds).
2. Execute the CLI command to initialize plan files:
   ```bash
   uv run python mlevo_cli.py new plan "<name>"
   ```
3. Open the newly created `training_plan.json` and present the proposal and design files to the user.
