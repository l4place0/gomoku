# Proposal: v2-stable-recovery

## Background

Round 6 regressed to 25% winrate (from Round 4's 75%) due to:
- LR dropped from 0.002 → 0.001 (over-convergence)
- 2 epochs on same data (overfitting, vloss went flat)
- Selfplay throughput was fine (720 games @ 32 threads) but training params degraded the model

This plan reverts to the Round 4 proven formula and gradually scales up.

## Goal

Recover from the Round 6 regression, establish a stable promotion rhythm, and progressively increase selfplay quality to reach a strong b10c128 model by end of training window.

## Target Metrics

- Winrate against previous best model in PK arena: **>= 55%** (promotion threshold)
- Target 3+ successful promotions across 8 rounds
- Selfplay throughput: maintain > 500 games/hr with 32 threads
- Final model: stable at sf_visits=128, pk_games=60

## Stages

| Stage | Rounds | Focus | Key Params |
|-------|--------|-------|------------|
| Recovery | 7-9 | Revert to Round 4 formula, re-establish promotions | lr=0.002, 1 epoch, visits=112 |
| Scale-up | 10-12 | Increase selfplay volume and PK sample size | lr=0.0015, visits=128, pk_games=50 |
| Convergence | 13-14 | Final tuning with more data and careful LR decay | lr=0.001, visits=128, pk_games=60 |

## Evaluation Plan

- Each round: 50+ games in PK arena with fixed visits (pk_visits_b=128, pk_visits_w=64)
- Promotion threshold: 55% winrate
- Fixed opening set for reliable evaluation (12+ openings, both sides)
