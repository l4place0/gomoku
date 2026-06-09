## 游戏状态机规范

### 1. GamePhase 枚举

游戏主循环必须使用显式 `GamePhase` 枚举驱动，禁止通过 `len(history)` + 多布尔变量的隐式组合来表达游戏阶段。

| Phase | 触发条件 | 退出条件 |
|-------|----------|----------|
| `INIT` | 程序启动 | 开局对话框关闭后 |
| `AI_FIRST` | `INIT` 结束且 AI 执黑（`not human_is_black`） | AI 落天元后 |
| `THREE_HAND` | `len(history) == 3` | 换手决策完成后 |
| `FIVE_HAND` | `len(history) == 4 and current_role == BLACK` | 第5手落子后 |
| `NORMAL` | 其他所有正常对弈回合 | 胜负判定 |
| `GAME_OVER` | `winner is not None` | 关闭窗口或再来一局 |

### 2. GameState 数据类

`GameState` 必须包含以下字段，且所有字段必须在 `snapshot()` 方法中深拷贝：

- `phase: GamePhase`
- `history: List[Tuple[int, int, int]]` — `(x, y, role)` 落子列表
- `current_role: int` — `BLACK=0` 或 `WHITE=1`
- `human_is_black: bool`
- `winner: Optional[int]`
- `five_candidates: List[Tuple[int, int]]` — 五手N打虚拟候选位置
- `game_id: Optional[str]`

### 3. Undo Stack 规范

- `undo_stack` 为 `List[GameState]` 快照列表
- **推入时机**：任何 `dll.DoMove` 或 `dll.SwapHand` 调用前，必须先 `push_checkpoint(gs)`
- **弹出（悔棋）算法**：
  1. 弹出 `prev = undo_stack.pop()`
  2. 对 `current.history[len(prev.history):]` 中的每个 move 倒序调用 `dll.UndoMove`
  3. 若 `current.human_is_black != prev.human_is_black`，调用 `dll.SwapHand(env, prev.human_is_black)`
  4. 将当前状态替换为 `prev`
- 悔棋 UI 每次最多弹出 2 个快照（对应悔 2 手）

## 结构化日志规范

### 1. 日志文件结构

所有对局事件追加写入 `logs/game_records.jsonl`，每行一个 JSON 对象。事件类型：

| `type` | 必填字段 | 说明 |
|--------|----------|------|
| `game_start` | `game_id`, `human_color`, `ai_color`, `timestamp` | 每局开始 |
| `move` | `game_id`, `move_num`, `x`, `y`, `role`, `player`, `phase`, `timestamp` | 每次落子 |
| `move`（AI） | 同上 + `search_id` | AI 落子需关联 search_logs.jsonl |
| `phase_transition` | `game_id`, `from_phase`, `to_phase`, `data`, `timestamp` | 状态机流转 |
| `swap` | `game_id`, `decision`, `score_black`, `score_white`, `by`, `timestamp` | 三手交换决策 |
| `five_n` | `game_id`, `candidates`, `chosen`, `by`, `timestamp` | 五手N打事件 |
| `undo` | `game_id`, `from_move_num`, `to_move_num`, `timestamp` | 悔棋操作 |
| `game_end` | `game_id`, `winner`, `total_moves`, `reason`, `timestamp` | 对局结束 |

### 2. search_id 关联规范

- AI 落子时，`capture_search_log()` 返回的 entry 中提取 `searchId` 字段
- 该 `search_id` 必须写入对应 `move` 事件的 `search_id` 字段
- 使用方：`jq 'select(.type=="move" and .search_id==6)' game_records.jsonl` 可定位任意 AI 决策对应的落子

### 3. session_end 安全规范

- 游戏通过关闭窗口退出时（`pygame.QUIT`），必须在 `dll.ReleaseEngine` 前调用 `game_logger.session_end()`
- `session_end()` 检查：若当前局未记录 `game_end` 事件，则补写 `game_end(winner=None, reason='quit')`
