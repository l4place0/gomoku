## ADDED Requirements

### Requirement: Hyperparameter Sweet Spot Validation
The system SHALL compare the hyperparameter values of models and edges against the recommended ranges from `docs/ml/specs/training-knowledge.md`.

#### Scenario: Validate selfplay games count
- **WHEN** a model has `sf_games` parameter below 500
- **THEN** the system SHALL flag it as a warning.

#### Scenario: Validate learning rate threshold
- **WHEN** a model has `tr_lr` parameter below 0.0005
- **THEN** the system SHALL flag it as a critical warning due to FP16 NaN risk.

### Requirement: Warning Badges in UI
The WebUI SHALL render warning badges next to any parameter values that deviate from the recommended sweet spots.

#### Scenario: Display warning badge and tooltip
- **WHEN** a parameter has been flagged as a warning
- **THEN** the WebUI SHALL display an amber warning icon next to the value and show a hover tooltip describing the constraint recommendation.
