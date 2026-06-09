## Context

### 根因分析（Bug #1）

游戏主循环中存在一个"AI先手天元落子"守卫：

```python
if not ai_first_done and not human_is_black:
    dll.DoMove(env, BOARD_SIZE//2, BOARD_SIZE//2, BLACK)
    history.append(...)
    current_role = WHITE; ai_first_done = True
    continue
```

该守卫本意是处理"用户开局选择让 AI 先手执黑"的场景（游戏第 0 手）。但三手交换的实现未考虑此守卫的副作用：

**正常开局（AI先手）**：`asked_open` 弹窗 → 用户同意换手 → `human_is_black=False` → 下一循环守卫触发 → 天元落子 → `ai_first_done=True` ✔

**三手交换（AI后验换手执黑）**：开局人类执黑（`ai_first_done=False`） → 三手落完 → AI 换手（`human_is_black=False`） → 下一循环守卫触发！→ 天元额外落子 → `ai_first_done=True` ✗

当三手交换完成时，`history` 已经有 3 颗棋子，所以不应再触发天元先手逻辑。

### 落子记录需求（Feature）

目前系统通过 `logging` 模块将运行时事件写入 `logs/runtime.log`，但落子日志夹杂在搜索和评估日志中，难以单独提取复盘。需要一个简洁独立的 `logs/game_records.jsonl` 文件，每行一个 JSON 事件，便于程序化解析和故障排查。

## Goals / Non-Goals

**Goals:**
- **修复状态机 Bug**：在三手交换完成后 AI 换手执黑时，同步置 `ai_first_done = True`，确保天元守卫仅在游戏真正第 0 手触发一次。
- **完整落子记录**：以轻量 JSON Lines 格式记录每盘对局的元数据、每手落子流水和对局结果，文件按 append 方式追加，支持多盘跨会话回溯。

**Non-Goals:**
- 不修改 AI 搜索引擎逻辑（C++ DLL 侧）。
- 不构建独立的棋谱回放 UI（仅提供文件格式）。
- 不改变 `logs/runtime.log` 的现有日志行为（两者独立并行）。

## Decisions

### 1. Bug Fix：单行修复，最小改动
- **位置**：[game.py L1085-1109](file:///C:/Users/19065/@me/workspace/gomoku/game.py#L1085-1109) — 三手交换 `else` 分支（AI 执白决策换手后）。
- **修改**：在 AI 决定换手（`human_is_black = False; dll.SwapHand(...)` 之后）立即追加 `ai_first_done = True`。
- **安全性**：AI 不换手时（继续执白），此行不执行，原有逻辑完全不受影响。

### 2. 游戏记录：独立模块，最小侵入
- **文件路径**：`logs/game_records.jsonl` — 与 `runtime.log` 平级，独立写入，append 模式。
- **数据结构**：
  ```json
  {"type":"game_start","game_id":"20260525_203000","human_color":"black","timestamp":"..."}
  {"type":"move","game_id":"20260525_203000","move_num":1,"x":7,"y":7,"role":"black","player":"human","timestamp":"..."}
  {"type":"game_end","game_id":"20260525_203000","winner":"white","total_moves":42,"timestamp":"..."}
  ```
- **写入接口**：
  - `init_game_record()` — 在 `asked_open` 处理完毕后调用一次，写入 `game_start` 事件并记录 `current_game_id`。
  - `log_game_move(x, y, role, player)` — 在每次 `dll.DoMove` 成功后调用，写入 `move` 事件。
  - `log_game_end(winner)` — 在胜负判定 `winner = current_role` 后调用，写入 `game_end` 事件。
- **最小侵入原则**：三个函数均为独立函数，不修改 `draw()` 或现有状态机主体逻辑，仅在调用点追加调用。

## Risks / Trade-offs

- **[Risk]** `game_records.jsonl` 文件长期追加可能变得很大（每手一行）。
  - **Mitigation**：文件为 JSONL 格式，可按对局 ID grep 过滤；文件大小增长极慢（每盘约 2~50KB），无需自动清理策略。
- **[Risk]** `log_game_move` 在五手 N 打的虚拟候选展示动画循环中被重复调用的风险。
  - **Mitigation**：`log_game_move` 仅在 `dll.DoMove` 成功后调用（真实落子），不在虚拟候选展示动画中调用。
