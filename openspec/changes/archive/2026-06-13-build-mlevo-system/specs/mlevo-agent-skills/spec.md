## ADDED Requirements

### Requirement: ML Explore Workflow (/ml-explore Command)
The Agent MUST support the `/ml-explore` workflow.
The workflow SHALL invoke the `mlevo-explore` skill, which guides the Agent in analyzing existing models, ledger history (`logs/evolution_ledger.json`), and research reports to identify performance bottlenecks and propose directions for the next plan.

#### Scenario: Running ML explore command
- **WHEN** user types `/ml-explore`
- **THEN** Agent analyzes logs and generates a summary of historical model performance with recommendations for next parameters

### Requirement: ML Propose Workflow (/ml-propose Command)
The Agent MUST support the `/ml-propose` workflow.
The workflow SHALL invoke the `mlevo-propose` skill to initialize a new evolution plan.
The Agent SHALL scaffold `proposal.md`, `design.md`, and an initial draft of `training_plan.json` under `docs/ml/plans/<plan-name>/` based on user-supplied goals.

#### Scenario: Running ML propose command
- **WHEN** user types `/ml-propose "high-visits-plan"`
- **THEN** Agent scaffolds `docs/ml/plans/high-visits-plan/` with proposal, design, and draft training plan

### Requirement: ML Apply Workflow (/ml-apply Command)
The Agent MUST support the `/ml-apply` workflow.
The workflow SHALL invoke the `mlevo-apply` skill to execute a round of an active plan.
The Agent SHALL first run `mlevo decide` to calculate the next round's parameters, present the computed parameters and the decision log to the user for feedback, incorporate any user adjustments, and then trigger the training process via `mlevo run`.

#### Scenario: Running ML apply command for a round
- **WHEN** user types `/ml-apply` to start next round
- **THEN** Agent runs `mlevo decide`, displays the parameters and warnings, prompts user for adjustments, and executes the training round upon approval

### Requirement: ML Archive Workflow (/ml-archive Command)
The Agent MUST support the `/ml-archive` workflow.
The workflow SHALL invoke the `mlevo-archive` skill to finalize a completed plan.
The Agent SHALL execute `mlevo archive`, summarize the key training insights in `conclusion.md`, and update `docs/ml/specs/training-knowledge.md` to persist the learned hyperparameter bounds and rules.

#### Scenario: Running ML archive command
- **WHEN** user types `/ml-archive`
- **THEN** Agent moves plan directory to archive, creates a snapshot ledger, and updates `docs/ml/specs/training-knowledge.md` with final winrate and parameters
