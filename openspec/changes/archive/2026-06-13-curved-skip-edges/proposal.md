## Why

In the inner DAG graph of the ModelGraph component, when edges skip rounds (e.g. A → B → C and A → C), all edges are currently drawn as straight lines on the same y-level. This causes the overlapping A → C edge to visually merge with A → B and B → C, obscuring the graph structure and making it confusing to read. Drawing these skip edges as curved arcs that clear intermediate nodes will clarify the DAG hierarchy and prevent overlapping.

## What Changes

- Modify `ModelGraph.jsx` to render forward edges that skip rounds (i.e. `|to.round - from.round| > 1`) as curved SVG quadratic bezier curves (Q command) arcing above the nodes.
- Make the curve height proportional to the number of skipped rounds.
- Keep adjacent edges (round diff = 1) as straight lines.
- Ensure edge labels are correctly positioned along the curved edges.
- Keep click handlers functioning on the curved edges.
- Ensure backward edges continue to function.
- Update CSS styling to support hover highlighting and selection on curved edges.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `training-webui`: Update DAG graph requirements to specify that edges skipping one or more rounds must be rendered as curved paths arcing above nodes, with proportional height, maintaining click interactivity and label positioning.

## Impact

- `ModelGraph.jsx`: Layout logic for edges.
- `index.css`: Edge styling, hover/selection specificity.
- Vitest tests: Frontend tests should remain passing.
