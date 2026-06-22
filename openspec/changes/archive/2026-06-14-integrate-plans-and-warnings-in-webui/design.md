## Context

The Gomoku training console is a Vite/React application served via a FastAPI backend. While it visualizes model versions (DAG graph) and training progress, it currently lacks visual integration of experiment plans (`training_plan.json`), artifact text documents (`proposal.md`, `conclusion.md`), and safety constraints (`training-knowledge.md`). This document outlines the technical design to unify these elements into the WebUI.

## Goals / Non-Goals

**Goals:**
- **Markdown Document Rendering**: Serve and render the markdown files (`proposal.md`, `design.md`, `conclusion.md`, `tasks.md`) in a sidebar/tabbed details view when a node or edge is selected in the lineage graph.
- **Plan Visual Boundary Groupings**: Group models in the ReactFlow DAG graph by plan using visually distinct lanes or bounding boxes.
- **Plans Catalog & Search**: Fetch active/archived plans from the backend and display them in a dedicated "Plans" page with search/filter features and a "jump to graph position" locator.
- **Hyperparameter Sweet Spot Warnings**: Validate actual model/edge parameters against guardrails defined in `training-knowledge.md` and display warning badges next to any anomalies.

**Non-Goals:**
- **Write Actions from UI**: Allowing users to edit, create, or archive plans directly from the WebUI frontend (will remain read-only to avoid concurrent write lock complexity).

## Decisions

### D1: Markdown Artifact Retrieval Endpoint
- **Decision**: Add a REST endpoint `GET /api/changes/{plan_name}/markdown/{filename}` in the FastAPI backend (`ml/webui/app.py`).
- **Alternatives Considered**: 
  1. *Reading files via frontend directly*: Rejected because the browser frontend cannot access local host files outside its origin sandbox due to CORS/security rules.
- **Rationale**: The FastAPI backend runs on the host system and has full access to the project directory. It can search both `docs/ml/changes/<plan_name>/` (active) and `docs/ml/changes/archive/<date>-<plan_name>/` (archived) to locate the requested file and return it as plain text.

### D2: Bounding Box Plan Groupings in ReactFlow
- **Decision**: Leverage ReactFlow's nested node hierarchy (Parent/Child nodes) to render a transparent, colored group boundary around all nodes sharing the same `plan_name`.
- **Alternatives Considered**:
  1. *Custom SVG overlay canvas*: Rejected due to high complexity and math needed to sync zoom/pan events manually.
- **Rationale**: ReactFlow natively supports Group Nodes. By nesting model nodes under a parent group node representing the plan, ReactFlow handles dragging, panning, zooming, and z-indexing out-of-the-box.

### D3: Client-Side Hyperparameter Alert Engine
- **Decision**: Implement the parameter threshold rules directly in the React frontend codebase.
- **Rationale**: Avoids database/backend logic bloat. The model parameters are already returned in the `mlevo graph` node/edge data. The frontend can compare them against a hardcoded constant object representing the `training-knowledge.md` sweet spots:
  ```js
  const CONSTRAINT_SWEET_SPOTS = {
    sf_games: { min: 100, recommended: 500 },
    pk_games: { min: 20 },
    tr_lr: { min: 0.0005 },
    sh_samples: { min: 50000, recommended: 150000 },
    tr_batch: { min: 16 }
  };
  ```
  If a value is violated, the frontend shows an inline warning icon and warning tooltip.

### D4: Single-Server SPA serving via FastAPI
- **Decision**: Serve frontend built assets directly from FastAPI backend.
- **Rationale**: Keeps deployment lightweight. Instead of needing both a Vite dev server and a FastAPI server running, the compiled frontend code in `webui/frontend/dist` is hosted directly on port 3000.
  - To support SPA HTML5 path routing in React Router (e.g. `/graph`, `/plans`), implement a catch-all route `serve_spa` that returns the main `index.html` file when files are not found on disk, while preserving 404 for unmatched `/api` calls.

## Risks / Trade-offs

- **[Risk] Markdown Styling Inconsistencies** → *Mitigation*: Render markdown inside a dedicated CSS container with styling for headers, pre/code blocks, and lists configured to fit the existing console dark theme.
- **[Risk] Multi-node layout overlap inside Plan Groups** → *Mitigation*: Ensure the layout generator script (`Graph.jsx` coordinate stacker) computes offsets that take the plan bounding-box paddings into account.
- **[Risk] SPA path refreshes return 404** → *Mitigation*: The catch-all wildcard endpoint in FastAPI serves the compiled `index.html` for all non-API and missing paths, letting client-side React Router resolve the route.

