## Why

经过数周开发，根目录堆积了 20+ Python 文件、C++ 源码、编译产物、17MB 字体文件、临时 JSON 报告，三个不同系统（游戏引擎、ML 训练、Web 控制台）的代码平铺在同一层级，缺乏组织。同时 `GameEngine.so` 被 `.gitignore` 忽略但仍被 git track，存在仓库体积膨胀问题。需要按系统职责重组目录结构，建立清晰边界，方便后续独立开发和维护。

## What Changes

- **创建 `game/` 包**：将游戏引擎相关 Python 文件（`game.py`、`game_logic.py`、`game_logger.py`、`model_weights.txt`、开局库数据、字体资源）移入
- **创建 `ml/` 包**：将 ML 训练管线文件（`automl_cli.py`、`mlevo_cli.py`、`training_ui.py`、`dag_engine.py`、`model_registry.py`、`plan_registry.py`、`run_training_loop.py`、开局库工具、模型/训练数据目录）移入，`webui/` 并入为其前端子目录
- **创建 `tools/` 包**：将跨系统公共引擎绑定（`ai_worker.py`、`headless_runner.py`）移入
- **创建 `engine/` 目录**：将 C++ 源码（`GameEngineDLL.*`、`KataInferenceAdapter.*`、`KataSelfplayMain.cpp`、`GameEngine.h`）和构建文件（`CMakeLists.txt`、`build.bat`、`build.sh`）移入
- **清理根目录临时文件**：删除 `headless_verify_report*.json`、`test_eval.json`、`cli_eval_test.json`、根目录 `training_plan.json` 副本
- **修复 `.gitignore`**：取消 track `GameEngine.so`，补充忽略规则（`__pycache__`、`logs/`、`*.jsonl`、`training_data/`、字体文件等）
- **更新所有 import 路径和文件路径引用**：Python import、subprocess 调用路径、ctypes DLL 加载路径、CMakeLists.txt 源文件路径
- **重组测试目录**：按系统分为 `tests/game/` 和 `tests/ml/`，更新 import
- **更新 `pyproject.toml`**：调整 `pythonpath` 配置

## Capabilities

### New Capabilities
- `workspace-structure`: 定义目录组织规范、包结构、跨系统依赖边界
- `path-safety-tests`: 重组前的安全网测试套件，覆盖模块可达性、文件存在性、子进程调用、C++ 构建路径

### Modified Capabilities
- `test-framework`: 测试目录结构变更为按系统分组，import 路径全部更新

## Impact

- **所有 Python 文件的 import 路径**：从 `from xxx import` 变为 `from game.xxx import` / `from ml.xxx import` / `from tools.xxx import`
- **CMakeLists.txt**：C++ 源文件路径从 `./` 变为 `engine/src/`
- **subprocess 调用**：`webui/app.py`、`automl_cli.py`、`training_ui.py` 中的 CLI 路径引用
- **ctypes DLL 加载**：`ai_worker.py`、`headless_runner.py`、`test_dll_integration.py` 中的 `GameEngine.so` 路径
- **KataGomo 配置路径**：`game.py`、`headless_runner.py` 中引用 KataGomo 配置的路径
- **git history**：大量文件移动，`GameEngine.so` 从 repo 中移除
