## Context

当前根目录包含 20+ Python 文件、C++ 源码、编译产物（`.so`/`.dll`）、17MB 字体、临时 JSON 报告，三个系统（游戏引擎、ML 训练、Web 控制台）平铺在同一层级。`GameEngine.so` 虽在 `.gitignore` 中但仍被 git track。代码通过 `BASE_DIR = Path(__file__).resolve().parent` 拼接路径，重组需同步更新所有路径引用。

## Goals / Non-Goals

**Goals:**
- 按系统职责拆分为 `game/`、`ml/`、`tools/`、`engine/` 四个目录
- 清理根目录临时文件和编译产物
- 修复 `.gitignore`，取消 track 大文件
- 分阶段执行，每阶段可独立验证
- 重组前先写安全网测试，确保路径变更不引入回归

**Non-Goals:**
- 不重构 `game.py` 内部结构（2290 行，稳定）
- 不改动 `KataGomo/` submodule 内部
- 不修改游戏逻辑或 ML 算法
- 不拆分 `game.py` 为多个子模块

## Decisions

### 1. 目录结构：四包 + 共享 submodule

```
gomoku/
├── game/          # 游戏引擎 GUI + 游戏逻辑
├── ml/            # ML 训练管线 + Web 控制台
├── tools/         # 跨系统公共引擎绑定
├── engine/        # C++ 源码 + 构建
├── KataGomo/      # git submodule (共享依赖)
├── tests/
├── docs/
└── pyproject.toml
```

**理由**：三个系统的边界已经清晰，`tools/` 作为 GameEngine Python 绑定层被 `game/` 和 `ml/` 共享。KataGomo 同时被游戏运行时（DNN 推理）和 ML 训练使用，必须留在根目录作为共享依赖。

**替代方案**：不设 `tools/`，将 `ai_worker.py` 归入 `game/`、`headless_runner.py` 归入 `ml/`。缺点是两者都依赖 GameEngine.so 的 ctypes 封装，会有重复。

### 2. webui/ 并入 ml/ 作为子目录

`webui/app.py` 是 `mlevo_cli.py` 的 thin wrapper，并入 `ml/webui/` 体现其归属。

**理由**：Web UI 不是独立系统，它是 ML 训练管线的前端。

### 3. 路径策略：基于包根目录的相对路径

所有文件路径引用改为基于**包根目录**（`game/`、`ml/`、`tools/`）而非项目根目录。每个包设置自己的 `BASE_DIR`。

```python
# game/game.py
BASE_DIR = Path(__file__).resolve().parent  # game/

# ml/automl_cli.py
BASE_DIR = Path(__file__).resolve().parent  # ml/

# tools/ai_worker.py
BASE_DIR = Path(__file__).resolve().parent  # tools/
```

KataGomo 路径统一通过 `Path(__file__).resolve().parent.parent / "KataGomo"` 引用。

### 4. 分阶段执行：先安全网，再移动，最后验证

- **Phase 0**：写安全网测试（模块可达性、文件存在性、子进程调用、C++ 构建）
- **Phase 1**：清理临时文件 + 修复 `.gitignore` + 取消 track `GameEngine.so`
- **Phase 2**：创建目录结构 + 逐批移动文件 + 更新 import/路径
- **Phase 3**：运行全量测试 + 功能验证 + 提交

### 5. C++ 引擎：源码和构建文件一起移

将 `GameEngineDLL.*`、`KataInferenceAdapter.*`、`KataSelfplayMain.cpp`、`GameEngine.h`、`CMakeLists.txt`、`build.bat`、`build.sh` 移入 `engine/`，源码放 `engine/src/`。

**理由**：CMakeLists.txt 需要同步更新路径，但一次性完成比分散更安全。`GameEngine.so` 编译产物留在根目录（被 `.gitignore` 忽略），因为它被 `tools/ai_worker.py` 通过绝对路径加载。

## Risks / Trade-offs

- **[import 路径遗漏]** → 安全网测试覆盖所有模块可达性，Phase 3 全量测试验证
- **[subprocess 路径断裂]** → 安全网测试覆盖 CLI 子进程调用
- **[CMakeLists.txt 路径错误]** → 安全网测试验证 cmake 配置成功
- **[git history 扁平化]** → 使用 `git mv` 保留文件历史追踪
- **[GameEngine.so 路径变化]** → `tools/ai_worker.py` 使用 `parent.parent` 定位根目录的 `.so` 文件
