# Design: Gomoku GTX1650Ti Optimized Evolution Plan

## Model Architecture
- `b10c128`: 10 residual blocks, 128 channels, fixup normalization
- ~2.96M parameters, FP16 training
- SWA (Stochastic Weight Averaging) + Lookahead optimizer

## Training Pipeline
1. Selfplay: katago engine generates games with MCTS guided by current best model
2. Shuffle: windowed sampling with exponential decay for continual learning
3. Train: PyTorch with policy+value+TD-value losses
4. Export: PyTorch checkpoint -> katago binary format
5. PK: headless arena with color-balanced evaluation

## Stage Rationale
- Rounds 1-5 (Warmup): Low visits, moderate games — quick iterations to establish baseline
- Rounds 6-8 (Intensification): More games, higher visits — deepen search quality
- Rounds 9-10 (Refinement): Maximum games/visits, lower LR, more epochs — fine-tune

## Hardware Constraints
- GPU: NVIDIA GeForce GTX 1650 Ti (4GB VRAM)
- Batch size 64 fits within 4GB with FP16
- 32 selfplay threads for throughput
