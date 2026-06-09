## Context

当前系统中，Pygame UI（`game.py`）承载了五子棋人机对弈和训练的全部交互。由于多线程开销大，主逻辑采用 Pygame 经典单线程同步循环设计。这种设计带来了两大痛点：
1. **重型计算期界面“假死”**：在系统启动（首次加载大模型）、三手交换（双侧胜率评估）、五手 N 打（AI 计算候选/保留点）这些高负载 C++ DLL 同步计算期间，UI 界面冻结，没有任何文字提示与蒙版锁定，容易使用户以为程序卡死或引发多次重复点击。
2. **胜利与悔棋按钮重叠**：底部的胜利喜报渲染横坐标使用了全屏宽度居中，当窗口拉宽（包含 470 像素侧边栏）后，文字右半边会被固定在右下角的“悔棋”按钮发生视觉覆盖遮挡。

## Goals / Non-Goals

**Goals:**
- **视觉反馈增强**：确保系统在所有非人类可操纵的高耗时重型计算环节（启动加载、三手交换评估、五手 N 打 AI 点位选择、AI 保留点计算）中，呈现清晰的半透明锁定遮罩与状态指示文字。
- **界面避让优化**：将胜利标识以 `BOARD_AREA_W`（棋盘物理宽度，670px）为基准居中渲染，彻底避开位于 `570px ~ 650px` 的“悔棋”按钮，实现完美定位隔离。
- **防抢跑拦截**：在任何重型同步计算前后，彻底清空积压的 Pygame 鼠标点击队列，防止后台动作完成后引发玩家误落子或二次触发。

**Non-Goals:**
- 将 Pygame 对弈或 DLL 搜索引擎接口改造成多线程异步并发模型（此更改会极大颠覆现有 DLL 内存指针所有权与单线程状态机，暂不考虑）。
- 更改除 `game.py` 外的其他独立运行模块（如基于 Tkinter 的 `training_ui.py`）。

## Decisions

### 1. 胜利标识渲染定位算法微调
- **设计**：将 [game.py L910](file:///C:/Users/19065/@me/workspace/gomoku/game.py#L910) 处原本使用全窗口宽度居中 `(WIDTH - text.get_width()) // 2` 调整为使用棋盘局中 `(BOARD_AREA_W - text.get_width()) // 2`。
- **对比**：
  - *方案 A（全屏居中）*：横坐标位于 `570px` 左右，文字偏右，极易被右下角 `btn` 重叠遮挡。
  - *方案 B（移入侧边栏或顶部栏）*：打乱了原本的底部状态指示对称视觉结构。
  - *方案 C（棋盘局中，采纳）*：横坐标位于 `335px` 左右，偏向棋盘中心下方，与 `570px` 的悔棋按钮拉开 `163px` 完美距离，极具美感且零改动开销。

### 2. 引入统一的 `draw_blocking_overlay` 辅助遮罩绘制函数
- **设计**：在 `game.py` 中抽象出一个轻量、通用的锁定遮罩方法，支持参数化定制主题色（`color`）、标题（`title`）及子标题（`subtitle`）：
  ```python
  def draw_blocking_overlay(title, subtitle, color=(80, 120, 180)):
      # 1. 棋盘区半透明覆盖 (alpha=120, 黑色)
      overlay = pygame.Surface((BOARD_AREA_W, HEIGHT - STATUS_H))
      overlay.set_alpha(120)
      overlay.fill((15, 15, 15))
      screen.blit(overlay, (0, 0))
      
      # 2. 绘制圆角指示框
      box_w, box_h = 360, 100
      box_x = (BOARD_AREA_W - box_w) // 2
      box_y = (HEIGHT - STATUS_H - box_h) // 2
      box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
      pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=10)
      pygame.draw.rect(screen, color, box_rect, 3, border_radius=10)
      
      # 3. 绘制文字
      t_surf = font.render(title, True, color)
      screen.blit(t_surf, (box_x + (box_w - t_surf.get_width())//2, box_y + 20))
      s_surf = small_font.render(subtitle, True, (100, 100, 100))
      screen.blit(s_surf, (box_x + (box_w - s_surf.get_width())//2, box_y + 56))
  ```
- **复用计划**：
  - *AI 思考中*：`draw_blocking_overlay("AI 正在思考中...", "请勿落子或点击界面", (80, 120, 180))` (蓝色调)
  - *三手交换评估*：`draw_blocking_overlay("AI 正在评估三手交换决策...", "正在计算黑白双向最高胜率走法...", (180, 120, 40))` (黄色调)
  - *五手 N 打候选计算*：`draw_blocking_overlay("AI 正在选择五手N打候选点...", "正在评估并筛选平衡点位中...", (220, 80, 80))` (红色调)
  - *五手 N 打保留点计算*：`draw_blocking_overlay("AI 正在评估保留点...", "正在计算对白棋最有利的候选点位...", (80, 120, 180))` (蓝色调)

### 3. 游戏加载画面渲染机制
- **设计**：在 Pygame `screen` 创建后、`env` 引擎与模型权重/模型路径加载前，优先运行绘制一个全屏的精致 Wood 背景卡片，告知用户神经网络推理加速组件加载中，并执行强制视图翻转：
  ```python
  screen.fill((211, 159, 89)) # 原 WOOD_BG 棋盘色
  # 绘制文字与载入提示
  # pygame.display.flip()
  ```
  在每个大模型加载函数（如 `load_model_weights`、`load_kata_model`）执行前，动态重绘并提示具体进度。

### 4. 重载队列清空拦截器
- **设计**：在高强度的计算评估之后，立即调用 `pygame.event.clear(pygame.MOUSEBUTTONDOWN)` 和 `pygame.event.clear(pygame.MOUSEBUTTONUP)`，避免操作系统的消息泵在主线程卡顿期积压的二次点击事件污染下一回合落子。

## Risks / Trade-offs

- **[Risk]** 同步绘制由于加载时可能未完全初始化 Pygame 部分组件导致闪退。
  - **Mitigation**：必须在 `pygame.init()` 及 `pygame.font.init()` 顺利运行、字体加载无误（霞鹜真楷）后，且在 `screen = pygame.display.set_mode()` 赋值完成后再进行加载屏绘制。
- **[Risk]** 遮罩绘制在 `draw()` 返回之前未生效。
  - **Mitigation**：将 `draw_blocking_overlay` 的具体触发逻辑统一塞入 `draw()` 的最末尾，根据状态变量（`ai_is_searching` 或新增的交换/N打计算状态标志）决定是否叠加绘制，避免与原棋盘像素发生顺序渲染紊乱。
