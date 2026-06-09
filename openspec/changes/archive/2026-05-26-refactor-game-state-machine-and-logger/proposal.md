## Why

当前 `game.py` 的主循环使用 **6 个离散布尔变量**（`asked_open`、`asked_three`、`ai_first_done`、`five_asked`、`winner`、`virtual_candidates`）加上 `len(history)` 和 `current_role` 的特定组合来隐式表达游戏阶段。这导致了以下问题：

1. **Bug：悔棋后 `asked_three` 不重置** — 激进悔棋回到 0 手后，三手交换规则被永久跳过，无法再触发
2. **Bug：五手N打 `keep_pos=None` 死锁** — 当候选评估返回空时游戏彻底卡死，唯一出路是关闭程序
3. **风险：G2（开局对话框）无 `continue` 是隐式 fall-through** — 无注释说明，极易被后续维护者误改
4. **风险：AI_MOVE 守卫使用魔法数字** — `not (len==4 and role==BLACK)` 硬编码阶段判断，扩展性差
5. **日志孤岛** — `game_records.jsonl` 与 `search_logs.jsonl` 之间无关联字段，无法追踪"哪局哪手AI做了什么决策"
6. **无重置路径** — `GAME_OVER` 是终态，只能关闭程序重开

## What Changes

### 1. 显式状态机（`GamePhase` 枚举 + `GameState` 数据类）

用 `GamePhase` 枚举替换所有隐式布尔标志，用 `GameState` 数据类聚合所有可快照的游戏状态：

```
INIT → AI_FIRST → THREE_HAND → FIVE_HAND → NORMAL → GAME_OVER
```

主循环改为基于当前 Phase 的分发（dispatch），每个阶段有独立的处理函数。

### 2. 完整回溯（Undo Stack）

维护 `undo_stack: List[GameState]` 快照列表。每次 `DoMove` / `SwapHand` 前推入快照；悔棋时弹出快照、调用 `dll.UndoMove` 复原棋盘、并恢复 `human_is_black` 到 DLL（若发生过交换）。这彻底修复悔棋问题，无需手动 reset 任何标志。

### 3. 统一结构化日志器（`game_logger.py`）

新建独立模块 `game_logger.py`，包含 `GameLogger` 类：
- 每个事件类型有独立方法：`game_start`、`move`、`phase_transition`、`swap`、`five_n`、`undo`、`game_end`
- `move` 事件携带 `search_log_id` 字段，关联 `search_logs.jsonl`
- 窗口关闭时自动调用 `session_end()`，防止 `game_end` 事件丢失

## Capabilities

### Modified Capabilities

- `engineering`: 游戏主循环架构重构、日志系统设计规范

## Impact

- **`game_logger.py`** [NEW]: 独立结构化日志模块
- **`game.py`** [MODIFY]: 主循环重构（约删除 450 行旧主循环，新增 ~400 行显式状态机）；保留所有 `draw_*`、`confirm`、`alert` 等 UI 函数不变
