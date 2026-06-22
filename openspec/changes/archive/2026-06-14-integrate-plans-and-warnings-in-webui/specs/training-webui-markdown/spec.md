## ADDED Requirements

### Requirement: Markdown Retrieval API
The system SHALL expose a GET REST endpoint `/api/changes/{plan_name}/markdown/{filename}` to read and serve markdown files.

#### Scenario: Retrieval of active proposal
- **WHEN** the WebUI requests `GET /api/changes/test-plan/markdown/proposal.md`
- **THEN** the backend SHALL check if `docs/ml/changes/test-plan/proposal.md` exists and return its content as plain text.

#### Scenario: Retrieval of archived conclusion
- **WHEN** the WebUI requests `GET /api/changes/test-plan/markdown/conclusion.md`
- **THEN** the backend SHALL search for `docs/ml/changes/archive/*-test-plan/conclusion.md`, read it, and return its content as plain text.

### Requirement: Tabbed Markdown Document Viewer
The WebUI details sidebar SHALL contain a tabbed interface allowing users to view the proposal, design, and conclusion markdown files.

#### Scenario: Clicking the documentation tab on a node or edge
- **WHEN** the user selects a node or edge in the graph and clicks the "Documentation" tab in the sidebar
- **THEN** the WebUI SHALL fetch the corresponding plan's markdown documents and render them in place.
