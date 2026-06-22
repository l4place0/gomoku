## ADDED Requirements

### Requirement: Supplement promotion decision with Elo confidence interval
When Elo data is available, `evaluate_promotion()` SHALL use Elo difference and confidence interval as a supplementary signal alongside the existing winrate threshold.

#### Scenario: Elo CI supports promotion
- **WHEN** winrate >= 0.55 AND Elo diff > 0 AND CI lower bound > 0
- **THEN** promotion is recommended with high confidence

#### Scenario: Elo CI contradicts winrate
- **WHEN** winrate >= 0.55 BUT Elo diff CI includes 0 (uncertain)
- **THEN** promotion is still allowed (winrate is primary) but a warning is logged

#### Scenario: No Elo data available
- **WHEN** no elo_history.jsonl exists or candidate has no prior comparisons
- **THEN** the existing winrate-only logic applies unchanged

### Requirement: Include Elo metrics in PK output
The PK result JSON SHALL include Elo-related fields when elo_history data is available.

#### Scenario: PK output with Elo data
- **WHEN** PK completes and Elo has been computed
- **THEN** the output JSON includes: elo_diff (float), ci_lower (float), ci_upper (float), elo_decision (string: "strong_likely"/"weak_likely"/"uncertain")

#### Scenario: PK output without Elo data
- **WHEN** PK completes but no Elo history exists
- **THEN** the output JSON omits Elo fields (backward compatible)

### Requirement: Store Elo in evolution ledger
The evolution_ledger.json entry for each round SHALL include Elo metrics when available.

#### Scenario: Ledger entry with Elo
- **WHEN** a round completes with Elo computation
- **THEN** the ledger entry's pk section includes: elo_diff, ci_lower, ci_upper

### Requirement: Robust regression detection using Elo
The system SHALL provide Elo-based regression detection that is more robust than raw winrate trends for small sample sizes.

#### Scenario: Elo-based sudden drop detection
- **WHEN** a model's Elo drops by more than 50 points compared to its parent
- **THEN** a high-severity regression is flagged

#### Scenario: Elo trend decline detection
- **WHEN** Elo decreases over 3+ consecutive rounds (not just winrate)
- **THEN** a medium-severity trend decline is flagged
