## MODIFIED Requirements

### Requirement: 测试分层体系
系统 SHALL 支持四层测试：单元测试（纯逻辑，<1s）、集成测试（tiny preset 真实训练，<60s）、WebUI 测试（前后端组件，<30s）、E2E 验收（full preset，用户手动触发）。Agent SHALL 能通过 `mlevo test --suite all --json` 一键执行前三层。测试目录 SHALL 按系统分为 `tests/game/` 和 `tests/ml/`，与源码包结构对应。

#### Scenario: 执行全部自动测试
- **WHEN** 用户执行 `mlevo test --suite all --json`
- **THEN** 依次执行 unit、integration、webui-api、webui-ui 测试，返回汇总报告

#### Scenario: 单独执行单元测试
- **WHEN** 用户执行 `mlevo test --suite unit --json`
- **THEN** 仅执行单元测试，返回结果

#### Scenario: 测试目录与源码包对应
- **WHEN** 项目重组完成
- **THEN** `tests/game/` 包含游戏相关测试（`test_game_logic.py`、`test_dll_integration.py`），`tests/ml/` 包含 ML 相关测试（`test_automl.py`、`test_branch.py`、`test_cli_state.py`、`test_dag_engine.py`、`test_integration.py`、`test_migration.py`、`test_mlevo.py`、`test_model_registry.py`、`test_training_pipeline.py`、`test_webui_api.py`）

### Requirement: 单元测试覆盖
单元测试 SHALL 覆盖：model_registry（注册、hash 唯一、parent 关系、环检测）、dag_engine（拓扑排序、分支创建、无环校验）、decision_engine（参数调整、早停触发）。每个测试 SHALL 在 1 秒内完成。所有 import 路径 SHALL 使用新的包路径（`from ml.model_registry import`、`from game.game_logic import`）。

#### Scenario: 模型注册表单元测试
- **WHEN** 执行 model_registry 相关单元测试
- **THEN** 验证注册、检索、过滤、环检测等所有场景

#### Scenario: DAG 引擎单元测试
- **WHEN** 执行 dag_engine 相关单元测试
- **THEN** 验证拓扑排序、分支创建、无环校验等所有场景

#### Scenario: 游戏逻辑单元测试
- **WHEN** 执行 game_logic 相关单元测试
- **THEN** 验证对称性检测、距离计算、低影响候选点选择等所有场景
