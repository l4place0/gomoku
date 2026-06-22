## Why

Currently, the Gomoku ML training console's log viewer is a basic component that dumps all log files together without categorization. This makes searching, filtering, and real-time troubleshooting difficult and slow during active selfplay/training cycles. Redesigning this view will separate C++ game engine logs from Python training pipeline logs, implement advanced multi-criteria filtering, highlight errors/warnings, and enable a live "tail" mode to facilitate real-time monitoring.

## What Changes

- **Source-based Categorization**: Add main navigation tabs separating Game Engine Runtime logs (C++) and Training Pipeline logs (Python).
- **Advanced Filters Row**: Add inputs for full-text search, specific round number, log level (INFO/WARN/ERROR), and date range constraints.
- **Pipeline Stage Selector**: For pipeline logs, add clickable pills to quickly filter by selfplay, shuffle, train, export, or PK.
- **Double-Pane layout**: Introduce a sidebar on the left for file listing and a console pane on the right for log viewing.
- **Terminal Scannability**: Add a line-number gutter, support line wrapping options, and visually highlight warn/error levels.
- **Live Tail Mode**: Implement a self-refreshing tailing loop (every 3 seconds) with auto-scroll to the bottom of the log viewer.
- **Action buttons**: Enable Copy-to-Clipboard and Download actions for the loaded log file.

## Capabilities

### New Capabilities
- `advanced-log-viewer`: Adds a separate, modern, split-pane log console WebUI component that supports category filtering, stage selection, date range filtering, search term highlighting, and live tail mode.

### Modified Capabilities
<!-- None -->

## Impact

- WebUI Frontend: Replaces the current implementation in [LogViewer.jsx](file:///home/l4p/gomoku/webui/frontend/src/components/LogViewer.jsx).
- Stylesheet: Appends custom CSS classes to [index.css](file:///home/l4p/gomoku/webui/frontend/src/index.css) to support double-pane grids, live terminal layout, and color highlights.
