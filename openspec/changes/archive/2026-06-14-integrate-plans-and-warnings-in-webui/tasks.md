## 1. Backend REST API Endpoints

- [x] 1.1 Implement `GET /api/changes/{plan_name}/markdown/{filename}` in `ml/webui/app.py` to fetch proposal/design/conclusion markdown.
- [x] 1.2 Verify markdown retrieval endpoint responses and path security rules.

## 2. Plans Catalog Page

- [x] 2.1 Add navigation route for Plans page in `webui/frontend/src/App.jsx`.
- [x] 2.2 Implement `webui/frontend/src/pages/Plans.jsx` list view displaying plan names, status, hypothesis, and rounds completed.
- [x] 2.3 Add a "Locate in Graph" button to focus and pan the lineage graph to the plan's initial model.

## 3. Plan Bounding Boxes in DAG Lineage Graph

- [x] 3.1 Modify node data preparation in `webui/frontend/src/pages/Graph.jsx` to assign parent group IDs based on plan names.
- [x] 3.2 Implement ReactFlow nested group nodes to represent plan boundaries.
- [x] 3.3 Style plan group bounding boxes with distinct colored borders and background translucent fills.

## 4. Sidebar Markdown Document Viewer

- [x] 4.1 Implement a tabbed details layout in the side cards in `Graph.jsx` (Parameters vs. Documentation).
- [x] 4.2 Fetch markdown files via the REST API when a node or edge is selected.
- [x] 4.3 Style the rendered markdown text with dark-theme consistent styling.

## 5. Hyperparameter Sweet Spot Warning Badges

- [x] 5.1 Add hyperparameter sweet spot threshold constraints based on `training-knowledge.md` to frontend constants.
- [x] 5.2 Implement a parameter validator utility to flag parameter values that violate safety rules.
- [x] 5.3 Render an amber warning badge and helper tooltip next to flagged values in the Model Details and Edge Details cards.

## 6. Verification and Test Execution

- [x] 6.1 Add backend API test cases for the markdown files endpoint in `tests/test_webui_api.py`.
- [x] 6.2 Execute the full test suite via `mlevo test --suite all` and ensure everything passes.

## 7. Single-Server SPA serving via FastAPI

- [x] 7.1 Import FileResponse and implement serve_spa catch-all route in `ml/webui/app.py`.
- [x] 7.2 Verify direct navigation and page refreshes (e.g. /graph, /plans) on the unified port.

