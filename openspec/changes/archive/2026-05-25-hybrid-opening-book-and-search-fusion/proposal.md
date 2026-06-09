## Why

五子棋博弈引擎当前在三个阶段存在核心棋力与算力瓶颈：
1. **开局阶段算力空转**：开局前几手盘面太空，MiniMax 搜索不仅效率极低且缺乏大局观，而一直运行神经网络 MCTS 又极耗费显存与计算时间。
2. **搜索框架排序粗糙**：由于置换表（TT）中的最佳着法字段未被写入与利用，且缺乏杀手启发（Killer Move）和历史启发（History Heuristic），导致在深度搜索时 Alpha-Beta 剪枝效率偏低，同等思考时间内看不够深。
3. **融合权重死板**：神经网络与 MiniMax 搜索的融合在全盘均采用固定比例，未能发挥“开局重布局战略（MCTS 强项），终局重绝对死活（MiniMax 强项）”的互补优势。

本变更旨在通过引入**双源动态开局库**、**动态搜索排序启发式套件**与**双框架动态切换机制**，实现“开局库秒回-中盘MCTS战略布局-残局MiniMax精确收割”的三阶段混合博弈体系，大幅度提升棋力与搜索性能。

## What Changes

- **双源动态开局库**：
  - 引入融合“传统 26 种直指/斜指职业定式”与“AI 自对弈自进化探索奇招”的双源开局库。
  - 实现基于 Zobrist 棋盘哈希的 **8 路对称性归一化** 开局检索。
  - 在 Python GUI 提供“传统稳健 / 创新奇招 / 随机混合”的开局风格选择。
- **搜索排序套件优化**：
  - 在置换表（TT）的 `HashItem` 中完整写入与检索 `bestMove`，首选 Hash Move 触发 Beta 剪裁。
  - 引入每个深度的双杀手走法（Killer Moves）缓存。
  - 引入全局历史启发（History Heuristic）加权机制。
- **双框架动态切换决策中心**：
  - 丢弃固定混合权重，在 Python GUI 侧加入动态 Visits 和搜索深度控制器。
  - 引入以“棋局步数、战术冲突（活三/冲四检测）、胜率两极分化”为指标的多维时机判定算法，自适应切换或平滑过渡 MCTS 与 MiniMax。

## Capabilities

### New Capabilities
- `opening-book`: 双源动态开局库。支持规范对称性 Zobrist 检索、导入 26 种经典直指/斜指开局库分支，并支持在自对弈或挖掘训练中，自动导出并沉淀高 Visits、高胜率的 AI 奇招走法。

### Modified Capabilities
- `framework`: 优化搜索框架层。支持在置换表中保存和检索 `bestMove`，并引入杀手启发（Killer Move）与历史启发（History Heuristic）算法优化 `negaMax` 动态排序，以换取极高的 Alpha-Beta 剪枝效率。
- `ml-training`: 优化机器学习与融合策略。支持由 Python 侧动态控制 visits 数并在中残局自适应降级，同时对混合公式进行基于手数量的动态调整，确保战略与战术的平衡。
- `engineering`: 优化工程与交互。在 Pygame UI 中集成开局风格切换按钮，并扩展日志面板以记录三阶段（开局库/MCTS/MiniMax）的实时决策切换过程。

## Impact

- **C++ 核心层 (`GameEngine.h`, `GameEngineDLL.cpp`, `GameEngineDLL.h`)**：
  - 需在置换表写入、`negaMax` 搜索和 `SwapHand`/`GetTopMoves` 流程中注入排序和控制逻辑，重新编译为 DLL。
- **Python GUI 层 (`game.py`)**：
  - 需构建开局库存储及检索模块、动态时机决策器，并修改界面渲染与按钮事件。
- **构建系统与数据**：
  - 引入外部轻量级开局库数据文件（JSON/SQLite）。
