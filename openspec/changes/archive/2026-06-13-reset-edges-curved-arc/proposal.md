## Why

In the Gomoku training console, model rounds that failed sometimes inherit the parent of the last promoted model. When rendering this as an edge in the inner DAG graph, it creates backward edges (e.g., from a higher round R7 to a lower round R1). Currently, these edges are drawn as straight lines, causing severe visual overlapping with forward edges. We need to distinguish and properly render these "reset" edges.

## What Changes

- Detect backward/reset edges in the ModelGraph where `from.round > to.round`.
- Render backward edges with a curved arc that goes above or below the node layout to prevent visual overlapping with forward edges.
- Style backward edges with distinct styling (e.g., dashed stroke, different color/opacity) to signify that they represent resets or rollbacks.
- Update global CSS for these styled elements.

## Capabilities

### New Capabilities

*(None)*

### Modified Capabilities

- `training-webui`: Model evolution graph view is updated to detect backward edges, render them as curved arcs, and style them differently.

## Impact

- `webui/frontend/src/components/ModelGraph.jsx`: SVG path calculation and styling will be modified.
- `webui/frontend/src/index.css`: Added CSS styles for backward/reset edges.
