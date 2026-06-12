## 1. CSS Styling

- [x] 1.1 Add `.graph-edge.reset` with dashed lines and custom color/opacity styling in `index.css`.

## 2. Core Implementation

- [x] 2.1 Update edge coordinates detection in `ModelGraph.jsx` to switch source/target sides for backward edges (`from.round > to.round`).
- [x] 2.2 Replace `<line>` elements with `<path>` elements using quadratic bezier coordinates for curved backward edges (and straight paths for forward edges) in `ModelGraph.jsx`.
- [x] 2.3 Apply the `.reset` class to backward edges in `ModelGraph.jsx`.

## 3. Verification

- [x] 3.1 Run frontend unit tests with `npm test` and verify that all tests pass.
