## 1. 基础架子与 CLI 参数解析实现

- [x] 1.1 创建 `headless_runner.py` 基础框架并导入 `ctypes`、`json`、`subprocess` 等依赖，严禁导入 `pygame`。
- [x] 1.2 使用 `argparse` 设计并实现完整的命令行接口参数解析（`--black-model`、`--white-model`、`--games`、`--concurrency`、`--output` 等）。

## 2. 状态机裁判与 DLL / Worker 桥接实现

- [x] 2.1 主进程加载 `GameEngine.dll`，在 `headless_runner.py` 中初始化基础黑方博弈引擎（加载主物理模型）。
- [x] 2.2 实现白方子进程拉起及 IPC JSON 管道协议双向绑定（输入 history，输出着法坐标与 MCTS visits 配置）。
- [x] 2.3 编写无头裁判状态机：支持完整的开局库秒查、自动三手交换判定（根据胜率评分对比自动执行）、以及五手N打候选选择。
- [x] 2.4 实现主循环的终局判定（`CheckWin`）、和异常 `finally` 块下的子进程强制清理 `terminate` 机制。

## 3. 标准化 JSON 赛段报告输出

- [x] 3.1 实现每场对局完成后对局数据（获胜方、总步数、落子时间、落子历史路径）的内存级记录。
- [x] 3.2 实现整场赛段（Match）完结时，汇总胜率数据、统计分析数据并将其以结构化 JSON 的格式输出到指定的 `--output` 路径下。
