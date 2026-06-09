## Context

随着五子棋博弈引擎引入“三阶段混合对弈”（开局秒回-中盘MCTS-残局MiniMax战术算杀），右侧 Dashboard 呈现的数据指标变得极为庞杂。然而，由于当前的绘制逻辑是硬编码的静态排列，导致玩家在开局时看到一大堆 AB 搜索节点为零或 None，在残局 AB 战术算杀时又看到神经网络参数等冗余或空数据，信息密度和语义感知度差。

此外，系统的调试日志只打印在控制台标准输出中，关闭窗口后便丢失，不利于长期演进和复杂对局调试。AI 的同步计算也导致 Pygame 主界面冰冻，引起玩家误点击排队，在计算结束后会触发“自动抢跑落子”的严重体验 Bug。

---

## Goals / Non-Goals

**Goals:**
- 实现侧边栏 Dashboard 数据指标的“按需动态渲染”，大幅提升界面高级感和信息语义清晰度。
- 引入统一的 `logging` 系统，将完整的运行时关键对局状态、引擎检索和日志数据同步持久化到 `logs/runtime.log` 下。
- 提供 AI 思考状态下的全屏遮挡 UI 反馈，并在 AI 搜索结束时硬性清除鼠标事件缓冲队列，彻底避免点击抢跑排队问题。

**Non-Goals:**
- 不改变 C++ DLL 搜索引擎的原生输出和通信格式。
- 不将主计算线程移至复杂的多线程后台，仍维持当前的同步计算模型，但通过渲染管线与事件清除手段达到无暇的用户体验。

---

## Decisions

### 决策 1：基于状态决策的侧边栏动态上下文视图引擎
- **方案选择**：在 `draw_search_log_panel()` 中获取 `current_framework_stage`。根据阶段（Book / MCTS / MiniMax / VCF）动态分发渲染逻辑。
- **动态视图模型**：
  - **Book 阶段**：仅展现开局库检索状态、匹配对称面、开局风格以及推荐落子，彻底隐藏 MCTS/MiniMax 所有繁琐字段。
  - **MCTS 阶段**：突出展现神经网络参数、Visits 限额上限、KataGomo 是否就绪/激活/应用的布尔标志、神经网络状态以及局势雷达输出。
  - **MiniMax / VCF 阶段**：强制将 Visits 显示清零或标为 AB，展现 AB 评分、迭代加深搜索深度 (depth)、全盘检索总节点数 (nodes)、置换表哈希命中率 (hash) 与 Beta 剪枝量 (betaCuts)，完全隐藏神经网络所有字段。

### 决策 2：建立统一的主程序 Logging 持久化中心
- **方案选择**：采用内置的标准 `logging` 模块建立一个名为 `GomokuRuntime` 的全局 Logger。
- **架构设计**：
  - 针对文件输出：注册 `logging.FileHandler` 写入 `logs/runtime.log`，日志级别设为 `DEBUG`，记录最详尽的引擎心跳与日志序列。
  - 针对控制台输出：保持简洁，主要打印核心对局状态，提供更清爽的终端视觉。
  - 覆盖范围：系统启动初始化、悔棋、人类落子、AI 状态决策、雷达扫描、搜出最佳落子以及落子后胜负检测，均调用该统一日志器同步落盘。

### 决策 3：思考期全屏 UI 视觉锁定与 Pygame 事件清空拦截
- **方案选择**：
  1. **状态标志阀**：引入全局状态变量 `ai_is_searching = False`。
  2. **遮罩渲染**：在 `draw()` 渲染管线中，若检测到 `ai_is_searching` 为 True，在棋盘主区域上方覆盖绘制一层带有微弱透明度的暗色 Surface，并在正中央渲染一个精美的白底圆角对话框卡片，显示 `"AI 正在思考中... \n 请勿落子或点击界面"`。
  3. **时序控制**：
     - 在 AI 普通回合入口调用 `dll.GetTopMoves` 之前，立即设置 `ai_is_searching = True`，同步调用 `draw()` 及 `pygame.display.flip()` 更新图层。
     - 在 `dll.GetTopMoves` 计算返回的下一行，立即将 `ai_is_searching = False`。
     - **最关键的一步**：立即执行 `pygame.event.clear(pygame.MOUSEBUTTONDOWN)` 与 `pygame.event.clear(pygame.MOUSEBUTTONUP)`。这能彻底清除在 AI 思考（界面卡死）期间用户因心急而胡乱点击的物理事件，切断点击排队时序流。

---

## Risks / Trade-offs

- **[Risk]** 在 AI 思考过程中，Pygame 处于同步卡死状态，操作系统可能会误认为“程序未响应”。
  - **Mitigation**：由于我们在计算开始的一瞬间就绘制并 Flip 了精致的半透明遮罩卡片，玩家有了明确的视觉预期。此外，对于正常的算杀（一般在几百毫秒内返回），玩家体感极快，UI 体验仍非常流畅高级。
- **[Risk]** 日志文件 `logs/runtime.log` 随着长久对弈越来越大。
  - **Mitigation**：使用 `FileHandler` 或直接在游戏每次启动时对日志文件进行截断/重写（即覆盖写入模式 `mode='w'`），只保留当次最鲜活的调试日志，或者采用 `RotatingFileHandler` 限制最大尺寸。在此我们采用 `mode='w'`（覆盖写入）以聚焦当次对局调试。
