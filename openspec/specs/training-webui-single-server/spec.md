# training-webui-single-server Specification

## Purpose
TBD - created by archiving change integrate-plans-and-warnings-in-webui. Update Purpose after archive.
## Requirements
### Requirement: Single-Server Static Asset Hosting
The system SHALL serve static files (JavaScript, CSS, HTML, and assets) from the compiled frontend directory `webui/frontend/dist` directly on the FastAPI server port.

#### Scenario: Serve index.html at root
- **WHEN** the user requests `GET /`
- **THEN** the system SHALL return the content of `webui/frontend/dist/index.html`.

#### Scenario: Serve bundle assets
- **WHEN** the user requests a compiled bundle path like `GET /assets/index-*.js`
- **THEN** the system SHALL return the matching file with the correct MIME type.

### Requirement: SPA Catch-all Routing
The system SHALL return `index.html` for any unmatched non-API request, allowing React Router to handle HTML5 history routes.

#### Scenario: Direct access to /graph
- **WHEN** the user requests `GET /graph` or refreshes the page on `/plans`
- **THEN** the system SHALL return `webui/frontend/dist/index.html` with a 200 status code.

#### Scenario: Unmatched API route returns 404
- **WHEN** the user requests `GET /api/nonexistent`
- **THEN** the system SHALL return a 404 JSON error instead of index.html.

