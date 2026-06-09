## 1. 流程约束与配置文件初始化

- [x] 1.1 在项目根目录创建 `AGENTS.md` 约束文件，添加 TDD 强制开发纪律 rule
- [x] 1.2 创建并配置 `pyproject.toml` 作为项目 pytest 核心配置文件
- [x] 1.3 创建 `tests/` 目录结构，并配置 `tests/conftest.py` 全局 fixture 及环境防御

## 2. 纯逻辑函数提取与重构

- [x] 2.1 创建 `game_logic.py`，存放解耦后的五子棋纯算法逻辑
- [x] 2.2 将 `game.py` 中的 `is_symmetric` 和对称检测逻辑移植至 `game_logic.py`
- [x] 2.3 将 `game.py` 中的 `choose_low_impact_candidates_for_black` 等核心纯计算候选点逻辑移入 `game_logic.py`
- [x] 2.4 重构 `game.py` 内部的调用，将其改写为从 `game_logic.py` 导入以确保后向兼容性与 GUI 正常运行

## 3. Tier 1 Python 单元测试集构建

- [x] 3.1 编写 `tests/test_game_logic.py` 覆盖 `is_symmetric` 各个方向的板面翻转及对称性验证
- [x] 3.2 在单元测试中覆盖 `choose_low_impact_candidates_for_black` 的算法逻辑，在没有 Pygame 和 DLL 的情况下独立验证开局低影响点的选取
- [x] 3.3 运行单元测试并确保全部通过

## 4. Tier 2 DLL 集成测试集构建

- [x] 4.1 编写 `tests/test_dll_integration.py` 验证通过 ctypes/cffi 加载 `GameEngineDLL.dll` 是否成功
- [x] 4.2 编写集成测试，测试 DLL 提供的下子、状态机转换逻辑
- [x] 4.3 编写五子棋禁手检测集成测试，通过 DLL 验证黑棋三三禁手、四四禁手、长连禁手等规则的判定是否正确
- [x] 4.4 编写集成测试验证输赢状态机判定

## 5. Tier 3 手动验证 SOP 与 CI 流程准备

- [x] 5.1 在 `tests/README.md` 中编写详细的验证 SOP（覆盖 GUI 渲染测试、CUDA 模式下神经网络运行测试与双模型自对弈测试）
- [x] 5.2 整体运行自动化测试套件 `pytest`，修复所有发现的逻辑缺陷，生成最终测试报告
