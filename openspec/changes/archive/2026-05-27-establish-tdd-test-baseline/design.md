## Context

当前五子棋博弈项目在功能迭代时缺乏保障性的测试框架（Harness）。为了防止新改动（如多进程双模型自对弈、参数交换等）引入回归缺陷或棋力退化，需要建立一套“SDD -> 编写 spec 验证点 -> TDD 编写对应测试”的闭环流程。

本设计旨在以**最小改动原 OpenSpec 工作流**为前提，建立 pytest 测试框架作为 Harness，并对项目现有代码（如 `game.py`）进行小范围重构以提升可测试性。

## Goals / Non-Goals

**Goals:**
- 引入 `AGENTS.md` 注入 AI 开发纪律，强制 TDD 流程。
- 配置以 `pytest` 为核心的测试基础设施（`pyproject.toml`、`tests/conftest.py`）。
- 对 `game.py` 纯逻辑函数进行解耦，提取至 `game_logic.py`。
- 实现三层验证体系（Tier 1 Python 单元测试、Tier 2 C++ DLL 集成测试、Tier 3 手动验证 SOP）。
- 确保测试套件能在本地通过一键命令行自动执行。

**Non-Goals:**
- 修改 `openspec/config.yaml` 或原有的 CLI 工作流。
- 为所有的 Pygame 渲染或复杂的神经网络训练实现完全自动化的端到端 GUI 测试。

## Decisions

### 1. 开发约束引入：AGENTS.md
- **决策**：在项目根目录新建 `AGENTS.md` 来放开发纪律规范，而不是去修改 OpenSpec schema。
- **合理性**：这是对 AI Agent 的最直接约束。在 AI 进行任何 change 时都会主动读取此类约束文档，不需要污染 Spec。
- **规则**：“所有开发和重构必须先写 spec（SDD），接着编写对应的 pytest 单元/集成测试（TDD），并保证在 archive 之前通过所有自动化测试。”

### 2. 纯逻辑函数提取：`game_logic.py`
- **决策**：把 `is_symmetric`、`choose_low_impact_candidates_for_black` 等纯 Python 逻辑函数从 `game.py` 提取到新文件 `game_logic.py`。
- **合理性**：直接 `import game` 会触发 `pygame.init()` 及依赖，在 headless 自动化测试环境中往往会由于没有显示设备（NO_DISPLAY）或未初始化而报错。提取为纯 Python 文件可以完全脱离 Pygame 界面，极其易于进行高效的单元测试。
- **替代方案**：通过 Mock `pygame` 和 DLL。但 Mock 的维护成本极高且容易引入假阳性，剥离出纯函数是最健壮、优雅的架构演进。

### 3. 三层测试模型 (Tier 1 / Tier 2 / Tier 3)
- **决策**：
  - **Tier 1 (单元测试)**：使用 pytest 对 `game_logic.py` 里的纯函数进行测试。
  - **Tier 2 (集成测试)**：通过 Python 加载 `GameEngineDLL.dll`，测试下子、禁手检测（三三禁手、四四禁手、长连禁手）等核心功能，验证 C++ 与 Python 的绑定和交互。
  - **Tier 3 (手动验证 SOP)**：对于必须依赖图形设备或特殊 CUDA 环境的用例（如完整 GUI 自对弈、模型权重比拼），编写结构化的 Markdown SOP 指南。

## Risks / Trade-offs

- **[Risk] DLL 加载平台兼容性** → 编译生成的 `GameEngineDLL.dll` 在某些系统上需要正确的 MSVC 运行时，或者在非 Windows 系统上无法运行。
  - **Mitigation**：在 `tests/conftest.py` 中进行防御性导入，如果加载 DLL 失败，跳过 Tier 2 集成测试，或者引导开发者编译对应平台的动态库，并使用 pytest 标记标记集成测试，如 `@pytest.mark.integration`。
- **[Risk] 重构 `game.py` 影响现有 UI** → 将函数移至 `game_logic.py` 可能会漏掉某些调用处导致报错。
  - **Mitigation**：在 `game.py` 中从 `game_logic.py` 导入这些函数，保持原有的变量名与接口行为完全一致，确保后向兼容性。
