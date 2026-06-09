# Gomoku AI Engine

15x15 五子棋博弈引擎，集成 Alpha-Beta 搜索、KataGomo 神经网络推理、AutoML 训练管线。

## Architecture

```
gomoku/
├── game/              # Game engine + Pygame GUI
│   ├── game.py        # Main game loop, state machine, rendering
│   ├── game_logic.py  # Symmetry, distance, candidate selection
│   └── game_logger.py # Structured game logging
├── ml/                # ML training pipeline
│   ├── automl_cli.py  # Selfplay → shuffle → train → export orchestrator
│   ├── mlevo_cli.py   # Evolution workflow with DAG lineage
│   ├── training_ui.py # Tkinter training management GUI
│   ├── model_registry.py / plan_registry.py / dag_engine.py
│   └── webui/         # FastAPI training console
├── tools/             # Shared engine bindings
│   ├── ai_worker.py   # GameEngine ctypes wrapper
│   └── headless_runner.py # Headless match evaluation
├── engine/            # C++ source + CMake build
│   ├── src/           # GameEngineDLL, KataInferenceAdapter
│   └── CMakeLists.txt
└── KataGomo/          # KataGo fork (git submodule)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| GUI | Python + Pygame |
| Search | C++ Alpha-Beta with hash table, VCF solver |
| Neural Net | KataGomo MCTS (CUDA / OpenCL / Eigen) |
| Training | PyTorch, KataGomo selfplay pipeline |
| Web Console | FastAPI |
| Build | CMake + MSVC / GCC |

## Quick Start

### Prerequisites

- Python 3.12+
- C++ compiler (MSVC 2022 or GCC 13+)
- CMake 3.18+

### Build & Run

```bash
# Clone with submodule
git clone --recurse-submodules https://github.com/l4place0/gomoku.git
cd gomoku

# Install dependencies
pip install pygame psutil numpy

# Build engine (basic, no CUDA)
cd engine && cmake -B build . && cmake --build build && cd ..

# Run game
python game/game.py
```

### With CUDA / KataGomo Neural Net

```bash
# Additional requirements: NVIDIA driver, CUDA Toolkit, cuDNN, zlib
cd engine
cmake -B build . -DENABLE_KATAGOMO_CUDA=ON -DCUDNN_ROOT_DIR=../include/cuda
cmake --build build
cd ..

# Place model
# KataGomo/models/model.bin.gz

python game/game.py
```

## ML Training Pipeline

```bash
# Run AutoML evolution loop
python ml/automl_cli.py --preset tiny

# MLEvo workflow (plan → train → evaluate → promote)
python ml/mlevo_cli.py new my-plan
python ml/mlevo_cli.py run --plan my-plan --round 1 --preset small

# Training UI
python ml/training_ui.py

# Web console
pip install fastapi uvicorn
uvicorn ml.webui.app:app --reload
```

## Testing

```bash
pip install pytest
pytest tests/ -v

# Safety net tests (module reachability, file existence, CLI invocation)
pytest tests/test_path_safety.py -v
```

## Project Structure

| Component | Description |
|-----------|-------------|
| `game/game.py` | Pygame GUI with state machine (INIT → AI_FIRST → THREE_HAND → FIVE_HAND → NORMAL → GAME_OVER) |
| `engine/` | C++ engine: board logic, forbidden point detection, Alpha-Beta search, KataGomo inference adapter |
| `ml/automl_cli.py` | Full training loop: selfplay → shuffle → train → export → PK evaluation |
| `ml/mlevo_cli.py` | Evolution orchestrator with DAG-based model lineage, branch/merge, fault injection |
| `ml/model_registry.py` | JSONL-based model version registry with hash, parent, winrate tracking |
| `tools/headless_runner.py` | Rule-compliant headless match runner (three-hand swap, five-hand N-play) |

## Dependencies

**Runtime:** pygame, numpy, psutil

**Training (optional):** torch (CUDA build), KataGomo selfplay scripts

**Build:** CMake, C++17 compiler, KataGomo source (`KataGomo/cpp/`)

## License

Research project. See [KataGomo](https://github.com/hzyhhzy/KataGomo) for upstream license.
