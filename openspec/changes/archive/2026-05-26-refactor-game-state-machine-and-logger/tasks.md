## 第一组：基础设施（game_logger.py + GamePhase/GameState）

- [x] 1.1 新建 `game_logger.py`，实现 `GameLogger` 类，包含所有日志方法：
      `game_start`, `move`（含 `search_id`、`phase` 字段），`phase_transition`,
      `swap`, `five_n`, `undo`, `game_end`, `session_end`。

- [x] 1.2 在 `game.py` 顶部添加 `GamePhase(Enum)` 枚举（6个阶段：
      INIT / AI_FIRST / THREE_HAND / FIVE_HAND / NORMAL / GAME_OVER）。

- [x] 1.3 在 `game.py` 中添加 `GameState` 数据类，包含：
      `phase`, `history`, `current_role`, `human_is_black`,
      `winner`, `five_candidates`, `game_id`，以及 `snapshot()` 方法。

- [x] 1.4 添加 `undo_stack: List[GameState] = []` 全局列表，
      以及 `push_checkpoint(gs)` 和 `apply_undo(gs)` 两个辅助函数。
      `apply_undo` 负责调用 `dll.UndoMove` + 条件性 `dll.SwapHand`。

- [x] 1.5 在 `game.py` 中实例化 `game_logger = GameLogger(LOG_DIR)`，
      并在程序末尾 `dll.ReleaseEngine` 前调用 `game_logger.session_end()`。

## 第二组：主循环重构（Phase Handlers）

- [x] 2.1 将 `draw()` 签名改为 `draw(gs: GameState)`，从 `gs` 读取
      `winner`、`current_role`、`human_is_black`、`five_candidates`，
      删除对应全局变量的直接引用（在 draw 函数内部）。
      同步更新所有调用处：`confirm()` / `alert()` 内部的 `draw()` 调用也同步修改。

- [x] 2.2 实现 `handle_init(gs)` —— 替换 G2 (`asked_open`) 逻辑：
      展示开局换手对话框，更新 `gs.human_is_black`，若有换手则 `push_checkpoint + dll.SwapHand`，
      调用 `game_logger.game_start`，转移到 `AI_FIRST`（若 AI 执黑）或 `NORMAL`。

- [x] 2.3 实现 `handle_ai_first(gs)` —— 替换 G3 (`ai_first_done`) 逻辑：
      `push_checkpoint(gs)` → `dll.DoMove(天元)` → `gs.history.append` →
      `game_logger.move` → 检查胜负 → 转移到 `THREE_HAND`（history==1）或 `NORMAL`。

- [x] 2.4 实现 `handle_three_hand(gs)` —— 替换 G4 (`asked_three`) 逻辑：
      按 `gs.human_is_black` 决定由人类或 AI 做决策；若换手：
      `push_checkpoint(gs)` → `dll.SwapHand` → `gs.human_is_black` 更新 →
      `game_logger.swap` → 转移到 `FIVE_HAND`（history==3，下一手第4手）或 `NORMAL`。
      注意：三手交换后 gs.phase 置为 NORMAL（等待第4手落子），当 history==4 且
      current_role==BLACK 时由主循环转入 FIVE_HAND。

- [x] 2.5 实现 `handle_five_hand(gs, btn, sidebar_buttons)` —— 替换 G5 逻辑：
      - 进入时计算候选，`gs.five_candidates = selected`
      - 人类执黑路径：玩家交互选 N 个候选 → AI 保留一个 → `push_checkpoint + DoMove`
      - AI执黑路径：AI 计算候选 → 玩家选一个 → `push_checkpoint + DoMove`
      - `keep_pos is None` 时：将 `gs.five_candidates = []` 并 `gs.phase = NORMAL` 退出，
        **不再死锁**（Fix Bug 2）
      - 成功落子后：`game_logger.five_n + game_logger.move` → 检查胜负 → 转移 `NORMAL`

- [x] 2.6 实现 `handle_normal(gs, btn, sidebar_buttons)` —— 替换 event loop + G6 逻辑：
      - `QUIT` 事件 → `gs.phase = GAME_OVER`（不再直接 `run=False`）
      - 悔棋按钮：调用 `apply_undo(gs)` 1 或 2 次 → `game_logger.undo` →
        `five_asked` 等标志从快照自动恢复（**Fix Bug 1**）
      - 人类落子：`push_checkpoint + dll.DoMove` → `game_logger.move` → 胜负检查
      - AI落子: Book/MCTS/MiniMax 路由（逻辑不变）→ `capture_search_log` 获取 `search_id` →
        `push_checkpoint + dll.DoMove` → `game_logger.move(search_id=...)` → 胜负检查

- [x] 2.7 实现 `handle_game_over(gs)` —— 替换 G1 (`winner`) 逻辑：
      仅处理 `QUIT` 事件（`pygame.event.get()`），其余循环等待。
      增加 "再来一局" 按钮：点击后重置 `gs` 为新 `GameState`，清空 `undo_stack`，
      调用 `dll.ResetEngine(env)` 或重新初始化棋盘（待确认 DLL 接口）。

- [x] 2.8 删除旧主循环（L1124-L1571），替换为 Phase Dispatch 主循环：
      ```python
      gs = GameState(phase=GamePhase.INIT, ...)
      while gs.phase != GamePhase.TERMINATED:
          btn, sidebar_buttons = draw(gs); pygame.display.flip()
          dispatch(gs, btn, sidebar_buttons)
      ```

## 第三组：日志集成与验证

- [x] 3.1 在 `capture_search_log()` 返回 of entry 中提取 `searchId`，
      在 AI 落子的 `game_logger.move()` 调用中传入 `search_id=entry['searchId']`，
      实现两份 JSONL 文件的关联。

- [x] 3.2 在所有 phase transition 处调用 `game_logger.phase_transition`，
      记录状态机流转事件。

- [x] 3.3 运行 Python 语法检查：
      `python -c "import ast; ast.parse(open('game.py').read()); print('OK')"`
      以及 `python -c "import game_logger; print('OK')"`

- [x] 3.4 手动测试路径覆盖（描述性，无自动化）：
      - 路径 A：人类执黑，普通对局直至胜负，验证 game_records.jsonl 含完整记录
      - 路径 B：AI先手，三手交换AI换执黑，五手N打，验证 phase_transition 事件序列
      - 路径 C：激进悔棋（悔回0手再重新开始），验证三手交换可重新触发
      - 路径 D：五手N打评估返回 None，验证游戏不死锁
      - 路径 E：关闭窗口（未分胜负），验证 session_end 写入 game_end(reason='quit')
