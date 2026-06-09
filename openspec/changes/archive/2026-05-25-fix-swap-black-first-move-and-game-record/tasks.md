## 1. [BUG FIX] 三手交换后 ai_first_done 状态修正

- [x] 1.1 在 `game.py` 三手交换 `else` 分支（AI决定换手执黑）中，在 `dll.SwapHand(env, human_is_black)` 调用之后立即追加 `ai_first_done = True`，防止"AI先手天元"守卫在已有历史落子时错误触发。
- [x] 1.2 编写对应的逻辑验证注释，说明此修复的作用与时序前提。

## 2. [FEATURE] 每盘落子记录模块

- [ ] 2.1 在 `game.py` 中定义全局变量 `current_game_id = None` 与 `GAME_RECORD_PATH`（指向 `logs/game_records.jsonl`）。
- [ ] 2.2 实现 `init_game_record()` 函数：以 `YYYYMMDD_HHMMSS` 格式生成 `game_id`，写入 `game_start` JSON Lines 记录（含 `human_color`、`timestamp`）。
- [ ] 2.3 实现 `log_game_move(x, y, role, player)` 函数：追加写入 `move` JSON Lines 记录（含 `move_num = len(history)`、坐标、角色、落子方、时间戳）。
- [ ] 2.4 实现 `log_game_end(winner)` 函数：追加写入 `game_end` JSON Lines 记录（含胜者颜色字符串、`total_moves`、时间戳）。
- [ ] 2.5 在 `asked_open` 弹窗处理完毕后调用 `init_game_record()`，记录本盘元数据。
- [ ] 2.6 在游戏主循环中所有 `dll.DoMove` 成功落子处（AI 开局天元、人类普通落子、AI 普通落子、五手 N 打落子）追加调用 `log_game_move()`。
- [ ] 2.7 在所有 `winner = current_role` 或 `winner = BLACK/WHITE` 赋值处追加调用 `log_game_end(winner)`。

## 3. 功能验证

- [ ] 3.1 重现 Bug：模拟人类先手开局 → AI 三手交换换手执黑 → 验证第 4 手后五手 N 打正确触发（AI 提供候选点），天元不再多落一子。
- [ ] 3.2 验证落子记录：运行完整对局后，检查 `logs/game_records.jsonl` 是否包含正确的 `game_start`、连续 `move` 记录及 `game_end`；手数、坐标、角色均与实际对局一致。
- [ ] 3.3 运行 Python 语法检查确认无语法错误。
