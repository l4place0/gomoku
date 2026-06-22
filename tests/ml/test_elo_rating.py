#!/usr/bin/env python3
"""Tests for ml/elo_rating.py — EloRatingEngine."""

import json
from pathlib import Path

import pytest

from ml.elo_tracker import EloTracker, PKRecord
from ml.elo_rating import EloRatingEngine, ModelElo, PairwiseDiff


@pytest.fixture
def tmp_history(tmp_path):
    return tmp_path / "elo_history.jsonl"


def _write_records(path: Path, records: list[PKRecord]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in records:
            f.write(r.to_json() + "\n")


def _make_record(candidate, baseline, cand_wins, base_wins, round_no=1):
    """Create a PKRecord with per-color wins split roughly evenly."""
    half_cand = cand_wins // 2
    half_base = base_wins // 2
    return PKRecord(
        candidate=candidate, baseline=baseline,
        candidate_wins=cand_wins, baseline_wins=base_wins,
        candidate_black_wins=half_cand, candidate_white_wins=cand_wins - half_cand,
        baseline_black_wins=half_base, baseline_white_wins=base_wins - half_base,
        round=round_no, branch="mainline", timestamp="2026-01-01T00:00:00Z",
    )


class TestEloRatingEngine:
    def test_empty_history(self, tmp_history):
        engine = EloRatingEngine(tmp_history)
        result = engine.compute_all()
        assert result == {}

    def test_single_pair(self, tmp_history):
        _write_records(tmp_history, [
            _make_record("aaa", "bbb", 15, 5, 1),
        ])
        engine = EloRatingEngine(tmp_history)
        result = engine.compute_all()
        assert len(result) == 2
        assert "aaa" in result
        assert "bbb" in result
        # aaa won more, should have higher Elo
        assert result["aaa"].elo > result["bbb"].elo

    def test_pairwise_diff(self, tmp_history):
        _write_records(tmp_history, [
            _make_record("aaa", "bbb", 15, 5, 1),
        ])
        engine = EloRatingEngine(tmp_history)
        diff = engine.get_pairwise_diff("aaa", "bbb")
        assert diff is not None
        assert diff.elo_diff > 0
        assert diff.ci_lower < diff.ci_upper
        assert diff.p_superiority > 0.5

    def test_rankings_sorted(self, tmp_history):
        _write_records(tmp_history, [
            _make_record("aaa", "bbb", 15, 5, 1),
            _make_record("ccc", "aaa", 12, 8, 2),
        ])
        engine = EloRatingEngine(tmp_history)
        rankings = engine.get_rankings()
        assert len(rankings) >= 2
        # Should be sorted descending by Elo
        for i in range(len(rankings) - 1):
            assert rankings[i].elo >= rankings[i + 1].elo

    def test_ci_contains_true_value(self, tmp_history):
        # With enough data, CI should contain the true Elo difference
        _write_records(tmp_history, [
            _make_record("aaa", "bbb", 55, 45, 1),  # slight edge
        ])
        engine = EloRatingEngine(tmp_history)
        diff = engine.get_pairwise_diff("aaa", "bbb")
        assert diff is not None
        # With 100 games, CI should be reasonably tight
        assert diff.ci_lower < diff.elo_diff < diff.ci_upper

    def test_prefix_match(self, tmp_history):
        _write_records(tmp_history, [
            _make_record("abcdef123456", "654321fedcba", 15, 5, 1),
        ])
        engine = EloRatingEngine(tmp_history)
        # Should resolve prefix to full hash
        diff = engine.get_pairwise_diff("abcdef", "654321fed")
        assert diff is not None
        assert diff.elo_diff > 0

    def test_compute_all_populates_elo_info(self, tmp_history):
        _write_records(tmp_history, [
            _make_record("aaa", "bbb", 10, 10, 1),
        ])
        engine = EloRatingEngine(tmp_history)
        engine.compute_all()
        assert engine._elo_info is not None
