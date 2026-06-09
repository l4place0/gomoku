## 1. Style Integration

- [x] 1.1 Append redesigned CSS layout and highlight styling classes to [index.css](file:///home/l4p/gomoku/webui/frontend/src/index.css)

## 2. React Component Implementation

- [x] 2.1 Replace [LogViewer.jsx](file:///home/l4p/gomoku/webui/frontend/src/components/LogViewer.jsx) with the new double-pane layout including category tabs (Pipeline vs Engine) and a sidebar for log file selection
- [x] 2.2 Implement metadata parsing for log files in the sidebar (extracting round number and pipeline stage badges)
- [x] 2.3 Implement the filtering panel including full-text query, round number, level selection, date range inputs, and pipeline stage pills
- [x] 2.4 Implement line-by-line terminal rendering inside the console window with line numbers, error/warning visual coloring, and search match highlighting
- [x] 2.5 Implement the "Live Tail Mode" polling loop (fetching logs every 3 seconds and scrolling the console viewport to the bottom)
- [x] 2.6 Implement Copy-to-Clipboard and Download action buttons in the console header

## 3. Verification & Testing

- [x] 3.1 Verify the updated log viewer component mounts and functions correctly in the web application
- [x] 3.2 Update the frontend tests in [components.test.jsx](file:///home/l4p/gomoku/webui/frontend/src/__tests__/components.test.jsx) and run them to ensure 100% test coverage and compliance with TDD rules
