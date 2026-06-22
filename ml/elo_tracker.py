#!/usr/bin/env python3
"""elo_tracker.py — Pairwise PK result recorder for Elo rating computation.

Appends PK results to elo_history.jsonl after each evaluation round.
Data is consumed by elo_rating.py for MLE Elo computation.
"""

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "elo_history.jsonl"


@dataclass
class PKRecord:
    """A single pairwise PK result record."""
    candidate: str          # SHA256 hash of candidate model
    baseline: str           # SHA256 hash of baseline model
    candidate_wins: int     # total wins by candidate
    baseline_wins: int      # total wins by baseline
    candidate_black_wins: int  # wins by candidate when playing black (P1)
    candidate_white_wins: int  # wins by candidate when playing white (P2)
    baseline_black_wins: int   # wins by baseline when playing black (P1)
    baseline_white_wins: int   # wins by baseline when playing white (P2)
    round: int              # training round number
    branch: str             # branch name
    timestamp: str          # ISO 8601 timestamp

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "PKRecord":
        return cls(**json.loads(line))


class EloTracker:
    """Records pairwise PK results to elo_history.jsonl."""

    def __init__(self, history_path: Optional[Path] = None):
        self._path = history_path or DEFAULT_HISTORY_PATH

    def record(
        self,
        candidate_hash: str,
        baseline_hash: str,
        candidate_wins: int,
        baseline_wins: int,
        candidate_black_wins: int,
        candidate_white_wins: int,
        baseline_black_wins: int,
        baseline_white_wins: int,
        round_no: int,
        branch: str = "mainline",
    ) -> None:
        """Append a PK result record to elo_history.jsonl.

        Skips recording if candidate_wins + baseline_wins == 0 (no games played).
        """
        total = candidate_wins + baseline_wins
        if total == 0:
            return

        record = PKRecord(
            candidate=candidate_hash,
            baseline=baseline_hash,
            candidate_wins=candidate_wins,
            baseline_wins=baseline_wins,
            candidate_black_wins=candidate_black_wins,
            candidate_white_wins=candidate_white_wins,
            baseline_black_wins=baseline_black_wins,
            baseline_white_wins=baseline_white_wins,
            round=round_no,
            branch=branch,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")

    def read_all(self) -> list[PKRecord]:
        """Read all records from elo_history.jsonl."""
        if not self._path.exists():
            return []
        records = []
        with open(self._path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(PKRecord.from_json(line))
        return records


def backfill_from_ledger(ledger_path: Path, history_path: Optional[Path] = None) -> int:
    """Extract historical PK data from evolution_ledger.json and populate elo_history.jsonl.

    Returns the number of records written.
    """
    tracker = EloTracker(history_path)

    if not ledger_path.exists():
        return 0

    _MAX_JSON_SIZE = 50 * 1024 * 1024
    if ledger_path.stat().st_size > _MAX_JSON_SIZE:
        return 0

    try:
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    except Exception:
        return 0

    if not isinstance(ledger, list):
        return 0

    # Clear existing history to avoid duplicates
    if tracker._path.exists():
        tracker._path.unlink()

    count = 0
    for entry in ledger:
        if not isinstance(entry, dict):
            continue
        pk = entry.get("pk", {})
        round_no = entry.get("round", 0)
        wins = pk.get("wins_new", 0)
        losses = pk.get("losses_new", 0)

        if wins + losses == 0:
            continue

        # Backfill uses placeholder hashes since we don't have the actual model hashes
        # from the ledger. The backfill is mainly for populating the comparison graph.
        sprt = pk.get("sprt", {})
        record = PKRecord(
            candidate=f"round_{round_no}_candidate",
            baseline=f"round_{round_no}_baseline",
            candidate_wins=wins,
            baseline_wins=losses,
            # Per-color data not available in legacy ledger, approximate from total
            candidate_black_wins=wins // 2,
            candidate_white_wins=wins - wins // 2,
            baseline_black_wins=losses // 2,
            baseline_white_wins=losses - losses // 2,
            round=round_no,
            branch="mainline",
            timestamp=entry.get("timestamp", ""),
        )

        tracker._path.parent.mkdir(parents=True, exist_ok=True)
        with open(tracker._path, "a", encoding="utf-8") as f:
            f.write(record.to_json() + "\n")
        count += 1

    return count
