## ADDED Requirements

### Requirement: TDD Development Constraint
为了防止无测试或未通过测试的代码合入，AI MUST 严格遵守 SDD-TDD 开发规范，在所有新代码或重构代码中应用测试驱动开发。

#### Scenario: Agent checks AGENTS.md rule
- **WHEN** AI Agent begins any code modifications or creates new capabilities
- **THEN** AI Agent SHALL read `AGENTS.md` and comply with the rule that requires writing pytest-based unit/integration tests and passing existing test suites before archiving.

### Requirement: Code logic separation for testability
系统中的纯游戏逻辑与算法函数 SHALL 能够不依赖 Pygame GUI 窗口初始化与 C++ DLL 即被测试。

#### Scenario: Extract pure functions from game.py
- **WHEN** pure logic functions like `is_symmetric` and `choose_low_impact_candidates_for_black` are called by the game loop or tests
- **THEN** they SHALL be imported and executed from a standalone module `game_logic.py` without initializing a Pygame video device.

### Requirement: Automatic verification via pytest
项目中的 Python 纯函数、DLL 接口绑定以及博弈引擎核心逻辑 SHALL 支持自动化测试。

#### Scenario: Running unit and integration tests
- **WHEN** the command `pytest` is executed in the repository root directory
- **THEN** pytest SHALL discover all tests under the `tests/` directory, load configuration from `pyproject.toml`, run all unit/integration tests, and output passing results without manual intervention.

### Requirement: Standard Operating Procedure for manual verification
对于因硬件依赖或界面交互导致无法完全自动化的部分（如神经网络加载、GUI 渲染渲染和人工自对弈测试），系统 SHALL 包含可执行的手动验证 SOP 以确保稳定性。

#### Scenario: Execute manual verification steps
- **WHEN** verify actions require Pygame rendering or neural network CUDA execution that cannot be automated in headless environments
- **THEN** the developer SHALL follow the step-by-step Standard Operating Procedure (SOP) outlined in the test documentation to complete verification.
