## Why

测试发现两个缺陷：

**[BUG]** 当 AI 在三手交换环节选择换手执黑后，游戏主循环中的"AI 先手天元落子"守卫逻辑（`if not ai_first_done and not human_is_black`）会在下一循环迭代中错误触发，强制在天元额外放置一颗黑子，导致五手 N 打规则从未触发。根因是三手交换完成后 `ai_first_done` 仍为 `False`，而此时 `human_is_black` 已变为 `False`，两者共同满足了本应仅在"AI 开局执黑先手"场景中触发的守卫条件。

**[FEATURE]** 当前系统缺乏每一盘对局的完整落子顺序记录，调试时只能依赖运行时日志中零散的 `print` 信息，无法在 Bug 复现或复盘时快速重建对局状态。

## What Changes

- **[BUG FIX] 三手交换后 `ai_first_done` 标志修正**：当 AI 通过三手交换换手执黑时，立即将 `ai_first_done` 置为 `True`，防止"AI先手天元"守卫逻辑在已有历史落子的情况下再次触发。
- **[FEATURE] 每盘对局落子记录（Game Record）**：在每盘对局开始时，自动将该盘的配置（交换结果、角色分配）以及落子流水（手数、坐标、角色、时间戳）以 JSON Lines 格式追加写入 `logs/game_records.jsonl` 中，便于 debug 和复盘。

## Capabilities

### New Capabilities

*(无新增 Capability specs)*

### Modified Capabilities

- `engineering`: 修复三手交换后 AI 先手守卫逻辑的状态机缺陷；新增每盘落子记录写入系统。

## Impact

- **game.py (Python UI & Main Loop)**：
  - 在三手交换完成后 AI 换手执黑的分支中，增加 `ai_first_done = True` 赋值，彻底封堵天元守卫的错误触发路径。
  - 新增游戏记录模块：`init_game_record()` 初始化当盘记录；`log_game_move()` 在每次落子后追加一行；在对局开始、落子、胜负判定时调用上述接口。
