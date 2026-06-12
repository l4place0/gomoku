#!/usr/bin/env python3
"""sprt.py — Sequential Probability Ratio Test for model evaluation.

Provides SPRT statistical testing, Elo conversion, and confidence interval
estimation for PK (player-kill) evaluation in the training pipeline.
"""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class SPRTResult:
    """Result of a SPRT evaluation."""
    decision: str  # "accept", "reject", "undecided"
    llr: float  # log-likelihood ratio
    elo_diff: float  # estimated Elo difference
    ci_lower: float  # 95% CI lower bound (Elo)
    ci_upper: float  # 95% CI upper bound (Elo)
    winrate: float
    wins: int
    losses: int
    total: int

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "llr": round(self.llr, 4),
            "elo_diff": round(self.elo_diff, 1),
            "ci_lower": round(self.ci_lower, 1),
            "ci_upper": round(self.ci_upper, 1),
            "winrate": round(self.winrate, 4),
            "wins": self.wins,
            "losses": self.losses,
            "total": self.total,
        }


def winrate_to_elo(winrate: float) -> float:
    """Convert win probability to Elo difference.

    Args:
        winrate: Win probability in [0, 1]. 0.5 means equal strength.

    Returns:
        Elo difference. Positive means candidate is stronger.
    """
    if winrate <= 0:
        return -400.0
    if winrate >= 1:
        return 400.0
    # Clamp to avoid log(0)
    winrate = max(0.001, min(0.999, winrate))
    return -400.0 * math.log10(1.0 / winrate - 1.0)


def elo_to_winrate(elo: float) -> float:
    """Convert Elo difference to win probability."""
    return 1.0 / (1.0 + 10.0 ** (-elo / 400.0))


def sprt_check(
    wins: int,
    losses: int,
    alpha: float = 0.05,
    beta: float = 0.05,
    elo_diff: float = 35.0,
) -> Optional[str]:
    """Sequential Probability Ratio Test.

    Tests H0: candidate is weaker than baseline by elo_diff
    vs H1: candidate is stronger than baseline by elo_diff.

    Args:
        wins: Number of candidate wins (excluding draws).
        losses: Number of baseline wins (excluding draws).
        alpha: Type I error rate (false positive).
        beta: Type II error rate (false negative).
        elo_diff: Elo difference for H1 hypothesis.

    Returns:
        "candidate_wins" if H1 accepted, "baseline_wins" if H0 accepted,
        None if undecided (continue testing).
    """
    if wins + losses < 1:
        return None

    # Under H1: candidate is stronger by elo_diff
    p1 = elo_to_winrate(elo_diff)
    # Under H0: equal strength
    p0 = 0.5

    # Log-likelihood ratio
    llr = 0.0
    if wins > 0:
        llr += wins * math.log(p1 / p0)
    if losses > 0:
        llr += losses * math.log((1 - p1) / (1 - p0))

    # Decision boundaries
    a = math.log(beta / (1 - alpha))
    b = math.log((1 - beta) / alpha)

    if llr >= b:
        return "candidate_wins"
    elif llr <= a:
        return "baseline_wins"
    return None


def compute_sprt_result(
    wins: int,
    losses: int,
    alpha: float = 0.05,
    beta: float = 0.05,
    elo_diff: float = 35.0,
) -> SPRTResult:
    """Compute full SPRT result with statistics.

    Args:
        wins: Number of candidate wins (excluding draws).
        losses: Number of baseline wins (excluding draws).
        alpha: Type I error rate.
        beta: Type II error rate.
        elo_diff: Elo difference for H1 hypothesis.

    Returns:
        SPRTResult with decision, statistics, and confidence intervals.
    """
    total = wins + losses
    winrate = wins / total if total > 0 else 0.5

    # Compute LLR
    if total > 0:
        p1 = elo_to_winrate(elo_diff)
        p0 = 0.5
        llr = 0.0
        if wins > 0:
            llr += wins * math.log(p1 / p0)
        if losses > 0:
            llr += losses * math.log((1 - p1) / (1 - p0))
    else:
        llr = 0.0

    # Decision
    decision_raw = sprt_check(wins, losses, alpha, beta, elo_diff)
    if decision_raw == "candidate_wins":
        decision = "accept"
    elif decision_raw == "baseline_wins":
        decision = "reject"
    else:
        decision = "undecided"

    # Elo estimate
    elo_est = winrate_to_elo(winrate)

    # 95% confidence interval using normal approximation
    # SE = sqrt(p*(1-p)/n) where p = winrate, n = total
    if total > 1:
        se = math.sqrt(winrate * (1 - winrate) / total)
        # Convert SE to Elo scale using delta method
        # dElo/dp = 400 / (ln(10) * p * (1-p))
        deriv = 400.0 / (math.log(10) * winrate * (1 - winrate)) if 0 < winrate < 1 else 0
        elo_se = se * deriv
        ci_lower = elo_est - 1.96 * elo_se
        ci_upper = elo_est + 1.96 * elo_se
    else:
        ci_lower = -400.0
        ci_upper = 400.0

    return SPRTResult(
        decision=decision,
        llr=llr,
        elo_diff=elo_est,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        winrate=winrate,
        wins=wins,
        losses=losses,
        total=total,
    )
