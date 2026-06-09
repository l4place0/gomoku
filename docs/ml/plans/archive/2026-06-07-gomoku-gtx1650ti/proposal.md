# Proposal: Gomoku GTX1650Ti Optimized Evolution Plan

## Goal
Train a b10c128 neural network for Gomoku AI via iterative self-play reinforcement learning on a GTX 1650 Ti (4GB VRAM).

## Target Metrics
- Winrate against baseline model in PK arena: >= 55% per round
- Target winrate for early stopping: 85%
- Loss plateau threshold: 0.005

## Evaluation Plan
- 3-stage progressive training: warmup (rounds 1-5), intensification (6-8), refinement (9-10)
- PK arena with color-swapped sub-rounds for fair evaluation
- Automatic promotion when candidate beats champion at >= 55% winrate
