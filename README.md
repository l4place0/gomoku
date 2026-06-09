# Gomoku

这是一个 15x15 五子棋项目，包含 Pygame 图形界面、C++ 搜索引擎 DLL、轻量模型权重评估，以及可选的 KataGomo/CUDA 推理和训练环境。

## 先看结论

如果只是运行游戏，对方需要恢复：

- Python + Pygame
- C++ 构建工具
- `KataGomo/` 源码目录
- `GameEngine.dll`
- `LXGWZhenKaiGB-Regular.ttf`
- `model_weights.txt`

如果要完整恢复训练和 CUDA/KataGomo 推理环境，还需要：

- NVIDIA 驱动
- CUDA Toolkit
- cuDNN
- zlib
- PyTorch
- KataGomo 模型文件 `KataGomo/models/model.bin.gz`
- 训练数据目录 `KataGomo/training_data/`，如需延续已有训练

不要把 `.venv/`、`build/`、`.git/`、训练数据、CUDA/cuDNN DLL 直接塞进源码包。它们应由接收方按本文重新下载或单独恢复。

## 项目文件

核心文件：

- `game.py`：游戏主界面，使用 `ctypes` 调用 `GameEngine.dll`。
- `GameEngine.h`：棋盘状态、禁手、搜索、评估、权重模型和 KataGomo 融合逻辑。
- `GameEngineDLL.cpp` / `GameEngineDLL.h`：DLL 导出接口。
- `KataInferenceAdapter.cpp` / `KataInferenceAdapter.h`：KataGomo 推理适配层。
- `KataSelfplayMain.cpp`：KataGomo selfplay 可执行程序入口。
- `CMakeLists.txt`：CMake 构建配置。
- `build.bat`：Windows 一键构建脚本。
- `model_weights.txt`：轻量线性评估权重。
- `LXGWZhenKaiGB-Regular.ttf`：Pygame 界面字体。
- `training_ui.py`：训练管理界面。

生成或外部恢复的文件：

- `GameEngine.dll`：构建后生成，必须和 `game.py` 在同一目录。
- `KataGomo/`：外部源码目录，构建时需要。
- `include/cuda/`：可选，本项目约定的本地 cuDNN 解压目录。
- `KataGomo/models/model.bin.gz`：可选，KataGomo 推理模型。
- `KataGomo/training_data/`：可选，训练数据，通常非常大。

## 官方下载入口

这些链接是恢复环境时使用的上游来源：

- Python for Windows: <https://www.python.org/downloads/windows/>
- CMake: <https://cmake.org/download/>
- Visual Studio Build Tools: <https://visualstudio.microsoft.com/downloads/>
- Git for Windows: <https://gitforwindows.org/>
- uv: <https://docs.astral.sh/uv/getting-started/installation/>
- PyTorch: <https://pytorch.org/get-started/locally/>
- CUDA Toolkit: <https://developer.nvidia.com/cuda-downloads>
- cuDNN: <https://developer.nvidia.com/cudnn>
- cuDNN Windows 安装说明: <https://docs.nvidia.com/deeplearning/cudnn/installation/latest/windows.html>
- KataGomo: <https://github.com/hzyhhzy/KataGomo>
- zlib: <https://www.zlib.net/>，也可用 Scoop 或 vcpkg 安装。

## 目录布局

恢复后的推荐目录结构：

```text
gomoku/
  README.md
  .gitignore
  CMakeLists.txt
  build.bat
  game.py
  training_ui.py
  GameEngine.h
  GameEngineDLL.cpp
  GameEngineDLL.h
  KataInferenceAdapter.cpp
  KataInferenceAdapter.h
  KataSelfplayMain.cpp
  model_weights.txt
  LXGWZhenKaiGB-Regular.ttf
  GameEngine.dll                  # 构建后生成
  .venv/                          # 本地创建，不随源码传输
  build/                          # 本地生成，不随源码传输
  KataGomo/
    cpp/
    python/
    scripts/
      gomocup/default_gtp.cfg
      engine/katago.exe           # CUDA selfplay 构建后生成
    models/model.bin.gz           # 可选模型
    training_data/                # 可选训练数据
  include/
    cuda/
      include/cudnn.h
      lib/x64/cudnn.lib
      bin/x64/cudnn64_9.dll
```

## 1. 安装基础工具

安装 Python：

1. 从 <https://www.python.org/downloads/windows/> 下载 Windows 64-bit installer。
2. 安装时勾选 `Add python.exe to PATH`。
3. 验证：

```powershell
python --version
pip --version
```

安装 C++ 构建工具：

1. 从 <https://visualstudio.microsoft.com/downloads/> 下载 `Build Tools for Visual Studio 2022`。
2. 安装工作负载 `Desktop development with C++`。
3. 确认包含 MSVC v143、Windows 10/11 SDK、C++ CMake tools。
4. 验证：

```powershell
cl
```

安装 CMake：

1. 从 <https://cmake.org/download/> 下载 Windows x64 Installer。
2. 安装时选择把 CMake 加入 PATH。
3. 验证：

```powershell
cmake --version
```

安装 Git：

1. 从 <https://gitforwindows.org/> 下载并安装。
2. 验证：

```powershell
git --version
```

## 2. 恢复 Python 虚拟环境

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install pygame
```

如果要使用训练界面：

```powershell
pip install psutil numpy
```

如果要训练模型，再按 <https://pytorch.org/get-started/locally/> 选择 Windows、pip、对应 CUDA 或 CPU 版本安装 PyTorch。示例 CPU 版：

```powershell
pip install torch torchvision torchaudio
```

安装后验证：

```powershell
python -c "import pygame; print('pygame ok')"
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

`training_ui.py` 默认的 Python 命令是 `uv run python`。如果接收方不使用 uv，可以在训练界面里把 `Python` 字段改成：

```text
python
```

也可以安装 uv：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv --version
```

## 3. 恢复 KataGomo 源码

本项目构建时会引用 `KataGomo/cpp`，因此接收方如果要重新构建 `GameEngine.dll`，需要恢复 `KataGomo/`。

推荐使用 Git：

```powershell
git clone -b Gom2024 https://github.com/hzyhhzy/KataGomo.git KataGomo
```

如果不能使用 Git，可以从 <https://github.com/hzyhhzy/KataGomo> 下载源码压缩包，解压后把目录重命名为：

```text
KataGomo
```

放置位置必须是项目根目录下：

```text
gomoku/KataGomo/cpp
gomoku/KataGomo/python
gomoku/KataGomo/scripts
```

验证：

```powershell
Test-Path .\KataGomo\cpp
Test-Path .\KataGomo\scripts\gomocup\default_gtp.cfg
```

如果 `default_gtp.cfg` 不存在，先不要启用 KataGomo 推理；游戏仍会退回到内置搜索。

## 4. 构建基础 GameEngine.dll

基础构建不启用 CUDA，但仍需要 `KataGomo/cpp` 源码目录。

```powershell
.\build.bat
```

成功后应看到根目录生成：

```text
GameEngine.dll
```

验证：

```powershell
Test-Path .\GameEngine.dll
```

然后运行游戏：

```powershell
python game.py
```

## 5. 恢复轻量评估权重

轻量权重文件放在项目根目录：

```text
gomoku/model_weights.txt
```

格式是 `key=value`：

```text
blend=0.70
own_scale=1.00
enemy_scale=1.08
center_weight=8
neighbor_weight=18
pattern.five=100000
pattern.four=12500
pattern.blocked_four=6200
pattern.three=1450
pattern.blocked_three=620
pattern.two=260
pattern.blocked_two=120
```

`game.py` 启动时会自动尝试加载该文件。文件缺失或加载失败时，程序会使用内置规则评估。

## 6. 恢复 CUDA/cuDNN/zlib 完整环境

只有以下场景需要这一节：

- 使用 `-DENABLE_KATAGOMO_CUDA=ON` 构建。
- 运行 KataGomo 模型推理。
- 使用 `training_ui.py` 做 GPU selfplay 或训练。

安装 NVIDIA 驱动：

1. 安装与显卡匹配的 NVIDIA Game Ready / Studio / Data Center 驱动。
2. 验证：

```powershell
nvidia-smi
```

安装 CUDA Toolkit：

1. 从 <https://developer.nvidia.com/cuda-downloads> 下载 Windows x86_64 安装器。
2. 建议安装到默认目录，例如：

```text
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1
```

3. 验证：

```powershell
nvcc --version
```

安装 cuDNN：

1. 从 <https://developer.nvidia.com/cudnn> 下载与 CUDA 版本匹配的 `cuDNN Backend for Windows`。
2. 本仓库当前本地环境使用过 `cudnn-windows-x86_64-9.21.1.3_cuda13-archive.zip` 这一类 CUDA 13 包。接收方不必完全相同，但 cuDNN 的 CUDA 大版本应和 CUDA Toolkit 对齐。
3. 解压后把内容放到项目内：

```text
gomoku/include/cuda/include/cudnn.h
gomoku/include/cuda/lib/x64/cudnn.lib
gomoku/include/cuda/bin/x64/cudnn64_9.dll
```

也就是说，`CUDNN_ROOT_DIR` 应指向：

```text
gomoku/include/cuda
```

验证：

```powershell
Test-Path .\include\cuda\include\cudnn.h
Test-Path .\include\cuda\lib\x64\cudnn.lib
Test-Path .\include\cuda\bin\x64\cudnn64_9.dll
```

安装 zlib：

推荐 Scoop：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
irm get.scoop.sh | iex
scoop install zlib
```

CMake 会优先尝试：

```text
%USERPROFILE%\scoop\apps\zlib\current
```

如果不用 Scoop，也可以用 vcpkg 安装 zlib，然后构建时传入 `ZLIB_ROOT`：

```powershell
.\build.bat -DENABLE_KATAGOMO_CUDA=ON -DZLIB_ROOT=C:\path\to\zlib
```

## 7. 构建 CUDA/KataGomo 版本

确认已具备：

```text
KataGomo/cpp
include/cuda/include/cudnn.h
include/cuda/lib/x64/cudnn.lib
CUDA Toolkit
zlib
```

构建：

```powershell
.\build.bat -DENABLE_KATAGOMO_CUDA=ON -DCUDNN_ROOT_DIR="$PWD\include\cuda"
```

构建成功后应得到：

```text
GameEngine.dll
KataGomo/scripts/engine/katago.exe
```

CMake 会把需要的 CUDA/cuDNN/zlib 运行时 DLL 复制到：

```text
gomoku/
gomoku/KataGomo/scripts/engine/
```

如果运行时报缺 DLL，手动检查这些文件是否存在：

```text
cudart64_*.dll
cublas64_*.dll
cublasLt64_*.dll
cudnn64_9.dll
cudnn_*.dll
zlib.dll
```

## 8. 恢复 KataGomo 模型

游戏会尝试加载：

```text
KataGomo/models/model.bin.gz
KataGomo/scripts/gomocup/default_gtp.cfg
```

模型来源有三种：

- 从你已有环境中单独拷贝 `KataGomo/models/model.bin.gz`。
- 从 KataGomo/Gom2024 相关发布或服务获取兼容模型。
- 使用本项目训练流程导出模型。

放置路径必须是：

```text
gomoku/KataGomo/models/model.bin.gz
```

验证：

```powershell
Test-Path .\KataGomo\models\model.bin.gz
Test-Path .\KataGomo\scripts\gomocup\default_gtp.cfg
```

没有这个模型时，游戏仍可运行，只是不会启用 KataGomo 推理。

## 9. 恢复训练环境

启动训练管理界面：

```powershell
python training_ui.py
```

训练界面默认路径：

```text
Kata root:       gomoku/KataGomo
Data dir:        gomoku/KataGomo/training_data
Engine exe:      gomoku/KataGomo/scripts/engine/katago.exe
Selfplay cfg:    gomoku/KataGomo/training_data/native_selfplay_15.cfg
Game model:      gomoku/KataGomo/models/model.bin.gz
```

首次恢复训练环境时，建议在界面中依次点击：

```text
Check Deps
Native Init
Init Dirs
```

或者手动创建目录：

```powershell
New-Item -ItemType Directory -Force .\KataGomo\training_data
New-Item -ItemType Directory -Force .\KataGomo\models
```

训练数据很大，默认写入：

```text
KataGomo/training_data/
```

如果要延续已有训练，需要单独传输或恢复这个目录。不要把它放进普通源码包。

## 10. 打包给其他人的建议

源码包建议包含：

```text
README.md
.gitignore
CMakeLists.txt
build.bat
bulid-debug.bat
game.py
training_ui.py
GameEngine.h
GameEngineDLL.cpp
GameEngineDLL.h
KataInferenceAdapter.cpp
KataInferenceAdapter.h
KataSelfplayMain.cpp
model_weights.txt
LXGWZhenKaiGB-Regular.ttf
TODO.md
```

如果希望对方无需编译即可运行，可以额外包含：

```text
GameEngine.dll
```

如果希望对方能重新编译，还需要让对方按本文恢复：

```text
KataGomo/
```

如果希望对方完整恢复 CUDA/KataGomo/训练环境，则单独传输或说明恢复：

```text
include/cuda/
KataGomo/models/model.bin.gz
KataGomo/training_data/
```

不要放入普通源码包：

```text
.venv/
.git/
build/
logs/
__pycache__/
*.zip
*.7z
*.rar
cudnn*.dll
cublas*.dll
cudart*.dll
zlib.dll
KataGomo/training_data/
```

## 11. 常见问题

`ctypes` 找不到 `GameEngine.dll`：

- 先运行 `.\build.bat`。
- 确认 `GameEngine.dll` 和 `game.py` 在同一目录。

`pygame` 导入失败：

```powershell
pip install pygame
```

CMake 找不到 `KataGomo/cpp/forbiddenPoint/ForbiddenPointFinder.cpp`：

- 没有恢复 `KataGomo/` 源码。
- 执行 `git clone -b Gom2024 https://github.com/hzyhhzy/KataGomo.git KataGomo`。

CMake 找不到 C++ 编译器：

- 安装 Visual Studio 2022 Build Tools。
- 打开新的 PowerShell 再运行 `.\build.bat`。
- 或使用 Visual Studio 的 `Developer PowerShell for VS 2022`。

CMake 找不到 cuDNN：

- 确认 `.\include\cuda\include\cudnn.h` 存在。
- 构建时显式传入：

```powershell
.\build.bat -DENABLE_KATAGOMO_CUDA=ON -DCUDNN_ROOT_DIR="$PWD\include\cuda"
```

运行时报 CUDA/cuDNN DLL 缺失：

- 确认 CUDA Toolkit 已安装。
- 确认 cuDNN 的 `bin/x64` 中 DLL 已复制到项目根目录或 `KataGomo/scripts/engine/`。
- 重新运行 CUDA 构建，让 CMake 自动复制运行时 DLL。

PyTorch CUDA 不可用：

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

- 如果输出 `False`，按 <https://pytorch.org/get-started/locally/> 重新选择 CUDA 版 PyTorch 安装命令。
- 同时确认 `nvidia-smi` 正常。

压缩源码非常慢：

- 不要压缩 `.venv/`、`.git/`、`KataGomo/training_data/`、`include/`、CUDA/cuDNN DLL。
- 源码包应该很小；完整训练环境应单独恢复或单独传输。
