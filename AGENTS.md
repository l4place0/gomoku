# AI Coding Agent Instructions & Discipline

> [!IMPORTANT]
> **CRITICAL RULE**: All AI agents participating in this codebase's development and refactoring MUST strictly adhere to the following **SDD-TDD Harness** discipline. No code changes shall be archived without passing this quality check.

## 1. SDD (Spec-Driven Development) Requirement
- Before making any code modifications, agents **MUST** ensure an OpenSpec change is proposed and all spec requirements/scenarios are clearly outlined in the active `specs/` files.
- Each requirement must have concrete, verifiable `WHEN/THEN` scenarios.

## 2. TDD (Test-Driven Development) Discipline
- For every new feature or logic change:
  - **First**, write or update the corresponding automated test(s) under the `tests/` directory (using the `pytest` framework).
  - **Second**, implement/refactor the minimal code necessary to make the tests pass.
- All code files containing pure calculations, utilities, or standalone logic **MUST** have high test coverage (>90%).
- Do not mix pure functions with GUI window initialization or dynamic library loader code, to keep them easily mockable and testable in headless environments.
- **Environment Management**: Agents **MUST** use `uv` toolchain to run python code, execute tests, and manage dependencies (e.g. use `uv run pytest` instead of plain `pytest`).

## 3. Exit Verification Criteria
- Before running `/opsx-archive` or finalizing any change, the agent **MUST**:
  1. Run `pytest` locally and verify that **100% of all unit and integration tests pass**.
  2. If the change includes UI rendering, GPU usage, or deep self-play logic that cannot be fully automated, follow the corresponding **Manual Verification SOP** in `tests/README.md` and log manual confirmation.
