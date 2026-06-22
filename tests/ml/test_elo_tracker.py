#!/usr/bin/env python3
"""Tests for ml/elo_tracker.py — EloTracker and backfill."""

import json
import tempfile
from pathlib import Path

import pytest

from ml.elo_tracker import EloTracker, PKRecord, backfill_from_ledger


@pytest.fixture
def tmp_history(tmp_path):
    return tmp_path / "elo_history.jsonl"


@pytest.fixture
def tracker(tmp_history):
    return EloTracker(tmp_history)


class TestPKRecord:
    def test_roundtrip(self):
        rec = PKRecord(
            candidate="abc123", baseline="def456",
            candidate_wins=12, baseline_wins=8,
            candidate_black_wins=7, candidate_white_wins=5,
            baseline_black_wins=4, baseline_white_wins=4,
            round=15, branch="mainline",
            timestamp="2026-06-14T23:00:00Z",
        )
        j = rec.to_json()
        rec2 = PKRecord.from_json(j)
        assert rec2.candidate == "abc123"
        assert rec2.baseline == "def456"
        assert rec2.candidate_wins == 12
        assert rec2.baseline_wins == 8
        assert rec2.candidate_black_wins == 7
        assert rec2.round == 15

    def test_json_is_valid(self):
        rec = PKRecord(
            candidate="a", baseline="b",
            candidate_wins=1, baseline_wins=0,
            candidate_black_wins=1, candidate_white_wins=0,
            baseline_black_wins=0, baseline_white_wins=0,
            round=1, branch="mainline", timestamp="t",
        )
        data = json.loads(rec.to_json())
        assert set(data.keys()) == {
            "candidate", "baseline", "candidate_wins", "baseline_wins",
            "candidate_black_wins", "candidate_white_wins",
            "baseline_black_wins", "baseline_white_wins",
            "round", "branch", "timestamp",
        }


class TestEloTracker:
    def test_record_appends_line(self, tracker):
        tracker.record(
            candidate_hash="aaa", baseline_hash="bbb",
            candidate_wins=10, baseline_wins=5,
            candidate_black_wins=6, candidate_white_wins=4,
            baseline_black_wins=3, baseline_white_wins=2,
            round_no=1,
        )
        tracker.record(
            candidate_hash="ccc", baseline_hash="aaa",
            candidate_wins=8, baseline_wins=12,
            candidate_black_wins=4, candidate_white_wins=4,
            baseline_black_wins=6, baseline_white_wins=6,
            round_no=2,
        )
        records = tracker.read_all()
        assert len(records) == 2
        assert records[0].candidate == "aaa"
        assert records[1].candidate == "ccc"

    def test_skip_zero_games(self, tracker):
        tracker.record(
            candidate_hash="aaa", baseline_hash="bbb",
            candidate_wins=0, baseline_wins=0,
            candidate_black_wins=0, candidate_white_wins=0,
            baseline_black_wins=0, baseline_white_wins=0,
            round_no=1,
        )
        assert tracker._path.exists() is False or tracker.read_all() == []

    def test_read_empty(self, tracker):
        assert tracker.read_all() == []

    def test_append_only(self, tracker):
        for i in range(5):
            tracker.record(
                candidate_hash=f"c{i}", baseline_hash=f"b{i}",
                candidate_wins=i + 1, baseline_wins=i,
                candidate_black_wins=i, candidate_white_wins=1,
                baseline_black_wins=i, baseline_white_wins=0,
                round_no=i,
            )
        records = tracker.read_all()
        assert len(records) == 5
        assert [r.round for r in records] == [0, 1, 2, 3, 4]


class TestBackfill:
    def test_backfill_from_ledger(self, tmp_path):
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps([
            {"round": 1, "timestamp": "2026-01-01", "pk": {"wins_new": 12, "losses_new": 8}},
            {"round": 2, "timestamp": "2026-01-02", "pk": {"wins_new": 15, "losses_new": 5}},
            {"round": 3, "timestamp": "2026-01-03", "pk": {"wins_new": 0, "losses_new": 0}},
        ]))

        history = tmp_path / "history.jsonl"
        count = backfill_from_ledger(ledger, history)
        assert count == 2  # round 3 has 0 games, skipped

        tracker = EloTracker(history)
        records = tracker.read_all()
        assert len(records) == 2
        assert records[0].round == 1
        assert records[0].candidate_wins == 12
        assert records[1].round == 2

    def test_backfill_missing_ledger(self, tmp_path):
        count = backfill_from_ledger(tmp_path / "nonexistent.json", tmp_path / "h.jsonl")
        assert count == 0
