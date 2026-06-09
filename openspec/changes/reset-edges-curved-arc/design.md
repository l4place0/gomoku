## Context

In the Gomoku training console, failed rounds sometimes inherit from a parent of the last promoted model, creating backward edges in the model lineage graph. When rendered, these edges are drawn as straight lines, overlapping directly with the forward edges in the mainline path. This makes the graph difficult to read and visually unappealing.

## Goals / Non-Goals

**Goals:**
- Detect backward/reset edges (where `from.round > to.round`).
- Render these edges as curved paths arcing above or below the node layout.
- Use a distinct styling (e.g. dashed lines, distinct color) for reset/backward edges.
- Ensure the arrow/marker points in the correct direction (leftwards/into the target node) and aligns with the curve tangent.
- Keep the click target for details functional on curved paths.

**Non-Goals:**
- Modifying the layout or alignment of nodes.
- Changing the backend APIs.

## Decisions

### 1. Edge Coordinates and Direction
For forward edges:
- Source: Right side of source node (`from.x + nodeWidth / 2 + 4`)
- Target: Left side of target node (`to.x - nodeWidth / 2 - 10`)

For backward/reset edges (`from.round > to.round`):
- Source: Left side of source node (`from.x - nodeWidth / 2 - 4`)
- Target: Right side of target node (`to.x + nodeWidth / 2 + 10`)

This avoids drawing the line through the source or target nodes.

### 2. Curved Path Geometry
We will render backward edges as SVG quadratic bezier curves:
`M x1 y1 Q controlX controlY x2 y2`
- `controlX = (x1 + x2) / 2`
- `controlY = Math.min(y1, y2) - yOffset` (arcing upwards above the nodes)
- `yOffset = 80 + (from.round - to.round) * 15` (offset grows with distance to prevent overlap between multiple backward edges).

For forward edges, we will keep the standard straight line rendering (or `<path>` with straight line command `d="M x1 y1 L x2 y2"` for code uniformity).

### 3. Styling
We will define a new CSS class `.graph-edge.reset` in `index.css`:
- Use `stroke-dasharray: 4,4` (or similar) to make it dashed.
- Use a distinct color (e.g., a warm orange or muted red/yellow accent like `rgba(240, 140, 0, 0.4)` or using CSS variables if available, e.g., `var(--status-failed)` or `var(--text-secondary)`). Let's use `var(--status-failed)` or a custom dashed style.
- We will define a corresponding arrowhead marker if needed, or reuse the default. Since the edge is styled as reset, maybe a custom marker color or just reusing the existing marker is fine.

## Risks / Trade-offs

- **Risk:** Curved line selection target is harder to click.
- **Mitigation:** Update the invisible thick click-target line to use the exact same path geometry as the visible curve.
