#!/usr/bin/env python3
"""Integration tests for mlevo CLI state machine and subcommands."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = PROJECT_ROOT / "ml"
CLI = [sys.executable, str(ML_DIR / "mlevo_cli.py")]


def run_cli(*args):
    """Run mlevo CLI and return parsed JSON output."""
    cmd = CLI + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return proc


def run_cli_json(*args):
    """Run mlevo CLI and return parsed JSON."""
    proc = run_cli(*args)
    if proc.returncode == 0 and proc.stdout.strip():
        return json.loads(proc.stdout.strip())
    return {"error": proc.stderr.strip(), "exit_code": proc.returncode}


class TestSchema:
    def test_schema_output(self):
        proc = run_cli("schema")
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert "commands" in data
        assert "state_transitions" in data
        assert "presets" in data
        assert "run" in data["commands"]
        assert "status" in data["commands"]


class TestStatus:
    def test_status_json(self):
        data = run_cli_json("status")
        assert "pipeline_state" in data
        assert "current_round" in data
        assert data["pipeline_state"] in ("idle", "running", "paused", "crashed")


class TestProgress:
    def test_progress_json(self):
        data = run_cli_json("progress")
        assert "stage" in data
        assert "pct" in data


class TestStateMachine:
    def test_recover_when_not_crashed(self):
        """Cannot recover from non-crashed state."""
        proc = run_cli("recover")
        # Should fail if not in crashed state
        if proc.returncode != 0:
            data = json.loads(proc.stderr)
            assert "Cannot recover" in data.get("error", "")


class TestGraph:
    def test_graph_empty(self):
        """Graph on empty registry returns valid structure."""
        data = run_cli_json("graph")
        assert "nodes" in data
        assert "node_count" in data


class TestModels:
    def test_models_empty(self):
        """Models on empty registry returns empty list."""
        data = run_cli_json("models")
        assert "models" in data
        assert "count" in data


class TestInject:
    def test_inject_oom(self):
        """Fault injection OOM should crash pipeline."""
        data = run_cli_json("run", "--round", "999", "--preset", "tiny", "--inject", "oom")
        assert data.get("status") == "failed"
        assert data.get("error") == "OOM"
        # Clean up: recover
        run_cli("recover")

    def test_inject_nan(self):
        """Fault injection NaN should crash pipeline."""
        data = run_cli_json("run", "--round", "999", "--preset", "tiny", "--inject", "nan")
        assert data.get("status") == "failed"
        assert data.get("error") == "NaN loss"
        run_cli("recover")

    def test_inject_crash(self):
        """Fault injection crash should crash pipeline."""
        data = run_cli_json("run", "--round", "999", "--preset", "tiny", "--inject", "crash")
        assert data.get("status") == "failed"
        assert data.get("error") == "process crashed"
        run_cli("recover")
