## 1. 运行时日志系统同步持久化 (game.py)

- [x] 1.1 在 `game.py` 顶层配置标准 `logging` 服务，创建全局 `logger = logging.getLogger("GomokuRuntime")`，并注册覆盖写入日志文件 `logs/runtime.log` 的 `FileHandler`
- [x] 1.2 重构 `game.py` 中游戏主循环、悔棋、人类落子、AI 决策分支、雷达扫描等处的 `print` 语句，同步使用 `logger.info` 记录并同步落盘持久化

## 2. 侧边栏 Dashboard 动态决策上下文聚合 (game.py)

- [x] 2.1 修改 `draw_search_log_panel()` 的渲染架构，实现对决策阶段 `current_framework_stage` 的分支判断
- [x] 2.2 实现 `Book` 阶段的专属视图：显示对称转换、匹配走步、风格设定，并完全隐藏 MCTS/MiniMax 的底层信息
- [x] 2.3 实现 `MCTS` 阶段的专属视图：高亮神经网络 Visits 限制、神经网络评估参数 (Policy/Value Blend) 及当前神经网络状态信息
- [x] 2.4 实现 `MiniMax` 阶段的专属视图：强制 visits 显示为 AB 且将网络状态标为 Disabled，展现 AB 评分、迭代加深搜索深度 (depth)、全盘检索总节点数 (nodes)、置换表哈希命中率 (hash) 与 Beta 剪枝量 (betaCuts)

## 3. AI思考期全屏 UI 视觉拦截与事件清空机制 (game.py)

- [x] 3.1 在 `game.py` 初始化区定义全局状态变量 `ai_is_searching = False`
- [x] 3.2 在 `draw()` 函数中实现基于 `ai_is_searching` 的全盘暗色半透明图层遮罩与正中央“AI 正在思考中，请勿落子...”的精致提示卡片渲染
- [x] 3.3 在 AI 启动 `dll.GetTopMoves` 搜索前后，精准切换 `ai_is_searching` 状态并执行界面更新
- [x] 3.4 在 AI 搜索返回时，立即调用 `pygame.event.clear(pygame.MOUSEBUTTONDOWN)` 与 `pygame.event.clear(pygame.MOUSEBUTTONUP)` 清空积压的误触鼠标事件队列，根治抢跑 Bug

## 4. 全局集成测试与功能验证

- [x] 4.1 测试开局查库阶段：验证 Dashboard 布局是否干净，不包含冗余 metrics，日志同步持久化到 `logs/runtime.log`
- [x] 4.2 测试 MCTS 与 MiniMax 阶段：验证 Dashboard 切换是否实时、精准，显示相对应的专属数据
- [x] 4.3 测试 AI 思考期遮罩与清空拦截：验证在 AI 算棋期间是否有精美卡片遮挡，且计算完后没有发生任何“点击排队抢跑落子”现象
