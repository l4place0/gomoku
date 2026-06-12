# 工程侧 (Engineering)

## Purpose
保证五子棋引擎系统的完整性，支持主程序的正常运行、高效的本地构建与灵活调试开发。虽然工程侧的要求不直接决定棋力的上下限，但为复杂的搜子剪枝、开局库及 KataGomo 推理提供了最坚固的基础设施支撑。

---

## 1. 构建系统

### CMake 配置
- **文件**: [CMakeLists.txt](file:///C:/Users/19065/@me/workspace/gomoku/CMakeLists.txt)
- **标准**: C++17
- **两种构建模式**:

| 模式 | 开关 | 产物 | 依赖 |
|------|------|------|------|
| 基础 | 默认 | `GameEngine.dll` | MSVC, KataGomo/cpp (禁手源码) |
| CUDA | `-DENABLE_KATAGOMO_CUDA=ON` | `GameEngine.dll` + `katago.exe` | + CUDA Toolkit, cuDNN, zlib |

- 基础模式仅编译 `ForbiddenPointFinder.cpp`（禁手判定），不链接 KataGomo 完整源码
- CUDA 模式编译 KataGomo 全部 ~70 个源文件为 `katagomo_core` 静态库

### 构建脚本
- **文件**: [build.bat](file:///C:/Users/19065/@me/workspace/gomoku/build.bat)
- 自动检测可用的 CMake Generator（Ninja → NMake → MinGW → VS 2022）
- CUDA 构建强制使用 VS Generator
- 构建冲突时自动清理 `build/` 目录

---

## 2. DLL 接口

### 导出函数
- **声明**: [GameEngineDLL.h](file:///C:/Users/19065/@me/workspace/gomoku/GameEngineDLL.h)
- **实现**: [GameEngineDLL.cpp](file:///C:/Users/19065/@me/workspace/gomoku/GameEngineDLL.cpp)

共 14 个 C 导出函数，是 Python 与 C++ 之间的**全部通信通道**：

| 函数 | 用途 |
|------|------|
| `GetGameEngine` | 获取单例引擎指针 |
| `LoadModelWeights` | 加载轻量评估权重 |
| `LoadKataModel` | 加载 KataGomo 神经网络模型 |
| `SetKataEnabled` | 启用/禁用 KataGomo |
| `SetKataSearchParams` | 设置 visits/seconds/policyBlend/valueBlend |
| `IsKataReady` | 查询 KataGomo 是否就绪 |
| `SwapHand` | 换手 |
| `CheckWin` | 检测某位置是否形成五连 |
| `DoMove` | 落子 |
| `UndoMove` | 撤销落子 |
| `GetTopMoves` | 获取排序后的推荐着法列表 |
| `GetLastSearchLogJson` | 获取最近一次搜索的 JSON 日志 |
| `GetBoardState` | 获取棋盘状态数组 |
| `ReleaseEngine` | 释放引擎（当前为空操作） |

### Python 侧封装
- **文件**: [game.py](file:///C:/Users/19065/@me/workspace/gomoku/game.py) L1-73
- 使用 `ctypes.CDLL` 加载 DLL
- 通过 `getattr(dll, name, None)` 可选绑定（KataGomo 接口可能不存在）
- `AIMove` 结构体: `{x: int, y: int, score: int}`

---

## 3. 游戏流程

### 状态机 (隐式)
- **文件**: [game.py](file:///C:/Users/19065/@me/workspace/gomoku/game.py) 主循环 L786-1075
- 用全局 flag 变量控制流程阶段：

```
启动 → 开局换手? (asked_open)
          │
          ▼
     AI先手? → 天元落子
          │
          ▼
     三手交换? (asked_three, 仅人类执白时触发)
          │
          ▼
     五手N打 (five_asked, 第5手黑棋时触发)
       ├── 人类执黑: 人选N个候选 → AI保留1个
       └── AI执黑: AI选N个低影响候选 → 人保留1个
          │
          ▼
     正常对弈循环 (人/AI轮流)
          │
          ▼
     胜负判定 → 结束
```

### 关键全局变量
| 变量 | 类型 | 用途 |
|------|------|------|
| `history` | `list[(x,y,role)]` | 落子历史 |
| `current_role` | `int` | 当前执子方 (0=黑, 1=白) |
| `human_is_black` | `bool` | 人类是否执黑 |
| `winner` | `int\|None` | 胜者 |
| `virtual_candidates` | `list[(x,y)]` | 五手N打候选位置 |
| `five_move_candidate_count` | `int` | N打的N值 (2~5, 默认3) |

---

## 4. UI 界面

### Pygame 渲染
- **文件**: [game.py](file:///C:/Users/19065/@me/workspace/gomoku/game.py)
- **窗口尺寸**: `BOARD_AREA_W + SIDEBAR_W (470)` × `MARGIN + CELL*15 + STATUS_H`
- **字体**: `LXGWZhenKaiGB-Regular.ttf` (霞鹜真楷)

### 界面组成
| 区域 | 功能 |
|------|------|
| 棋盘区 | 15×15 木纹棋盘，棋子渐变效果，最后落子虚线高亮 |
| 侧边栏 | AI 分析面板：搜索统计、KataGomo 状态、Top10 候选、搜索历史 |
| 底部栏 | 手数、当前轮次、五手N打提示、悔棋按钮 |
| 弹窗 | `confirm()` 可拖拽确认对话框 |

### 训练面板
- 内嵌简单训练参数编辑 + selfplay/train/export 按钮
- 也可通过 `open_training_backend_ui()` 启动独立的 [training_ui.py](file:///C:/Users/19065/@me/workspace/gomoku/training_ui.py)

---

## 5. 日志系统

### 搜索日志
- **路径**: `logs/search_logs.jsonl`
- **格式**: 每行一个 JSON，记录完整的搜索信息
- **字段**: searchId, role, turn, candidateCount, targetDepth, reachedDepth, timedOut, totalMs, alphaBetaMs, kataMs, searchNodes, hashHits, hashHitRate, betaCuts, kataEnabled/Ready/Applied, top10 moves 详情
- **生成**: C++ 侧 `buildLastSearchLogJson()` 构造，Python 侧 `capture_search_log()` 获取并写入文件
- **控制**: UI 面板可切换 "AI only" / "All calls" 模式

---

## 6. 文件清单

```
gomoku/
  game.py                    # Python 主程序 (1075行)
  GameEngine.h               # C++ 引擎核心 (900行)
  GameEngineDLL.cpp           # DLL 导出实现 (135行)
  GameEngineDLL.h             # DLL 导出声明 (43行)
  KataInferenceAdapter.cpp    # KataGomo 适配 (292行)
  KataInferenceAdapter.h      # 适配器接口 (66行)
  KataSelfplayMain.cpp        # selfplay 入口 (49行)
  CMakeLists.txt              # CMake 构建配置 (243行)
  build.bat                   # Windows 构建脚本 (51行)
  training_ui.py              # 训练管理界面 (独立进程)
  model_weights.txt           # 评估权重配置
  LXGWZhenKaiGB-Regular.ttf   # UI 字体
  GameEngine.dll              # 构建产物
```

---
## Requirements
### Requirement: Pygame 侧边栏开局风格配置按钮
系统 SHALL 在 Pygame 主窗口的侧边栏上，渲染并集成一个开局风格选择按钮组。该按钮组 SHALL 支持在三种对局风格（“传统稳健 / 创新奇招 / 随机混合”）之间点击切换。系统 SHALL 在玩家点击不同按钮时，立即更新全局开局检索风格，并给予界面高亮反馈。

#### Scenario: 点击切换为创新风格按钮
- **WHEN** 玩家在侧边栏点击“创新奇招”按钮
- **THEN** 系统 SHALL 立即将全局开局风格 `opening_style` 切换为 `novelty` 并重新高亮该按钮

### Requirement: 三阶段对局实时日志与状态展示
系统 SHALL 在底部的状态显示栏与侧边栏的 AI 分析面板中，高亮显示当前的对局决策阶段：
- 当从开局库中秒回时，显示“决策：开局库 (Book)”。
- 当由 KataGomo 推理时，显示“决策：MCTS (神经网络)”。
- 当由 MiniMax 搜索时，显示“决策：MiniMax (AB 搜索)”。
- 当触发 VCF 必杀时，显示“决策：VCF 绝对算杀”。

#### Scenario: 对局显示 MCTS 神经网络决策阶段
- **WHEN** 当前对局由 KataGomo 执行 MCTS 搜索并落子
- **THEN** 系统底部的状态显示栏与侧边栏的 AI 分析面板中 SHALL 显示“决策：MCTS (神经网络)”

### Requirement: 三手交换决策阻断与正确时序执行
系统在第 3 手落子后，SHALL 拦截并阻断 AI 普通回合的抢跑落子行为，确保系统状态机能顺利推进进入下一轮循环的开头，从而 100% 正确触发三手交换决策逻辑（无论人类是执黑还是执白）。

#### Scenario: 人类执黑时成功触发三手交换决策
- **WHEN** 人类执黑放置第 3 手棋子，使得 `len(history) == 3` 且 `current_role` 变为 AI (执白)
- **THEN** AI 普通回合 SHALL 在当前循环中被拦截并跳过，使循环进入下一轮开头，顺利触发 AI 的三手交换相对评分评估

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

### Requirement: 游戏启动加载期状态提示
为了避免系统启动初始化以及加载大型神经网络模型和权重时出现主窗口黑屏/假死感，系统 SHALL 在主窗口 Pygame 初始化（`pygame.display.set_mode`）完成后，立即在主屏上绘制高辨识度的“启动加载页面”及实时文字进度提示，且 SHALL 在加载完成后自动进入正式游戏主界面。

#### Scenario: 游戏启动时显示引擎与大模型载入状态
- **WHEN** 游戏主程序被启动且尚未完成模型加载
- **THEN** 系统 SHALL 在 Pygame 窗口中渲染木纹背景与醒目的标题，展示“正在载入大模型与 CUDA 加速组件...”的文案提示，并调用 `pygame.display.flip()` 更新视图，随后再触发底层的 C++ DLL 模型载入

### Requirement: AI 非人类可执行动作环节视觉锁定与提示蒙版
在所有非人类玩家可执行且同步耗时的动作环节（包括三手交换 AI 决策评估期、五手 N 打 AI 执黑筛选候选点期、五手 N 打 AI 执白评估保留点期），系统 SHALL 在棋盘区（`BOARD_AREA_W` 宽度范围内）渲染一层黑色的半透明遮罩图层，并在其中央绘制圆角锁定对话框，提供与当前环节完全匹配的高辨识度提示文本，同时阻断用户在此期间的任何落子与面板交互操作。

#### Scenario: AI 执白进行三手交换双向胜率评估提示
- **WHEN** 对局进入第 3 手落子后且 AI 执白评估三手交换相对胜率
- **THEN** 系统 SHALL 在棋盘区绘制半透明遮罩，并渲染醒目的“AI 正在评估三手交换决策...”以及“正在计算黑白双向最高胜率走法...”提示信息卡片，阻止玩家误操作

#### Scenario: AI 执黑进行五手 N 打平衡候选点计算提示
- **WHEN** 对局进入第 4 手落子后且 AI 执黑计算并筛选 N 个低影响的平衡候选落子点
- **THEN** 系统 SHALL 在棋盘区绘制半透明遮罩，并渲染醒目的“AI 正在选择五手N打候选点...”以及“正在评估并筛选平衡点位中...”提示信息卡片

#### Scenario: AI 执白进行五手 N 打人类候选点保留评估提示
- **WHEN** 人类玩家作为黑方提供 N 个平衡候选点且 AI 执白计算并保留最有利的一点
- **THEN** 系统 SHALL 在棋盘区绘制半透明遮罩，并渲染醒目的“AI 正在评估保留点...”以及“正在计算对白棋最有利的候选点位...”提示信息卡片

### Requirement: 胜利标识安全避让定位
当游戏判定胜负（黑子或白子胜利）时，系统渲染的胜利标识文案 SHALL 以棋盘物理宽度区域 `BOARD_AREA_W` 为对齐基准进行水平居中对齐，从而在视觉上完全避让并独立于位于右下角固定位置（`BOARD_AREA_W-100` 起始宽度）的“悔棋”按钮，防止任何文字重叠和视觉遮挡。

#### Scenario: 胜利提示文字与悔棋按钮安全避让渲染
- **WHEN** 游戏判定有玩家胜出，且 `winner` 变量不为 None
- **THEN** 系统 SHALL 使用 `((BOARD_AREA_W-text.get_width())//2, HEIGHT-STATUS_H+20)` 的物理坐标将胜利喜报文字渲染至底部状态栏，使得其显示区域完全处于 `0 ~ 670px` 棋盘底部的中央，与 `570px` 处的悔棋按钮拉开至少 160 像素的物理安全间距

### Requirement: 三手交换双向相对评分展示
在第 3 手落子后的三手交换抉择关卡，Pygame 侧边栏日志与控制台 SHALL 完整记录并展示双向相对估算分数：不交换保持白棋得分 (`score_white`) 与交换换手执黑得分 (`score_black`)，确保决策过程透明可视。

#### Scenario: 成功记录与展示双向估值日志
- **WHEN** AI 执白在第 3 手评估交换决策
- **THEN** 系统 SHALL 打印 `score_white` 与 `score_black`，并在 UI 日志中展示当前估分详情


---

## ADDED Requirements

### Requirement: 对决控制台多模型路径文件选择 UI
在双 AI 对决控制台中，系统 SHALL 为黑白两方 AI 分别渲染“模型权重文件选择卡片”。卡片包含当前已载入的模型路径显示文本，以及一个 `[ 浏览模型 ]` 按钮。点击按钮后，系统 SHALL 弹出系统文件选择窗允许用户选择 `.bin.gz` 模型路径，并更新至对应 AI 状态属性中。

#### Scenario: 浏览并选择新模型路径
- **WHEN** 玩家点击白方 AI 卡片中的“浏览模型”按钮并成功选择 `models/custom.bin.gz`
- **THEN** 卡片上的显示路径文本实时渲染更新，并同步至 `gs.ai_white_cfg["model_path"]` 中。
