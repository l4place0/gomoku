## 1. 安全网测试（Phase 0）

- [x] 1.1 创建 `tests/test_path_safety.py`，编写模块可达性测试：验证 `game.game_logic`、`game.game_logger`、`ml.model_registry`、`ml.plan_registry`、`ml.dag_engine`、`ml.automl_cli`、`ml.mlevo_cli`、`tools.ai_worker` 可被 import
- [x] 1.2 在 `test_path_safety.py` 中编写文件存在性测试：验证 `game/model_weights.txt`、`game/assets/LXGWZhenKaiGB-Regular.ttf`、`game/data/opening_book.json`、`KataGomo/models/model.bin.gz`、`engine/src/GameEngineDLL.cpp`、`engine/CMakeLists.txt` 存在
- [x] 1.3 在 `test_path_safety.py` 中编写子进程调用测试：验证 `ml/mlevo_cli.py --help` 和 `ml/automl_cli.py --help` 可被 subprocess 正常调用
- [x] 1.4 运行安全网测试，确认当前状态（所有测试应 SKIP 或 PASS，记录基线）

## 2. 清理临时文件 + 修复 .gitignore（Phase 1）

- [x] 2.1 删除根目录临时产物：`headless_verify_report.json`、`headless_verify_report_fixed.json`、`headless_verify_report_perfect.json`、`test_eval.json`、`cli_eval_test.json`、`training_plan.json`
- [x] 2.2 更新 `.gitignore`：补充 `__pycache__/`、`logs/`、`*.jsonl`、`training_data/`、`LXGWZhenKaiGB-Regular.ttf`、`models/*.bin.gz`、`node_modules/`
- [x] 2.3 执行 `git rm --cached GameEngine.so` 取消 track 编译产物
- [x] 2.4 执行 `git rm --cached LXGWZhenKaiGB-Regular.ttf` 取消 track 字体文件
- [ ] 2.5 提交 Phase 1 清理结果

## 3. 创建目录结构 + 移动文件（Phase 2）

- [x] 3.1 创建 `game/` 目录及子目录 `game/assets/`、`game/data/`，创建 `game/__init__.py`
- [x] 3.2 移动游戏文件：`game.py`、`game_logic.py`、`game_logger.py`、`model_weights.txt` → `game/`；`LXGWZhenKaiGB-Regular.ttf` → `game/assets/`；`opening_book.json`、`opening_seeds.json`、`select_opening.py` → `game/data/`
- [x] 3.3 更新 `game/game.py` 中的路径引用：`BASE_DIR` 改为 `Path(__file__).resolve().parent`，KataGomo 路径改为 `parent.parent / "KataGomo"`，资源路径指向 `assets/` 和 `data/`
- [x] 3.4 创建 `ml/` 目录及子目录 `ml/data/`、`ml/webui/`，创建 `ml/__init__.py`
- [x] 3.5 移动 ML 文件：`automl_cli.py`、`mlevo_cli.py`、`training_ui.py`、`dag_engine.py`、`model_registry.py`、`plan_registry.py`、`run_training_loop.py`、`populate_opening_book.py`、`verify_opening_book.py`、`verify_symmetry.py`、`training_ui_state.json` → `ml/`
- [x] 3.6 移动 ML 数据：`model_registry.jsonl`、`plan_registry.jsonl` → `ml/data/`；`models/` → `ml/data/models/`；`training_data/` → `ml/data/training_data/`；`logs/` → `ml/data/logs/`
- [x] 3.7 移动 `webui/app.py` → `ml/webui/app.py`
- [x] 3.8 更新 `ml/` 下所有文件的路径引用：`BASE_DIR`、KataGomo 路径、数据文件路径、subprocess 调用其他 CLI 的路径
- [x] 3.9 更新 `ml/webui/app.py` 中对 `mlevo_cli.py` 的 subprocess 路径引用
- [x] 3.10 创建 `tools/` 目录，创建 `tools/__init__.py`，移动 `ai_worker.py`、`headless_runner.py` → `tools/`
- [x] 3.11 更新 `tools/ai_worker.py` 和 `tools/headless_runner.py` 中的 DLL 路径、KataGomo 配置路径
- [x] 3.12 创建 `engine/src/` 目录，移动 C++ 源码：`GameEngine.h`、`GameEngineDLL.cpp`、`GameEngineDLL.h`、`KataInferenceAdapter.cpp`、`KataInferenceAdapter.h`、`KataSelfplayMain.cpp` → `engine/src/`；`CMakeLists.txt`、`build.bat`、`build.sh` → `engine/`
- [x] 3.13 更新 `engine/CMakeLists.txt` 中的源文件路径（从 `./` 改为 `src/`）

## 4. 更新测试 + pyproject.toml（Phase 2 续）

- [x] 4.1 创建 `tests/game/` 和 `tests/ml/` 目录，创建各自的 `__init__.py`
- [x] 4.2 移动测试文件：`test_game_logic.py`、`test_dll_integration.py` → `tests/game/`；其余测试 → `tests/ml/`
- [x] 4.3 更新所有测试文件中的 import 路径：`from game_logic` → `from game.game_logic`，`from model_registry` → `from ml.model_registry` 等
- [x] 4.4 更新 `tests/test_dll_integration.py` 中的 DLL 路径
- [x] 4.5 更新 `tests/ml/test_branch.py`、`test_cli_state.py`、`test_integration.py`、`test_migration.py` 中的 subprocess CLI 路径
- [x] 4.6 更新 `pyproject.toml` 的 `pythonpath` 配置，确保 `game`、`ml`、`tools` 包可被发现
- [x] 4.7 更新 `tests/conftest.py` 如有需要

## 5. 验证 + 提交（Phase 3）

- [x] 5.1 运行安全网测试（Phase 0 写的），确认所有模块可达、文件存在、子进程调用正常
- [x] 5.2 运行 `pytest tests/` 全量测试，确认无回归
- [ ] 5.3 验证 `python -m game.game` 或 `python game/game.py` 能正常启动（如有显示设备）
- [x] 5.4 验证 `python ml/mlevo_cli.py --help` 和 `python ml/automl_cli.py --help` 正常输出
- [x] 5.5 验证 `engine/CMakeLists.txt` 路径正确（cmake -B build . 不报错）
- [x] 5.6 检查根目录整洁性：无散落源码、无临时产物
- [ ] 5.7 提交全部变更，附带重组说明
