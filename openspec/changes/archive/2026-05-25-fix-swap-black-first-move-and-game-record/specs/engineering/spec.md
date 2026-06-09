## ADDED Requirements

### Requirement: 三手交换后状态机完整性保障
当游戏执行三手交换（无论是人类或 AI 换手执黑），系统 SHALL 确保 `ai_first_done` 标志在三手交换完成后被正确置为 `True`，使得"AI先手天元落子"守卫逻辑（`if not ai_first_done and not human_is_black`）在已有历史落子的情况下不会重复触发，确保五手 N 打规则能在正确时机被激活。

#### Scenario: AI 三手交换换手执黑后不触发天元守卫
- **WHEN** AI 在三手交换环节选择换手执黑（`human_is_black` 变为 `False`，`ai_first_done` 在换手前为 `False`）
- **THEN** 系统 SHALL 立即将 `ai_first_done` 置为 `True`，使得下一个主循环迭代中"AI先手天元"守卫条件不再满足，游戏流程正确推进至人类（白方）的第4手，进而在第4手后正常触发五手 N 打规则

#### Scenario: 五手 N 打规则在三手交换后正确触发
- **WHEN** AI 已换手执黑，人类（白方）落下第4颗棋子，`len(history) == 4` 且 `current_role == BLACK`
- **THEN** 系统 SHALL 正常触发五手 N 打逻辑，AI 执黑正确进入"提供 N 个候选点"分支（`else` 分支），而非直接落子

### Requirement: 每盘对局落子记录
系统 SHALL 在每盘对局开始时，在 `logs/game_records.jsonl` 文件中追加一条 JSON 对象作为本盘对局记录头，包含对局 ID（基于时间戳）、人类颜色分配、三手交换结果、对局开始时间戳等元数据。系统 SHALL 在每一次实际落子（包括人类落子、AI 落子、五手 N 打落子）后，向该盘记录追加一条包含手数、棋盘坐标 (x, y)、角色（black/white）、落子方（human/ai）、时间戳的 JSON Lines 记录。对局结束（胜负判定）时，系统 SHALL 在该文件中追加一条结束行，记录胜者与总手数。

#### Scenario: 对局开始时写入对局元数据
- **WHEN** 一盘新对局开始（`asked_open` 弹窗处理完毕且已确定人类执黑/执白）
- **THEN** 系统 SHALL 在 `logs/game_records.jsonl` 追加一行包含 `type: "game_start"`、`game_id`、`human_color`、`timestamp` 字段的 JSON 对象

#### Scenario: 落子后记录到落子流水
- **WHEN** 任意一方成功落子（`dll.DoMove` 返回 True）
- **THEN** 系统 SHALL 向 `logs/game_records.jsonl` 追加一行包含 `type: "move"`、`game_id`、`move_num`（第几手）、`x`、`y`、`role`（black/white）、`player`（human/ai）、`timestamp` 字段的 JSON 对象

#### Scenario: 对局结束时记录胜负结果
- **WHEN** 游戏判定 `winner is not None`
- **THEN** 系统 SHALL 向 `logs/game_records.jsonl` 追加一行包含 `type: "game_end"`、`game_id`、`winner`（black/white）、`total_moves`、`timestamp` 字段的 JSON 对象
