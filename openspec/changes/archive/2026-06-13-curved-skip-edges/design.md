## Context

In the inner DAG graph of `ModelGraph.jsx`, nodes are placed at coordinates defined by their round numbers and relative indices. Edges (representing training runs) are currently drawn as straight lines using `L` paths in SVG. When edges span multiple rounds (e.g. from R1 to R3, skipping R2), they overlap with other sequential edges (R1 → R2, R2 → R3) because all nodes share a vertical baseline or central y-level. This design details how to represent these skip edges as curved lines to avoid overlap, while maintaining interactivity (click and hover) and correct label positioning.

## Goals / Non-Goals

**Goals:**
- Render forward edges with a round difference greater than 1 as curved SVG quadratic bezier paths arcing above nodes.
- Make the curve height proportional to the number of skipped rounds.
- Position the parameter change labels at the midpoint along the curved paths.
- Maintain full click handlers on both straight and curved edges.
- Keep backward edges behaving correctly.
- Add hover visual styling in CSS for the interactive edges.

**Non-Goals:**
- Implementing layout or rendering changes to the outer hypergraph.
- Modifying how nodes are positioned within the rounds.

## Decisions

### 1. Edge Path Type Selection
- **Decision:** Use quadratic Bezier curves (`Q` command in SVG path `d`) for both backward edges and forward round-skipping edges. Adjacent forward edges remain straight lines (`L` command).
- **Rationale:** A quadratic Bezier curve requires only a single control point. It is mathematically simple to compute the midpoint for label positioning and produces smooth, predictable arcs.
- **Alternatives Considered:** Cubic Bezier curves (`C` command), which require two control points. This was rejected because the extra complexity is not needed to create a simple arc.

### 2. Control Point Calculations for Forward Skip Edges
- **Decision:**
  - Let $P_1 = (x_1, y_1)$ be the starting point (right edge of source node) and $P_2 = (x_2, y_2)$ be the ending point (left edge of target node).
  - Control point $C = (controlX, controlY)$ is computed as:
    - $controlX = (x_1 + x_2) / 2$
    - $controlY = \min(y_1, y_2) - (40 + \text{roundDiff} \times 25)$
  - Curve midpoint (parameter $t = 0.5$):
    - $midX = 0.25 \times x_1 + 0.5 \times controlX + 0.25 \times x_2$
    - $midY = 0.25 \times y_1 + 0.5 \times controlY + 0.25 \times y_2$
- **Rationale:** Centering the control point horizontally (`(x_1 + x_2) / 2`) makes the curve symmetrical. Offsetting `controlY` by `40 + roundDiff * 25` guarantees that higher round differences scale the curve height higher, and subtracting from `min(y_1, y_2)` guarantees it arcs upwards and clears any intermediate node cards.

### 3. Click Interactivity and Hover highlight
- **Decision:** Keep the invisible wider helper path (`stroke-width: 12`, `stroke: transparent`) stacked behind the visible edge path. Register click handlers on the wrapping group (`<g>`). Add a CSS hover rule for the group selector `g:hover .graph-edge:not(.selected)` to highlight the visible edge when the user hovers anywhere on the group (including the wider click target).
- **Rationale:** This ensures clicking the curve is user-friendly and doesn't require pixel-perfect alignment. Group-level hovering ensures the hover visual feedback triggers reliably.

## Risks / Trade-offs

- **[Risk]** Overly high curves might clip the top boundary of the SVG viewport.
  - **Mitigation:** The SVG has dynamic width and height bounds. If needed, we can tweak the height coefficient (`25` pixels per round) to ensure curves fit within the `height = 500` viewport.
