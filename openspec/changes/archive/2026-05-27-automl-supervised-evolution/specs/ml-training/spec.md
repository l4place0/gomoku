## ADDED Requirements

### Requirement: Command Line Argument Support for Configuration
The ML training scripts (such as `train.py`, `shuffle.py`, and `export_model_pytorch.py`) SHALL parse and accept explicit command-line arguments passed from the external orchestrator CLI, overriding any hardcoded default settings.

#### Scenario: CLI argument pass-through to PyTorch trainer
- **WHEN** `automl_cli.py` invokes `train.py` with custom arguments (e.g. batch size and samples per epoch)
- **THEN** `train.py` SHALL parse and use the external parameters for PyTorch model training instead of defaults.
