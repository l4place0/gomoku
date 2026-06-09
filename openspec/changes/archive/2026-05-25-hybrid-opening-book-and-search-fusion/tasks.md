## 1. 棋盘对称性与开局库数据库构建

- [x] 1.1 在 Python 侧设计并实现 8 种对称变换（旋转与镜像翻转）的矩阵映射与坐标逆变换函数，并编写严格的单元测试
- [x] 1.2 创建开局库管理器 `OpeningBook`，支持加载及 $O(1)$ 检索 `opening_book.json` 数据文件
- [x] 1.3 导入 26 种经典直指与斜指的职业五子棋定式前 5 手数据，生成归一化哈希底子写入 `opening_book.json`

## 2. C++ 搜索引擎核心优化 (DLL重塑)

- [x] 2.1 修改 `GameEngine.h` 中的 `HashItem` 写入逻辑，确保每次发生剪裁或精确评估时写入 `bestMove`
- [x] 2.2 在 `GameEngine.h` 中新增双杀手着法缓存 `killerMoves` 和全局历史启发评分表 `historyScore`，并在每次 `getBestMoves` 时清理
- [x] 2.3 在 `GameEngine.h` 中实现 `getMoveSortScore(move, depth, hashMove)`，提供 Hash/Killer/History 的三级动态评分机制
- [x] 2.4 在 `negaMax` 递归搜索的每一步候选生成后，调用动态重排逻辑，并修改 Beta 剪裁机制以回填杀手缓存、历史评分与置换表
- [x] 2.5 运行 `.\build.bat` 重新配置并编译 C++ 引擎，生成最新的 `GameEngine.dll` 并确保无编译警告

## 3. Python 动态时机决策器与双框架整合

- [x] 3.1 在 `game.py` 中引入 `AI_SWAP_THRESHOLD` 配置，并设计全局局势雷达，统计活三与冲四数量
- [x] 3.2 实现 `decide_search_framework` 智能决策引擎，根据当前落子手数、战术冲突和胜率两极分化自适应挑选决策路线
- [x] 3.3 重构主对弈循环，将原有的单路搜索更新为“开局查库 -> MCTS 大局观 -> MiniMax 战术收割”的三阶段博弈数据流

## 4. 前端交互与 AI 自进化导出管线

- [x] 4.1 在 Pygame 侧边栏中渲染“传统稳健 / 创新奇招 / 随机混合”的开局风格选择按钮组，并实现点击高亮与状态同步事件
- [x] 4.2 在 UI 中集成本阶段决策状态文本，支持动态显示当前是“开局库 / MCTS / MiniMax / VCF算杀”
- [x] 4.3 修改 `training_ui.py` 中的自对弈数据流水线，增加高胜率/高 Visits 定式挖掘逻辑，使其在自对弈完毕后自动归一化沉淀并追加写入 `opening_book.json`

## 5. 功能校验与系统性评估

- [x] 5.1 验证前 5 手落子为开局库秒回，且走法丰富多变，完全契合传统定式与 AI 标签
- [x] 5.2 模拟进入中残局，验证在无威胁均势下正确调用 KataGomo 推理，有活三/冲四威胁时自动无缝降级切换为纯 MiniMax 算杀
- [x] 5.3 开启自对弈训练，验证 AI 发现的强势走法能自动以 `AI_NOVELTY` 标签动态入库，完成自进化闭环
