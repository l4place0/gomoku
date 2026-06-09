## 背景与根因

### 当前状态机结构

主循环每帧按顺序检查 6 个 Guard：

```
G1: winner is not None         → GAME_OVER (continue)
G2: not asked_open             → INIT dialog (fall-through! 无 continue)
G3: not ai_first_done and ...  → AI_FIRST (continue)
G4: len(history)==3 and ...    → THREE_HAND (continue)
G5: len(history)==4 and ...    → FIVE_HAND (continue)
G6: event loop + AI move       → NORMAL
```

### 核心 Bug 根因

**Bug 1（asked_three）**：`asked_three` 只在初始化和 `THREE_HAND` 分支中设置 `True`，从不被 undo 重置。悔棋回到 `history < 3` 后，`asked_three` 保持 `True`，G4 永远不再触发。

**Bug 2（keep_pos=None）**：五手N打中 `keep_pos is None` 时走 `continue`，但 `five_asked` 已经是 `True`，G5 永远不再触发。当前 `current_role == BLACK`、`len(history) == 4`，G6 AI_MOVE 守卫 `not (len==4 and BLACK)` 为 False，AI 也不走。游戏死锁。

---

## 设计决策

### 决策 1：GamePhase 枚举（显式状态）

```python
class GamePhase(Enum):
    INIT        = auto()  # 开局对话框未展示
    AI_FIRST    = auto()  # AI 天元先手（history=0，AI执黑）
    THREE_HAND  = auto()  # 三手交换决策（history=3）
    FIVE_HAND   = auto()  # 五手N打交互（history=4，role=BLACK）
    NORMAL      = auto()  # 常规对弈
    GAME_OVER   = auto()  # 胜负已分
```

Phase 存储在 `GameState` 中，与 `history`、`current_role`、`human_is_black`、`winner` 一起形成完整快照，可序列化用于 undo。

**替代方案（拒绝）**：保留隐式 bool，仅修 bug。拒绝原因：扩展性差，无法根治 Bug 2 类死锁。

### 决策 2：GameState 数据类（可快照状态）

```python
@dataclass
class GameState:
    phase:          GamePhase
    history:        List[Tuple[int,int,int]]  # (x, y, role)
    current_role:   int                        # BLACK=0, WHITE=1
    human_is_black: bool
    winner:         Optional[int]
    five_candidates: List[Tuple[int,int]]     # 五手N打候选位置
    game_id:        Optional[str]

    def snapshot(self) -> 'GameState':
        return GameState(
            phase=self.phase,
            history=list(self.history),
            current_role=self.current_role,
            human_is_black=self.human_is_black,
            winner=self.winner,
            five_candidates=list(self.five_candidates),
            game_id=self.game_id,
        )
```

### 决策 3：Undo Stack（完整回溯）

`undo_stack: List[GameState]` 存储历史快照列表。

**推入时机**（在任何不可逆操作前）：
- `dll.DoMove` 调用前
- `dll.SwapHand` 调用前（使 swap 可被悔棋）

**弹出（悔棋）算法**：
```
1. pop prev_state from undo_stack
2. for move in reversed(current.history[len(prev.history):]):
       dll.UndoMove(env, move.x, move.y, move.role)
3. if current.human_is_black != prev.human_is_black:
       dll.SwapHand(env, prev.human_is_black)
4. restore current = prev_state
```

这彻底解决 Bug 1（phase 从快照恢复，asked_three 问题不复存在）和 Bug 2（phase 恢复为 FIVE_HAND 或 NORMAL）。

### 决策 4：主循环改为 Phase Dispatch

```python
while gs.phase != GamePhase.TERMINATED:
    btn, sidebar_buttons = draw(gs); pygame.display.flip()
    
    if gs.phase == GamePhase.GAME_OVER:
        handle_game_over(gs)
    elif gs.phase == GamePhase.INIT:
        handle_init(gs)
    elif gs.phase == GamePhase.AI_FIRST:
        handle_ai_first(gs)
    elif gs.phase == GamePhase.THREE_HAND:
        handle_three_hand(gs)
    elif gs.phase == GamePhase.FIVE_HAND:
        handle_five_hand(gs, btn, sidebar_buttons)
    elif gs.phase == GamePhase.NORMAL:
        handle_normal(gs, btn, sidebar_buttons)
```

每个 handler 是纯函数（接受 `gs`，修改 `gs`，不依赖外部状态 except DLL/screen globals）。

### 决策 5：GameLogger 独立模块

```
game_logger.py
└── class GameLogger
    ├── __init__(log_dir)         设置路径，确保 logs/ 目录
    ├── game_start(human_color)   写 game_start 事件，生成 game_id
    ├── move(x, y, role, player, search_id=None, phase=None)
    │                             写 move 事件，含 search_id 关联
    ├── phase_transition(from_p, to_p, data={})
    │                             写 phase_transition 事件
    ├── swap(decision, score_b, score_w, by)
    │                             写 swap 事件（含评分）
    ├── five_n(candidates, chosen, by)
    │                             写 five_n 事件
    ├── undo(from_len, to_len)    写 undo 事件
    ├── game_end(winner, reason)  写 game_end 事件
    └── session_end()             安全关闭：如局未结束则补写 game_end(winner=None, reason='quit')
```

`move` 事件结构（新增 `search_id` 和 `phase` 字段）：
```json
{
  "type": "move",
  "game_id": "20260526_173000",
  "move_num": 8,
  "x": 7, "y": 6,
  "role": "black",
  "player": "ai",
  "phase": "NORMAL",
  "search_id": 6,
  "timestamp": "2026-05-26T17:30:12.123456"
}
```

### 决策 6：draw() 函数接受 gs 参数

`draw(gs)` 替换 `draw()`，直接从 `GameState` 读取 `winner`、`current_role`、`human_is_black`、`five_candidates`，消除对全局散落变量的依赖。

---

## 保持不变的部分

- `draw_realistic_board()`、`draw_stone()`、`draw_search_log_panel()` 等所有渲染函数
- `confirm()`、`alert()` 对话框
- `capture_search_log()` 和 `search_log_entries` 逻辑
- `decide_search_framework()`、开局库、MCTS/MiniMax 搜索路由
- `five_asked` 更名为 `GameState.phase == FIVE_HAND`，原 `five_move_candidate_count` 保持为全局配置变量
- DLL 接口、`env`、`dll.*` 调用保持不变

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| draw() 签名变更破坏调用处 | 中 | grep 全文替换 `draw()` → `draw(gs)`，统一修改 |
| GameState 快照包含 `five_candidates` 可能影响显示 | 低 | draw(gs) 从 gs.five_candidates 读取，行为一致 |
| undo 跨 SWAP 时 dll.SwapHand 调用时序 | 中 | 先 UndoMove 所有落子，再 SwapHand，测试用例覆盖 |
