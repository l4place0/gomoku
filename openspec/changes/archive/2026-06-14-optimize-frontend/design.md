## Context

The Gomoku ML training console frontend provides status, logs, models, and graph visualization. However, the current visual implementation is basic and lacks interactivity and refined styling. This design aims to revamp the WebUI styling and components to create a premium, cohesive, and modern user experience.

## Goals / Non-Goals

**Goals:**
- Implement a modern glassmorphic dark mode design system in `index.css` and `App.css`.
- Enhance the Dashboard page with a "Recent PK Result" card showing winrate, branch, result status, and base model hash.
- Enhance the Graph page with an overlapping prevention placement algorithm, smooth Bezier curves, and edge animation when a node is selected.
- Enhance the Models page with a responsive SVG Winrate Bar Chart highlighting the 55% threshold and interactive model status indicators.
- Enhance the Logs page with filter options, search functionality, and terminal styling.
- Ensure 100% responsive styling for standard mobile, tablet, and desktop viewports.

**Non-Goals:**
- Rewriting backend functionality (keep API endpoints identical).
- Introducing TailwindCSS or other CSS-in-JS libraries (sticking to Vanilla CSS).

## Decisions

### 1. Unified Glassmorphic Theme & CSS Variable System
- **Choice**: Modern dark mode with cohesive HSL-based tailored variables, translucent backgrounds, backdrop-blur, and subtle glow borders.
- **Rationale**: Elevates the user experience from a utility layout to a premium-feeling application.

### 2. Custom SVG Charting in Models View
- **Choice**: Handcrafted SVG Bar Chart component built directly with React and standard SVG elements rather than adding heavy chart libraries (like Chart.js or Recharts).
- **Rationale**: High customization, light footprint, and no external dependency version conflicts with React 19.

### 3. Smart DAG Node Spacing in ReactFlow
- **Choice**: Multi-layer layout mapping where node positions are calculated using horizontal layer indices based on the model's round, vertical branch offsets, and a collision resolver that shifts overlapping nodes.
- **Rationale**: Maintains clear mainline and branch structure while guaranteeing no overlapping nodes, even with concurrent training runs.

## Risks / Trade-offs

- **[Risk] High Node Count in Graph** → **[Mitigation]** The coordinate calculation uses grid-based bins to resolve overlaps, and ReactFlow's zoom/pan features naturally handle large DAGs.
- **[Risk] React 19 Compatibility** → **[Mitigation]** Standardizing on ReactFlow 11.x which works well with Vite and React 19, avoiding non-standard React components.
