import sys
import os
import pytest
import json
import shutil
import re
from pathlib import Path

from ml.mlevo_cli import DecisionEngine, cmd_new, find_plan, load_ledger, CHANGES_DIR, ARCHIVE_DIR

@pytest.fixture
def base_config():
    return {
        "sf_games": 500,
        "sf_visits": 96,
        "sh_samples": 150000,
        "tr_lr": 0.002,
        "tr_batch": 64,
        "pk_games": 20
    }

def test_decision_engine_entropy_boost(base_config):
    # History showing previous round (Round 1) failed promotion
    history = [
        {
            "round": 1,
            "pk": {
                "winrate": 0.35,
                "promoted": False
            }
        }
    ]
    engine = DecisionEngine(base_config, history)
    decided, reasons, warnings = engine.decide(next_round=2)

    # Entropy boost should trigger: sf_games * 1.2, sf_visits + 16
    assert decided["sf_games"] == 600
    assert decided["sf_visits"] == 112
    # Ensure reason is recorded
    assert any("Entropy boost" in r for r in reasons)
    assert not warnings

def test_decision_engine_no_entropy_boost_on_success(base_config):
    # History showing previous round promoted successfully
    history = [
        {
            "round": 1,
            "pk": {
                "winrate": 0.65,
                "promoted": True
            }
        }
    ]
    engine = DecisionEngine(base_config, history)
    decided, reasons, warnings = engine.decide(next_round=2)

    # sf_games and sf_visits should remain baseline
    assert decided["sf_games"] == 500
    assert decided["sf_visits"] == 96
    assert any("Entropy boost not triggered" in r for r in reasons)

def test_decision_engine_lr_decay_plateau(base_config):
    history = []
    # Mock log showing small loss difference across epochs (e.g. 5.12 to 5.11 -> diff 0.01 < 0.05)
    log_contents = {
        1: """
        BEGINNING NEXT EPOCH 0
        loss = 5.120000
        BEGINNING NEXT EPOCH 1
        loss = 5.110000
        """
    }
    engine = DecisionEngine(base_config, history, log_contents=log_contents)
    decided, reasons, warnings = engine.decide(next_round=2)

    # tr_lr should be decayed by 50%
    assert decided["tr_lr"] == 0.001
    assert any("LR decay" in r for r in reasons)

def test_decision_engine_no_lr_decay_on_large_diff(base_config):
    history = []
    # Mock log showing large loss difference across epochs (e.g. 5.25 to 5.05 -> diff 0.20 >= 0.05)
    log_contents = {
        1: """
        BEGINNING NEXT EPOCH 0
        loss = 5.250000
        BEGINNING NEXT EPOCH 1
        loss = 5.050000
        """
    }
    engine = DecisionEngine(base_config, history, log_contents=log_contents)
    decided, reasons, warnings = engine.decide(next_round=2)

    # tr_lr should remain baseline
    assert decided["tr_lr"] == 0.002
    assert any("LR decay not triggered" in r for r in reasons)

def test_decision_engine_crash_recovery_oom(base_config):
    history = []
    log_contents = {
        1: """
        Some normal lines...
        RuntimeError: CUDA out of memory. Tried to allocate...
        """
    }
    engine = DecisionEngine(base_config, history, log_contents=log_contents)
    decided, reasons, warnings = engine.decide(next_round=2)

    # Batch size should be halved
    assert decided["tr_batch"] == 32
    assert any("OOM recovery" in r for r in reasons)

def test_decision_engine_crash_recovery_nan(base_config):
    history = []
    log_contents = {
        1: """
        loss = NaN
        """
    }
    engine = DecisionEngine(base_config, history, log_contents=log_contents)
    decided, reasons, warnings = engine.decide(next_round=2)

    # tr_lr should be halved
    assert decided["tr_lr"] == 0.001
    assert any("NaN recovery" in r for r in reasons)

def test_decision_engine_guardrails(base_config):
    # Config violating guardrails
    bad_config = {
        "sf_games": 50,      # < 100
        "sf_visits": 96,
        "sh_samples": 20000, # < 50000
        "tr_lr": 0.002,
        "tr_batch": 64,
        "pk_games": 10       # < 20
    }
    engine = DecisionEngine(bad_config, [])
    decided, reasons, warnings = engine.decide(next_round=1)

    assert len(warnings) == 2
    assert any("sf_games (50) below recommended" in w for w in warnings)
    assert any("pk_games (10) below recommended" in w for w in warnings)

def test_scaffold_new_plan(tmp_path, monkeypatch):
    # Mock CHANGES_DIR to a temporary folder
    temp_plans_dir = tmp_path / "changes"
    monkeypatch.setattr("ml.mlevo_cli.CHANGES_DIR", temp_plans_dir)
    monkeypatch.setattr("ml.mlevo_cli.ARCHIVE_DIR", temp_plans_dir / "archive")
    monkeypatch.setattr("ml.mlevo_cli.get_plan_dir", lambda name: temp_plans_dir / name)

    class Args:
        name = "test-plan"

    cmd_new(Args())

    plan_dir = temp_plans_dir / "test-plan"
    assert plan_dir.exists()
    assert (plan_dir / "training_plan.json").exists()

    # Verify content of training_plan.json
    plan_config = json.loads((plan_dir / "training_plan.json").read_text(encoding="utf-8"))
    assert plan_config["plan_name"] == "test-plan"
    assert plan_config["total_rounds"] == 5
    assert plan_config["stages"][0]["config"]["sf_games"] == 500
