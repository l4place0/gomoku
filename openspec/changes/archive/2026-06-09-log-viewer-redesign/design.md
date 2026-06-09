## Context

The Gomoku ML training console utilizes a FastAPI backend (`webui/app.py`) and a React-based frontend (`webui/frontend`). The logs directory contains various logs: C++ engine runtime logs (`runtime.log`) and Python pipeline log files (e.g. `round_X_selfplay.log`, `round_X_train.log`, `kata_training_backend.log`).
Currently, logs are loaded via `/api/logs` and rendered sequentially in standard textboxes, which lacks scannability and makes filtering difficult.

## Goals / Non-Goals

**Goals:**
- Implement a double-pane layout: a sidebar list of logs on the left and a terminal console view on the right.
- Enable tab-based category separation between Game Engine and Pipeline logs.
- Add advanced client-side search, log-level highlighting, date-range filtering, and round matching.
- Add an interactive Live Tail mode with auto-scroll and 3-second polling.

**Non-Goals:**
- Refactoring the FastAPI backend logic or database models. We will rely on the existing `/api/logs` API endpoint, performing line-by-line parsing and filtering client-side to keep changes self-contained.

## Decisions

- **Client-Side Parsing**:
  - *Decision*: We will perform line-by-line filtering (by keyword, level, date range) in the React component rather than requesting backend API query params.
  - *Rationale*: Keeps the backend API simple. Since `/api/logs` already limits individual files to their tail end (last 2000 characters), client-side parsing is computationally cheap and provides near-instant UI response times.
- **Double-Pane Layout**:
  - *Decision*: Sidebar for file selector, right panel for the actual log console.
  - *Rationale*: Allows users to easily switch between logs of different stages (e.g. selfplay vs training) without losing context or visual layout.
- **Terminal UI Gutter**:
  - *Decision*: Map log lines to individual divs containing a line number gutter and the text content.
  - *Rationale*: Much cleaner than a raw `<pre>` tag. It allows us to apply precise CSS styling to lines with warnings or errors and dynamically highlight search term matches.

## Risks / Trade-offs

- **[Risk] Timestamp formats vary** → The C++ engine and Python pipeline use different date patterns.
  *Mitigation*: Implement robust regex matching in the React component's date-parsing logic to support both `[YYYY-MM-DD HH:MM:SS]` and `YYYY-MM-DD HH:MM:SS+0800` formats.
- **[Risk] Live tail polling overhead** → Rapid backend calls could cause UI lag.
  *Mitigation*: Set the polling interval to 3 seconds, which is standard for web log viewers, and only run the interval when the selected tab/tail toggle is active.
