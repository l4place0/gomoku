## ADDED Requirements

### Requirement: Source Separation
The log viewer SHALL divide the logs into two distinct categories: "Training Pipeline Logs" and "Game Engine Runtime".

#### Scenario: Switching categories shows correct log files
- **WHEN** the user selects the "Training Pipeline Logs" category tab
- **THEN** the system SHALL display files like `round_10_selfplay.log`, `round_10_train.log`, and `kata_training_backend.log` in the file sidebar list
- **WHEN** the user selects the "Game Engine Runtime" category tab
- **THEN** the system SHALL display files like `runtime.log` or `build_forbidden_check.log` in the file sidebar list

### Requirement: Advanced Filtering
The system SHALL support advanced filtering of log lines and log files.

#### Scenario: Full-text search and keyword highlighting
- **WHEN** the user inputs a search query in the search bar
- **THEN** the log viewer SHALL only display log lines containing that query and highlight the matching keyword

#### Scenario: Pipeline stage filtering
- **WHEN** the user clicks a pipeline stage pill (e.g., "SELFPLAY" or "TRAIN") under the pipeline category
- **THEN** the file sidebar SHALL only list log files matching that stage

#### Scenario: Date range filtering
- **WHEN** the user inputs start and end date boundaries
- **THEN** the log viewer SHALL only display log lines whose parsed timestamps fall within that range

### Requirement: Live Tailing
The log viewer SHALL provide a live tail mode for monitoring active training loops.

#### Scenario: Enabling tail mode polls logs and scrolls to bottom
- **WHEN** the user toggles "Enable Tail" to active
- **THEN** the system SHALL poll the logs from the backend every 3 seconds and scroll the console pane to the bottom on new log additions

### Requirement: Log Scannability and Actions
The log viewer SHALL support terminal-like scannability and quick actions.

#### Scenario: Log level line highlighting
- **WHEN** a log line contains "error", "failed", or "exception"
- **THEN** the log viewer SHALL render the line in red styling
- **WHEN** a log line contains "warn" or "warning"
- **THEN** the log viewer SHALL render the line in yellow/orange styling

#### Scenario: Copy and download actions
- **WHEN** the user clicks "Copy" or "Download" in the console header
- **THEN** the system SHALL copy the filtered lines to the clipboard or download them as a text file respectively
