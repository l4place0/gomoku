## ADDED Requirements

### Requirement: 模块可达性测试
安全网测试 SHALL 验证每个 Python 包（`game`、`ml`、`tools`）能被正常 import，不抛出 `ModuleNotFoundError` 或 `ImportError`。

#### Scenario: 导入游戏包
- **WHEN** 执行 `import game.game_logic`、`import game.game_logger`
- **THEN** 导入成功，无异常

#### Scenario: 导入 ML 包
- **WHEN** 执行 `import ml.model_registry`、`import ml.plan_registry`、`import ml.dag_engine`、`import ml.automl_cli`、`import ml.mlevo_cli`
- **THEN** 导入成功，无异常

#### Scenario: 导入 tools 包
- **WHEN** 执行 `import tools.ai_worker`
- **THEN** 导入成功，无异常（DLL 加载失败可接受，但 import 本身不应报错）

### Requirement: 文件存在性测试
安全网测试 SHALL 验证所有关键文件路径在重组后仍然可达。

#### Scenario: 游戏资源文件存在
- **WHEN** 检查 `game/model_weights.txt`、`game/assets/LXGWZhenKaiGB-Regular.ttf`、`game/data/opening_book.json`
- **THEN** 所有文件存在

#### Scenario: KataGomo 配置文件存在
- **WHEN** 检查 `KataGomo/models/model.bin.gz`、`KataGomo/scripts/gomocup/default_gtp.cfg`
- **THEN** 文件存在（或在测试环境中跳过）

#### Scenario: C++ 引擎源码存在
- **WHEN** 检查 `engine/src/GameEngineDLL.cpp`、`engine/src/GameEngine.h`、`engine/CMakeLists.txt`
- **THEN** 所有文件存在

### Requirement: 子进程调用测试
安全网测试 SHALL 验证通过 subprocess 调用 CLI 工具时路径正确。

#### Scenario: mlevo_cli 可被 subprocess 调用
- **WHEN** 执行 `subprocess.run([sys.executable, "ml/mlevo_cli.py", "--help"])`
- **THEN** 返回码为 0，输出包含帮助信息

#### Scenario: automl_cli 可被 subprocess 调用
- **WHEN** 执行 `subprocess.run([sys.executable, "ml/automl_cli.py", "--help"])`
- **THEN** 返回码为 0，输出包含帮助信息

### Requirement: C++ 构建路径测试
安全网测试 SHALL 验证 CMakeLists.txt 中的源文件路径在重组后仍然有效。

#### Scenario: cmake 配置成功
- **WHEN** 在 `engine/` 目录执行 `cmake -B build .`
- **THEN** cmake 配置成功，不报文件找不到错误

### Requirement: 测试目录结构验证
安全网测试 SHALL 验证测试目录结构与源码目录结构对应。

#### Scenario: 测试文件按系统分组
- **WHEN** 检查 `tests/game/` 和 `tests/ml/` 目录
- **THEN** `tests/game/` 包含游戏相关测试，`tests/ml/` 包含 ML 相关测试
