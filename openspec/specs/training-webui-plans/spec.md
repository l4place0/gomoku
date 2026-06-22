# training-webui-plans Specification

## Purpose
TBD - created by archiving change integrate-plans-and-warnings-in-webui. Update Purpose after archive.
## Requirements
### Requirement: Plans Catalog API
The system SHALL expose a GET REST endpoint `/api/plans` that returns all active and archived training plans with their name, status, scientific hypothesis, total rounds, and completed rounds.

#### Scenario: Fetching all plans
- **WHEN** the WebUI requests `GET /api/plans`
- **THEN** the backend SHALL retrieve active plan configurations from `docs/ml/plans/` and archived plans from `docs/ml/changes/archive/` and return them in JSON format.

### Requirement: Plans Catalog Page
The WebUI SHALL provide a page rendering a catalog of all plans, displaying their metadata, and containing an option to locate them in the DAG lineage graph.

#### Scenario: Clicking locate in graph
- **WHEN** the user clicks the locate button on a plan in the catalog
- **THEN** the WebUI SHALL redirect the user to the lineage graph view and focus the graph viewport on the initial model node of that plan.

### Requirement: Plan Boundary Bounding Boxes
The WebUI DAG graph page SHALL render visible boundary grouping boxes around all model nodes belonging to the same training plan.

#### Scenario: Rendering lineage graph with plan groupings
- **WHEN** the graph page is loaded and data is fetched
- **THEN** the system SHALL compute bounding boxes around nodes sharing the same `plan_name` and display colored boundaries with the plan name as the header.

