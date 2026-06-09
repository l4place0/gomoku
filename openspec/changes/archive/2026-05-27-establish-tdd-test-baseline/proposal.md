## Why

为了后续开发的稳定性，我们需要为本项目建立一套完整的测试框架作为 AI Harness。该框架将以 SDD (Spec-Driven Development) 为入口，以 TDD (Test-Driven Development) 为出口。这确保了后续所有的开发都会在这个测试框架内进行，并通过自动化测试与标准化手动验证 SOP 来保证代码的正确性和项目的健壮性，同时确保不破坏现有的 OpenSpec 工作流。

## What Changes

- **开发约束与流程规范**：
  - 在项目根目录下新增 `AGENTS.md` 约束文件，加入开发纪律：**“所有新功能的开发和旧功能的重构，必须通过 SDD 编写 spec，且必须通过 TDD 编写单元测试或集成测试，严禁无测试代码合入”**。这能以最小的改动约束 AI Agent，不污染原有的 OpenSpec 流程。
- **测试基础设施**：
  - 配置 `pytest` 作为核心测试框架，引入 `pyproject.toml` 作为项目和测试的统一配置文件。
  - 新建 `tests/` 目录存放所有测试代码，并在 `tests/conftest.py` 中配置全局的 `fixture` 和环境变量。
- **现有代码测试基线（Tier 1 & Tier 2 & Tier 3）**：
  - **Tier 1 (单元测试)**：针对纯 Python 逻辑函数（不依赖 Pygame GUI 和 DLL）编写完整的高覆盖率单元测试。
  - **Tier 2 (集成测试)**：编写用于验证 C++ DLL 接口绑定、核心博弈逻辑（下子、禁手检测、输赢判断）的集成测试。
  - **Tier 3 (手动验证 SOP)**：由于 GUI 渲染和 GPU 神经网络涉及硬件依赖，对于无法完全自动化的部分，由 AI 生成标准操作程序（SOP）指导手动验证。
- **代码可测试性微重构**：
  - 将 `game.py` 中的纯逻辑函数（例如：对称性检测 `is_symmetric`、黑棋低影响候选点选择 `choose_low_impact_candidates_for_black` 等）提取到独立的 `game_logic.py` 模块中。这样测试这些纯逻辑时无需初始化 Pygame 窗口或加载 C++ DLL，避免引发 GUI 环境依赖问题。

## Capabilities

### New Capabilities

- `tdd-harness`: 建立测试框架和开发流程闭环，提供完整的单元测试、集成测试以及手动 SOP 指南，为后续的 AI 自动迭代提供绝对的安全护栏。

### Modified Capabilities

<!-- No modified capabilities of requirements -->

## Impact

- **受影响的代码文件**：
  - `game.py`：提取纯逻辑函数至 `game_logic.py`，保持原有功能不受影响，只改变导入或调用关系。
- **新增配置文件与目录**：
  - `AGENTS.md`：新增 AI 纪律约束文件。
  - `pyproject.toml`：新增项目及 pytest 配置文件。
  - `tests/` 目录：包含 `conftest.py`、`test_game_logic.py`、`test_dll_integration.py` 等。
  - `openspec/specs/tdd-harness/` 目录：用于存放本 Change 对应的功能规范文件。
