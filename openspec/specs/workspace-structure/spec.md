## ADDED Requirements

### Requirement: 四包目录结构
项目 SHALL 按系统职责分为四个 Python 包：`game/`（游戏引擎 GUI + 游戏逻辑）、`ml/`（ML 训练管线 + Web 控制台）、`tools/`（跨系统公共引擎绑定）、`engine/`（C++ 源码 + 构建）。每个包 SHALL 包含 `__init__.py`。

#### Scenario: 包目录存在且可导入
- **WHEN** 项目重组完成
- **THEN** `game/`、`ml/`、`tools/` 目录存在，各自包含 `__init__.py`，可通过 `import game`、`import ml`、`import tools` 正常导入

#### Scenario: engine 目录包含 C++ 源码
- **WHEN** 项目重组完成
- **THEN** `engine/src/` 包含 `GameEngine.h`、`GameEngineDLL.cpp`、`GameEngineDLL.h`、`KataInferenceAdapter.cpp`、`KataInferenceAdapter.h`、`KataSelfplayMain.cpp`，`engine/` 包含 `CMakeLists.txt`、`build.bat`、`build.sh`

### Requirement: 游戏包内容完整
`game/` 包 SHALL 包含：`game.py`、`game_logic.py`、`game_logger.py`、`model_weights.txt`、`assets/LXGWZhenKaiGB-Regular.ttf`、`data/opening_book.json`、`data/opening_seeds.json`、`data/select_opening.py`。

#### Scenario: 游戏包文件齐全
- **WHEN** 项目重组完成
- **THEN** `game/` 目录下存在上述所有文件，根目录不再存在这些文件

### Requirement: ML 包内容完整
`ml/` 包 SHALL 包含：`automl_cli.py`、`mlevo_cli.py`、`training_ui.py`、`dag_engine.py`、`model_registry.py`、`plan_registry.py`、`run_training_loop.py`、`populate_opening_book.py`、`verify_opening_book.py`、`verify_symmetry.py`、`training_ui_state.json`、`webui/`、`data/`（含 `model_registry.jsonl`、`plan_registry.jsonl`、`models/`、`training_data/`、`logs/`）。

#### Scenario: ML 包文件齐全
- **WHEN** 项目重组完成
- **THEN** `ml/` 目录下存在上述所有文件和子目录，根目录不再存在这些文件

### Requirement: tools 包内容完整
`tools/` 包 SHALL 包含：`ai_worker.py`、`headless_runner.py`。

#### Scenario: tools 包文件齐全
- **WHEN** 项目重组完成
- **THEN** `tools/` 目录下存在上述文件，根目录不再存在这些文件

### Requirement: 根目录整洁
根目录 SHALL 仅保留：`game/`、`ml/`、`tools/`、`engine/`、`KataGomo/`、`tests/`、`docs/`、`openspec/`、`pyproject.toml`、`uv.lock`、`.gitignore`、`.gitmodules`、`AGENTS.md`、`README.md`。根目录 SHALL NOT 包含任何 `.py` 源文件（除测试入口外）、`.cpp`/`.h` 文件、临时 JSON 报告、编译产物。

#### Scenario: 根目录无散落源码
- **WHEN** 项目重组完成
- **THEN** 根目录不存在 `.py`、`.cpp`、`.h` 文件（除 `pyproject.toml` 外）

#### Scenario: 根目录无临时产物
- **WHEN** 项目重组完成
- **THEN** 根目录不存在 `headless_verify_report*.json`、`test_eval.json`、`cli_eval_test.json`、`search_logs.jsonl`、`training_plan.json`

### Requirement: KataGomo submodule 位置不变
`KataGomo/` SHALL 保留在根目录作为 git submodule，不移动到任何子包中。

#### Scenario: KataGomo 位置不变
- **WHEN** 项目重组完成
- **THEN** `KataGomo/` 仍在根目录，`.gitmodules` 配置正确

### Requirement: 路径引用正确性
所有 Python 文件中的文件路径引用 SHALL 基于各自的包根目录（`Path(__file__).resolve().parent`），KataGomo 路径 SHALL 通过 `parent.parent / "KataGomo"` 引用。

#### Scenario: game.py 路径正确
- **WHEN** 执行 `python game/game.py`
- **THEN** 能正确加载 `game/model_weights.txt`、`game/assets/LXGWZhenKaiGB-Regular.ttf`、`KataGomo/models/model.bin.gz`

#### Scenario: automl_cli.py 路径正确
- **WHEN** 执行 `python ml/automl_cli.py --help`
- **THEN** 能正确找到 KataGomo 训练脚本路径
