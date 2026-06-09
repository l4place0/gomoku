## ADDED Requirements

### Requirement: 侧边栏 Dashboard 动态决策上下文聚合
系统 SHALL 根据当前引擎决策阶段 (`current_framework_stage`) 动态切换右侧分析面板 (Dashboard) 的排版布局与展现字段，隐藏该阶段无关、未初始化或冗余的引擎指标，以呈现高聚合度的决策语义图景。

#### Scenario: 侧边栏在开局秒回库阶段的呈现
- **WHEN** 决策阶段为 `Book` 且 AI 触发秒回开局
- **THEN** 侧边栏 SHALL 展现开局风格设定、当前对称变换还原结果及推荐着步列表，同时隐藏 MiniMax (AB) 与 MCTS (Kata) 涉及的搜索节点、哈希命中率及 visits 细节

#### Scenario: 侧边栏在 MCTS 神经网络布局阶段的呈现
- **WHEN** 决策阶段为 `MCTS` 且 AI 启用 KataGomo 搜索
- **THEN** 侧边栏 SHALL 展现 Visits 参数限额、神经网络参数 (Policy/Value Blend)、KataGomo 启用就绪就绪度及局势雷达活三/冲四威胁数，同时隐藏 AB 搜索节点数、哈希命中率与 Beta 剪枝量等指标

#### Scenario: 侧边栏在 MiniMax 战术收割阶段的呈现
- **WHEN** 决策阶段为 `MiniMax` 且 AI 强行关停神经网络进行深层 AB 算杀
- **THEN** 侧边栏 SHALL 高亮展现 AB 评分、迭代加深搜索深度 (depth)、检索总节点数 (nodes)、置换表哈希命中率 (hash) 与 Beta 剪枝量 (betaCuts)，同时将神经网络 visits 强制清零并隐藏 Neural Net 的推理参数

---

### Requirement: 运行时系统日志同步持久化
系统 SHALL 在主对弈进程中集成标准 `logging` 模块，将启动配置、悔棋/落子、局势雷达扫描数据、决策路由器分支选择以及底层搜索日志以规范化、高可读的带时间戳格式，同步持久化输出至 `logs/runtime.log` 中。

#### Scenario: 游戏核心事件同步写入日志
- **WHEN** 系统启动、游戏回合推进、用户操作发生或者 AI 完成搜索
- **THEN** 系统 SHALL 立即将当前操作与引擎的核心属性组装为规范格式，异步或同步写入 `logs/runtime.log` 中

---

### Requirement: AI思考期视觉拦截遮罩与点击队列清空
系统 SHALL 在 AI 进行同步高负荷检索计算时，于主界面棋盘区渲染高辨识度的半透明遮罩与“思考中”提示卡片，明确告知玩家，并在 AI 落子计算完毕后立即清空在此期间用户误触积压的鼠标事件队列，根治点击抢跑 (Click Queueing) Bug。

#### Scenario: AI 思考期拦截用户操作并在结束后清空点击事件
- **WHEN** AI 开始调用 `dll.GetTopMoves` 搜索，使得 `ai_is_searching` 为 True
- **THEN** 系统 SHALL 在棋盘区绘制一层黑色半透明图层与卡片，遮挡并明确锁定操作；在搜索完成后，系统 SHALL 重置 `ai_is_searching` 状态，并调用 Pygame 事件清空 API 彻底抹除由于同步卡顿积压在队列中的 `MOUSEBUTTONDOWN` 与 `MOUSEBUTTONUP` 鼠标点击事件，随后再交付控制权给人类
