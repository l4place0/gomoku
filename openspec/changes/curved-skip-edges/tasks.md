## 1. Implement Curved Edges in ModelGraph

- [x] 1.1 Modify `ModelGraph.jsx` edge rendering logic to distinguish between backward edges, forward adjacent edges, and forward round-skipping edges.
- [x] 1.2 Implement SVG quadratic bezier curves (Q command) for forward round-skipping edges (`|to.round - from.round| > 1`), with height proportional to the number of skipped rounds.
- [x] 1.3 Update midpoint calculation for placing edge labels on forward round-skipping edges using the quadratic bezier curve formula.
- [x] 1.4 Verify that backward edges continue to work correctly and use their existing quadratic bezier curve rendering.

## 2. Style and Interactivity Polish

- [x] 2.1 Update `index.css` to add selector-based hover highlight for `.graph-edge:not(.selected)` on group hover, ensuring the hover highlight triggers when hovering over the wider invisible path.
- [x] 2.2 Verify that the click handler triggers correctly on both straight and curved edges.
- [x] 2.3 Run the vitest test suite to ensure all frontend unit tests continue to pass.
