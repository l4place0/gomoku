# Elo/Bradley-Terry Rating System Integration Research

**Date:** 2026-06-14
**Purpose:** Evaluate feasibility of integrating Elo/Bradley-Terry rating into the gomoku self-play training pipeline

---

## 1. Claim Verification (Adversarial Review)

### Claim Under Review
> "The Bradley-Terry MLE has a single global maximum, and Zermelo's iterative algorithm is guaranteed to converge to it, monotonically improving log-likelihood at every step."

**Source:** Wikipedia (secondary)
**Verdict:** PARTIALLY REFUTED

### Analysis

The claim is **mathematically incomplete** as stated. The critical omission is the **strong connectivity condition**:

- **Ford (1957)** proved that the MLE for the Bradley-Terry model exists and is unique **if and only if** the pairwise comparison graph is strongly connected (directed path exists from every player to every other through observed comparisons).
- **When the graph is disconnected** (e.g., two groups of models never compared), the MLE either does not exist or is not unique.
- **Complete separation** (one model wins all games, no losses) causes MLE parameters to diverge to infinity — analogous to the Hauck-Donner effect in logistic regression.
- **Hunter (2004)** "MM Algorithms for Generalized Bradley-Terry Models" confirms the conditions including absence of irreducible balanced closed sets.

The monotonic convergence part is true for the algorithm iterations, but convergence toward a non-existent MLE is meaningless.

### Implications for Gomoku Pipeline

In the current pipeline with ~20 games per PK round, the comparison graph is sparse. The strong connectivity condition is **not automatically satisfied**, especially when:
- New models only play against their direct parent (tree structure)
- Regression checks only test against ancestors
- Some branches may be isolated

**Recommendation:** When implementing Elo, ensure sufficient cross-comparisons to maintain a strongly connected graph, or use regularization/priors (as KataGomo's elo.py does).

---

## 2. Bradley-Terry Model & Elo Mathematical Foundations

### Core Mathematics

The Bradley-Terry model defines the probability that player i beats player j as:

```
P(i beats j) = p_i / (p_i + p_j)
```

Where p_i are positive strength parameters. The log-likelihood is:

```
L = sum_ij [ w_ij * log(p_i / (p_i + p_j)) ]
```

Where w_ij is the number of times i beat j.

### Key Properties

| Property | Condition | Reference |
|----------|-----------|-----------|
| MLE exists | Comparison graph connected | Ford 1957 |
| MLE unique | Graph strongly connected | Ford 1957 |
| Zermelo convergence | Strong connectivity + algorithm iterations | Zermelo 1929 |
| Monotonic LL improvement | Always (algorithm property) | Zermelo 1929 |
| Gaussian approximation valid | Sufficient games per pair | Asymptotic theory |

### Relationship to Elo

The Elo rating is a logarithmic transformation of Bradley-Terry strengths:

```
Elo_i = C * log10(p_i)
```

Where C is typically 400/log(10) ≈ 173.7 (the "Elo constant").

### Relationship to SPRT

The Sequential Probability Ratio Test (SPRT) for testing H0: winrate = 0.5 vs H1: winrate = w1 uses the log-likelihood ratio, which is directly connected to Bradley-Terry. The current `ml/sprt.py` already has `winrate_to_elo()` and `elo_to_winrate()` conversions.

---

## 3. openskill.py vs KataGomo/python/elo.py

### Comparison Matrix

| Criterion | openskill.py | KataGomo/python/elo.py |
|-----------|-------------|----------------------|
| **Algorithm** | Weng-Lin (Bayesian) | MLE Gauss-Newton |
| **Implementation** | Python, MIT license | Python, project-specific |
| **Lines of code** | ~2000 | ~855 |
| **Dependencies** | scipy, numpy | scipy, numpy |
| **Uncertainty estimate** | Yes (sigma) | Yes (stderr via Fisher info) |
| **Multi-player** | Yes | Yes |
| **P1 advantage** | Not natively | Yes (built-in) |
| **Ties/draws** | Yes (modified model) | No (wins/losses only) |
| **Prior support** | Limited | Yes (regularization) |
| **Convergence** | Fast (closed-form) | Iterative (Gauss-Newton) |
| **Disconnected graph** | Handles (Bayesian prior) | May fail (MLE) |

### Recommendation: KataGomo/python/elo.py

**Rationale:**
1. **Already in project** — no new dependency
2. **P1 advantage support** — critical for gomoku (first player has significant advantage)
3. **Prior/regularization** — can handle sparse comparison graphs
4. **Proven in KataGo context** — designed for exactly this use case (Go-like games)
5. **stderr via Fisher information** — provides confidence intervals directly

**openskill.py disadvantages for this use case:**
- Weng-Lin is designed for multiplayer matchmaking, not model evaluation
- No P1 advantage modeling
- Would add external dependency
- Less control over optimization

---

## 4. Current Pipeline Analysis

### Existing PK Flow
```
automl_cli.py:run_pk()
  → headless_runner.py: play games
  → raw winrate = wins / (wins + losses)
  → evaluate_promotion(winrate, threshold=0.55)
  → SPRT early stopping
```

### Existing Elo Code (Not Integrated)
- `ml/sprt.py`: `winrate_to_elo()`, `elo_to_winrate()`, `compute_sprt_result()`
- `KataGomo/python/elo.py`: Full MLE Elo system with Gauss-Newton optimizer
- `ml/mlevo_cli.py`: `RegressionDetector` uses raw winrate trends

### Model Registry
```python
class ModelRecord:
    winrate: float  # Single PK round's raw winrate
    # No Elo, no confidence interval, no cumulative rating
```

---

## 5. Integration Strategy

### Phase 1: Data Collection (Minimal Changes)

**Goal:** Accumulate pairwise comparison data without changing promotion logic.

1. Create `ml/elo_tracker.py`:
   - Store all PK results as (winner, loser, timestamp) tuples
   - Persist to `elo_history.json` in model registry directory
   - No rating computation yet — just data collection

2. Modify `ml/automl_cli.py:run_pk()`:
   - After each PK round, append results to elo_tracker
   - Record: (challenger_id, defender_id, wins, losses, timestamp)
   - Keep existing raw winrate promotion logic unchanged

### Phase 2: Offline Elo Computation

**Goal:** Compute Elo ratings from accumulated data, compare with raw winrates.

1. Create `ml/elo_rating.py`:
   - Use KataGomo/python/elo.py as backend
   - Compute Elo for all models in registry
   - Output: Elo ± stderr for each model
   - Handle disconnected components (prior regularization)

2. Create CLI command `python -m ml.elo_rating compute`:
   - Reads elo_history.json
   - Outputs Elo rankings
   - Does NOT affect promotion decisions

### Phase 3: Elo-Guided Promotion (Optional)

**Goal:** Use Elo as supplementary signal for promotion decisions.

1. Modify promotion criteria:
   - Keep existing threshold-based promotion as primary
   - Add Elo-based confidence interval check
   - Example: promote if winrate > 0.55 AND Elo difference > 50

2. Regression detection:
   - Replace raw winrate trend with Elo trend
   - More robust to small sample sizes

### Phase 4: DAG Integration (Future)

**Goal:** Use Elo for branch comparison and merge decisions.

1. Modify `ml/dag_engine.py`:
   - Store Elo at each node
   - Compare branches via Elo difference
   - Guide merge decisions

---

## 6. Risk Assessment

### Technical Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Sparse comparison graph | High | Use KataGomo's prior regularization |
| P1 advantage not modeled | High | KataGomo elo.py has P1Advantage support |
| Computational cost | Low | Gauss-Newton converges fast for small N |
| Breaking existing pipeline | Medium | Phase 1 is purely additive |
| Elo drift over time | Medium | Time-weighted recency or windowed computation |

### Unknown Factors

1. **Optimal K-factor / regularization strength** — needs experimentation
2. **How many games needed for stable Elo** — currently 20 per PK, may need more
3. **Handling of model re-training** — same architecture retrained = same player or new?
4. **Branch merging** — how to combine Elo from merged branches

### Open Questions

- Should Elo replace raw winrate for promotion, or supplement it?
- How to handle the transition period (models without Elo history)?
- Should we compute Elo incrementally (after each game) or in batch?

---

## 7. Conclusion

The Bradley-Terry/Elo approach is mathematically sound for model evaluation, with the caveat that the comparison graph must be strongly connected for the MLE to have a unique solution. The existing `KataGomo/python/elo.py` is the better choice over `openskill.py` because it's already in-project, handles P1 advantage, and supports regularization for sparse graphs.

The recommended approach is a phased integration starting with data collection (zero risk), then offline computation (low risk), then optional promotion integration (medium risk). This preserves the existing pipeline while building toward a more robust evaluation system.

---

## References

1. Ford, L.R. (1957). "Solution of a Ranking Problem." *American Mathematical Monthly*, 64(8), 28-30.
2. Zermelo, E. (1929). "Die Berechnung der Turnier-Ergebnisse als ein Maximumproblem der Wahrscheinlichkeitsrechnung." *Mathematische Zeitschrift*, 29, 436-460.
3. Hunter, D.R. (2004). "MM Algorithms for Generalized Bradley-Terry Models." *Annals of Statistics*, 32(1), 384-406.
4. Bradley, R.A. & Terry, M.E. (1952). "Rank Analysis of Incomplete Block Designs."
5. David, H.A. (1963). *The Method of Paired Comparisons*.
6. Feigin, P.D. & Cohen, A. (1978). "On a Model for Paired Comparisons with Ties."
