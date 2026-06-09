# Tasks: v2-stable-recovery

## Stage 1: Recovery (Rounds 7-9)

- [x] 1.1 Complete Round 7 — Revert to Round 4 formula (lr=0.002, 1 epoch, visits=112, 600 games, 50 PK)
- [x] 1.2 Complete Round 8 — Same params as Round 7 if promoted; retry with more sf_games if failed
- [ ] 1.3 Complete Round 9 — Transition round: if R7+R8 both promoted, bump sf_visits to 128

## Stage 2: Scale-up (Rounds 10-12)

- [ ] 2.1 Complete Round 10 — Increase sf_games to 800, lr to 0.0015, keep 1 epoch
- [ ] 2.2 Complete Round 11 — Same scale-up params; verify vloss trend
- [ ] 2.3 Complete Round 12 — If stable, increase sf_games to 1000

## Stage 3: Convergence (Rounds 13-14)

- [ ] 3.1 Complete Round 13 — lr=0.001, sf_games=1000, pk_games=60
- [ ] 3.2 Complete Round 14 — Final round, same params, archive plan

## Verification Checklist

- [ ] V.1 Confirm b10c128 model loads correctly on Linux (smoke test passed)
- [ ] V.2 Verify selfplay throughput > 500 games/hr with 32 threads
- [ ] V.3 Monitor vloss does not increase across rounds (overfitting guard)
- [ ] V.4 Confirm promotion threshold 55% is achievable with 50 PK games
