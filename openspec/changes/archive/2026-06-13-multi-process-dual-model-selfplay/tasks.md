## 1. 后台 Worker 托管程序开发

- [x] 1.1 编写 `ai_worker.py` 轻量级托管程序，负责加载 `GameEngine.dll`、接收 stdin 的 history 数据、本地同步棋盘，执行 AI 搜索并把着法坐标输出至 stdout。
- [x] 1.2 在 `ai_worker.py` 中实现管道异常 EOF 自动捕获安全退出逻辑，防止主进程异常退出导致显存孤儿残留。

## 2. 主子进程 IPC 通信桥接实现

- [x] 2.1 修改 `game.py`，在启动双 AI 对战时，自动读取白方物理模型路径，使用 `subprocess.Popen` 拉起 `ai_worker.py` 并维持双向管道。（已由 fix-pk-and-dual-model WorkerClient 实现）
- [x] 2.2 改造 AI 执白决策逻辑：若配置了白方物理模型，主程序不直接调用 `GetTopMoves`，而是将 history 转换为 JSON 写入子进程管道，并阻塞等待读取其落子着法。（已由 _query_white_worker_move 实现）
- [x] 2.3 确保在游戏关闭、窗口退出或重置时，安全向子进程发送退出信令并调用 `terminate` 确保 Worker 进程被销毁。（已由 finally cleanup + reset_board 实现）

## 3. 对决控制面板物理模型选择 UI 增强

- [x] 3.1 在侧边栏”白方 AI 配置卡片”上新增渲染 `模型路径显示文本` 和 `[ 浏览模型 ]` 文件选择按钮。（已存在）
- [x] 3.2 实现点击”浏览模型”按钮拉起 `tkinter.filedialog.askopenfilename` 系统窗口，允许用户选择 `.bin.gz` 模型路径并实时更新到 `GameState` 中。（已存在）
- [x] 3.3 新增”热重载”按钮以重新启动后台子进程，以便在对局中途即时载入新模型。（已存在）
