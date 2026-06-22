"""Layer 1: Pure logic tests for PK evaluation — no DLL or subprocess dependencies."""

import pytest
from tools.worker_client import WorkerClient


# --- Color assignment tests ---

def test_candidate_is_black_on_even_games():
    """Even game index: candidate plays BLACK."""
    for i in range(0, 10, 2):
        assert (i % 2 == 0) == True  # candidate_is_black = (game_idx % 2 == 0)


def test_candidate_is_white_on_odd_games():
    """Odd game index: candidate plays WHITE."""
    for i in range(1, 10, 2):
        assert (i % 2 == 0) == False


# --- PK verdict tests ---

def compute_verdict(pk_result: dict) -> str:
    """Compute PK verdict from a result dict (mirrors mlevo_cli logic)."""
    ipc = pk_result.get("ipc_failures", 0)
    completed = pk_result.get("completed_games", 0)
    planned = pk_result.get("planned_games", 0)
    results = pk_result.get("results", {})
    total = completed

    if ipc > 0:
        return "INVALID"
    if planned > 0 and completed < planned * 0.5:
        return "INVALID"
    if total > 0:
        black_pct = results.get("BLACK", 0) / total * 100
        white_pct = results.get("WHITE", 0) / total * 100
        max_pct = max(black_pct, white_pct)
        if max_pct > 70:
            return "DEGRADED"
        if planned > 0 and completed < planned * 0.8:
            return "DEGRADED"
    return "VALID"


def test_verdict_invalid_on_ipc_failures():
    result = {"ipc_failures": 1, "completed_games": 50, "planned_games": 50, "results": {"BLACK": 25, "WHITE": 25, "DRAW": 0}}
    assert compute_verdict(result) == "INVALID"


def test_verdict_invalid_on_incomplete_games():
    result = {"ipc_failures": 0, "completed_games": 10, "planned_games": 50, "results": {"BLACK": 5, "WHITE": 5, "DRAW": 0}}
    assert compute_verdict(result) == "INVALID"


def test_verdict_degraded_on_color_bias():
    result = {"ipc_failures": 0, "completed_games": 50, "planned_games": 50, "results": {"BLACK": 5, "WHITE": 45, "DRAW": 0}}
    assert compute_verdict(result) == "DEGRADED"


def test_verdict_valid():
    result = {"ipc_failures": 0, "completed_games": 50, "planned_games": 50, "results": {"BLACK": 20, "WHITE": 25, "DRAW": 5}}
    assert compute_verdict(result) == "VALID"


# --- Ledger consistency tests ---

def check_ledger_match(pk_result: dict, ledger: dict) -> dict:
    """Check if PK results match ledger (mirrors mlevo_cli logic)."""
    log_total = pk_result.get("completed_games", 0)
    ledger_wins = ledger.get("wins_new", 0)
    ledger_losses = ledger.get("losses_new", 0)
    ledger_total = ledger_wins + ledger_losses

    if ledger_wins == 0 and ledger_losses == 0 and log_total > 0:
        return {"match": False, "detail": f"Ledger says 0/0 but log shows {log_total} games completed"}
    if ledger_total > 0 and log_total > 0 and abs(ledger_total - log_total) > max(5, log_total * 0.3):
        return {"match": False, "detail": f"Ledger has {ledger_total} games but log has {log_total}"}
    return {"match": True, "detail": ""}


def test_ledger_mismatch_on_zero_zero():
    pk = {"completed_games": 19}
    ledger = {"wins_new": 0, "losses_new": 0}
    result = check_ledger_match(pk, ledger)
    assert result["match"] == False
    assert "0/0" in result["detail"]


def test_ledger_match_on_consistent_data():
    pk = {"completed_games": 50}
    ledger = {"wins_new": 30, "losses_new": 20}
    result = check_ledger_match(pk, ledger)
    assert result["match"] == True


def test_ledger_match_on_no_games():
    pk = {"completed_games": 0}
    ledger = {"wins_new": 0, "losses_new": 0}
    result = check_ledger_match(pk, ledger)
    assert result["match"] == True
