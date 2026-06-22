## Why

Currently, the training WebUI lacks integration with active/archived experiment plans and safety constraints. Researchers cannot view plan-level scientific documentation (proposals, designs, conclusions) or get visual alerts when training parameters deviate from historical sweet spots (guardrails). Combining plan documentation, visual groupings, and parameter warnings directly into the lineage graph will provide a much more unified and insightful ML training console.

## What Changes

- **Plan-Based DAG Grouping**: Group model nodes in the ReactFlow evolution graph visually by their training plan boundaries (Group Nodes/swimlanes).
- **Artifact Document Viewer**: Add a Markdown rendering panel in the WebUI sidebar to view plan-level artifacts (`proposal.md`, `design.md`, `conclusion.md`) for any selected node or edge.
- **Hyperparameter Warning Badges**: Display visual warning indicators (amber/orange alerts) on the WebUI when actual hyperparameters deviate from the recommended sweet spots defined in `training-knowledge.md`.
- **Plans Catalog & Navigation**: Add an interactive "Plans" library tab in the WebUI to view all active/archived plans and jump directly to their model positions on the DAG graph.
- **Single-Server Consolidation**: Mount and serve the compiled frontend React SPA directly via the FastAPI backend, eliminating the need to run two separate servers.

## Capabilities

### New Capabilities
- `training-webui-plans`: Expose API endpoints and render a Plan Catalog page to view active/archived plans. Enable plan boundary visual groupings in the ReactFlow DAG graph.
- `training-webui-markdown`: Expose API endpoints and render a tabbed Markdown document viewer in the details panel for active/archived proposals, designs, and conclusions.
- `training-webui-warnings`: Implement automatic validation of training parameters against recommended sweet spots from `training-knowledge.md` and display warning badges next to deviating hyperparameters in the WebUI.
- `training-webui-single-server`: Serve static assets and handle React Router SPA catch-all routing inside the FastAPI backend.

### Modified Capabilities

## Impact

- **Backend (FastAPI)**:
  - Add `GET /api/changes/{plan_name}/markdown/{filename}` to read and return proposal/conclusion markdown files.
  - Integrate parameter validation checks.
  - Mount frontend build directory `webui/frontend/dist` and add catch-all routing for SPA.
- **Frontend (Vite/React)**:
  - Update `webui/frontend/src/api.js` and `webui/frontend/src/pages/Graph.jsx` to fetch and render markdown docs, visual group boundaries, and parameter warning badges.
  - Implement a new tab/page `Plans.jsx` for the plan catalog.
