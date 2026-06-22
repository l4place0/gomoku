#!/usr/bin/env python3
"""elo_rating.py — MLE Elo rating engine wrapping KataGomo/python/elo.py.

Reads pairwise PK results from elo_history.jsonl, computes maximum-likelihood
Elo ratings with confidence intervals using Bradley-Terry model.
"""

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add KataGomo python to path for elo module
_KATA_ELO_DIR = Path(__file__).resolve().parent.parent / "KataGomo" / "python"
if str(_KATA_ELO_DIR) not in sys.path:
    sys.path.insert(0, str(_KATA_ELO_DIR))

from elo import (
    EloInfo,
    Likelihood,
    P1_ADVANTAGE_NAME,
    compute_elos,
    likelihood_of_games,
    make_center_elos_prior,
    make_sequential_prior,
    make_single_player_prior,
)

from ml.elo_tracker import EloTracker, PKRecord

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "elo_history.jsonl"


@dataclass
class ModelElo:
    """Elo rating for a single model."""
    hash: str
    elo: float
    stderr: float
    effective_games: float

    @property
    def ci_lower(self) -> float:
        return self.elo - 1.96 * self.stderr

    @property
    def ci_upper(self) -> float:
        return self.elo + 1.96 * self.stderr


@dataclass
class PairwiseDiff:
    """Elo difference between two models."""
    elo_diff: float
    ci_lower: float
    ci_upper: float
    p_superiority: float  # probability that candidate is stronger


class EloRatingEngine:
    """Computes MLE Elo ratings from pairwise PK data."""

    def __init__(self, history_path: Optional[Path] = None, prior_games: float = 10.0):
        self._history_path = history_path or DEFAULT_HISTORY_PATH
        self._prior_games = prior_games
        self._elo_info: Optional[EloInfo] = None
        self._records: List[PKRecord] = []

    def compute_all(self) -> Dict[str, ModelElo]:
        """Compute Elo ratings for all models from elo_history.jsonl.

        Returns dict mapping model hash -> ModelElo.
        """
        tracker = EloTracker(self._history_path)
        self._records = tracker.read_all()
        if not self._records:
            return {}

        # Build Likelihood data
        data: List[Likelihood] = []
        all_players = set()
        branch_players: Dict[str, List[str]] = {}  # branch -> [players by round]

        for rec in self._records:
            cand = rec.candidate[:12]
            base = rec.baseline[:12]
            all_players.add(cand)
            all_players.add(base)

            # Track per-branch ordering for sequential prior
            branch = rec.branch
            if branch not in branch_players:
                branch_players[branch] = []
            if cand not in branch_players[branch]:
                branch_players[branch].append(cand)
            if base not in branch_players[branch]:
                branch_players[branch].append(base)

            # Create Likelihood objects from per-color data
            # When candidate is black (P1): candidate_black_wins vs baseline_white_wins
            p1_games = rec.candidate_black_wins + rec.baseline_white_wins
            if p1_games > 0:
                p1_won = rec.candidate_black_wins / p1_games
                data.extend(likelihood_of_games(
                    p1=cand, p2=base,
                    num_games=p1_games,
                    p1_won_proportion=p1_won,
                    include_first_player_advantage=True,
                ))

            # When candidate is white (P2): candidate_white_wins vs baseline_black_wins
            p2_games = rec.candidate_white_wins + rec.baseline_black_wins
            if p2_games > 0:
                # In this case baseline is P1, candidate is P2
                p1_won = rec.baseline_black_wins / p2_games
                data.extend(likelihood_of_games(
                    p1=base, p2=cand,
                    num_games=p2_games,
                    p1_won_proportion=p1_won,
                    include_first_player_advantage=True,
                ))

        players = sorted(all_players)

        # Add priors for regularization
        # Sequential prior: adjacent models in each branch are expected to be similar
        for branch, branch_plas in branch_players.items():
            if len(branch_plas) > 1:
                data.extend(make_sequential_prior(branch_plas, self._prior_games))

        # Center prior: anchor population mean at Elo 0
        data.extend(make_center_elos_prior(players, 0.0))

        # P1 advantage prior
        data.extend(make_single_player_prior(P1_ADVANTAGE_NAME, 10.0, 0.0))

        # Compute MLE Elos
        self._elo_info = compute_elos(data)

        # Build result dict
        result = {}
        for player in self._elo_info.get_players():
            if player == P1_ADVANTAGE_NAME:
                continue
            result[player] = ModelElo(
                hash=player,
                elo=self._elo_info.get_elo(player),
                stderr=self._elo_info.get_approx_elo_stderr(player),
                effective_games=self._elo_info.effective_game_count.get(player, 0),
            )
        return result

    def get_pairwise_diff(self, candidate: str, baseline: str) -> Optional[PairwiseDiff]:
        """Compute Elo difference and CI between two models.

        Args:
            candidate: model hash (or prefix)
            baseline: model hash (or prefix)
        """
        if self._elo_info is None:
            self.compute_all()
        if self._elo_info is None:
            return None

        # Try to match hash prefixes
        cand = self._resolve_player(candidate)
        base = self._resolve_player(baseline)
        if cand is None or base is None:
            return None

        elo_diff = self._elo_info.get_elo_difference(cand, base)
        # CI from covariance matrix
        ci_lower, ci_upper = self._compute_pairwise_ci(cand, base)
        p_sup = self._elo_info.get_approx_likelihood_of_superiority(cand, base)

        return PairwiseDiff(
            elo_diff=elo_diff,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_superiority=p_sup,
        )

    def get_rankings(self) -> List[ModelElo]:
        """Get all models sorted by Elo descending."""
        elos = self.compute_all()
        return sorted(elos.values(), key=lambda m: -m.elo)

    def _resolve_player(self, name: str) -> Optional[str]:
        """Resolve a hash or prefix to a player name in the Elo data."""
        if self._elo_info is None:
            return None
        players = [p for p in self._elo_info.get_players() if p != P1_ADVANTAGE_NAME]
        if name in players:
            return name
        # Try prefix match
        matches = [p for p in players if p.startswith(name)]
        if len(matches) == 1:
            return matches[0]
        return None

    def _compute_pairwise_ci(self, p1: str, p2: str) -> Tuple[float, float]:
        """Compute 95% CI for Elo difference using covariance matrix."""
        elo_diff = self._elo_info.get_elo_difference(p1, p2)
        stderr_diff = self._elo_info.get_approx_elo_difference_stderr(p1, p2)
        ci_lower = elo_diff - 1.96 * stderr_diff
        ci_upper = elo_diff + 1.96 * stderr_diff
        return ci_lower, ci_upper


def main():
    """CLI entry point for offline Elo computation."""
    import argparse

    parser = argparse.ArgumentParser(description="Compute Elo ratings from PK history")
    parser.add_argument("command", choices=["compute", "rank", "sync"],
                        help="compute=compute Elos, rank=show rankings with branch info, sync=update model registry")
    parser.add_argument("--history", type=str, default=str(DEFAULT_HISTORY_PATH),
                        help="Path to elo_history.jsonl")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--prior-games", type=float, default=10.0,
                        help="Number of games for Bayesian prior strength")
    args = parser.parse_args()

    engine = EloRatingEngine(Path(args.history), args.prior_games)

    if args.command == "sync":
        # Sync Elo ratings to model registry
        from ml.model_registry import ModelRegistry
        registry = ModelRegistry()
        rankings = engine.get_rankings()
        updated = 0
        for m in rankings:
            # Try to match by hash prefix
            records = registry.read_all()
            for r in records:
                if r.hash.startswith(m.hash) or m.hash.startswith(r.hash):
                    if r.elo != m.elo:
                        registry.update_elo(r.hash, m.elo)
                        updated += 1
                    break
        print(f"Updated {updated} model records with Elo ratings.")
        return

    rankings = engine.get_rankings()
    if not rankings:
        print("No Elo data available.")
        return

    if args.command == "rank":
        # Show rankings with branch info from registry
        from ml.model_registry import ModelRegistry
        from ml.dag_engine import DAGEngine
        registry = ModelRegistry()
        dag = DAGEngine(registry)
        branch_summary = dag.get_branch_elo_summary()

        if args.json:
            output = {"rankings": [], "branches": branch_summary}
            for m in rankings:
                output["rankings"].append({
                    "hash": m.hash,
                    "elo": round(m.elo, 1),
                    "stderr": round(m.stderr, 2),
                    "ci_lower": round(m.ci_lower, 1),
                    "ci_upper": round(m.ci_upper, 1),
                })
            print(json.dumps(output, indent=2))
        else:
            print("=== Global Elo Rankings ===")
            print(f"{'Hash':<14} {'Elo':>8} {'Stderr':>8} {'95% CI':>18}")
            print("-" * 52)
            for m in rankings:
                ci = f"[{m.ci_lower:+.1f}, {m.ci_upper:+.1f}]"
                print(f"{m.hash:<14} {m.elo:>+8.1f} {m.stderr:>8.2f} {ci:>18}")
            print("\n=== Branch Elo Summary ===")
            for branch, info in sorted(branch_summary.items()):
                avg = f"{info['avg_elo']:+.1f}" if info['avg_elo'] is not None else "N/A"
                best = f"{info['best_elo']:+.1f}" if info['best_elo'] is not None else "N/A"
                print(f"  {branch}: avg={avg}, best={best}, models={info['model_count']}")
        return

    # Default: compute command
    if args.json:
        output = []
        for m in rankings:
            output.append({
                "hash": m.hash,
                "elo": round(m.elo, 1),
                "stderr": round(m.stderr, 2),
                "ci_lower": round(m.ci_lower, 1),
                "ci_upper": round(m.ci_upper, 1),
                "effective_games": round(m.effective_games, 1),
            })
        print(json.dumps(output, indent=2))
    else:
        print(f"{'Hash':<14} {'Elo':>8} {'Stderr':>8} {'95% CI':>18} {'Eff Games':>10}")
        print("-" * 62)
        for m in rankings:
            ci = f"[{m.ci_lower:+.1f}, {m.ci_upper:+.1f}]"
            print(f"{m.hash:<14} {m.elo:>+8.1f} {m.stderr:>8.2f} {ci:>18} {m.effective_games:>10.1f}")

    # Show P1 advantage if available
    if engine._elo_info and P1_ADVANTAGE_NAME in engine._elo_info.elo:
        p1_elo = engine._elo_info.get_elo(P1_ADVANTAGE_NAME)
        p1_stderr = engine._elo_info.get_approx_elo_stderr(P1_ADVANTAGE_NAME)
        if not args.json:
            print(f"\nFirst-player advantage: {p1_elo:+.1f} +/- {p1_stderr:.2f} Elo")


if __name__ == "__main__":
    main()
