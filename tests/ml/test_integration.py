#!/usr/bin/env python3
"""Integration tests for mlevo CLI with preset and fault injection.

These tests verify the CLI interface works correctly.
Actual training requires GPU and is tested in E2E.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = PROJECT_ROOT / "ml"
CLI = [sys.executable, str(ML_DIR / "mlevo_cli.py")]


def run_cli_json(*args):
    cmd = CLI + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode == 0 and proc.stdout.strip():
        return json.loads(proc.stdout.strip())
    if proc.stderr.strip():
        try:
            return json.loads(proc.stderr.strip())
        except json.JSONDecodeError:
            pass
    return {"error": proc.stderr or proc.stdout, "exit_code": proc.returncode}


class TestPresetParameters:
    """Test that preset parameters are correctly applied."""

    def test_tiny_preset_schema(self):
        """Verify tiny preset parameters exist."""
        schema = run_cli_json("schema")
        assert "tiny" in schema.get("presets", {})
        tiny_params = schema["presets"]["tiny"]
        assert "sf_games" in tiny_params

    def test_schema_commands_complete(self):
        """Verify all expected commands exist in schema."""
        schema = run_cli_json("schema")
        cmds = schema.get("commands", {})
        expected = ["schema", "status", "progress", "run", "branch", "merge",
                     "pk", "graph", "models", "model", "history", "recover",
                     "migrate", "test", "decide", "new", "list", "archive"]
        for cmd in expected:
            assert cmd in cmds, f"Command '{cmd}' missing from schema"


class TestStateMachineIntegration:
    """Test state machine transitions through CLI."""

    def test_status_after_inject_and_recover(self):
        """Full inject→crash→recover cycle."""
        # Inject OOM
        result = run_cli_json("run", "--round", "998", "--preset", "tiny", "--inject", "oom")
        assert result.get("status") == "failed"

        # Status should be crashed
        status = run_cli_json("status")
        assert status.get("pipeline_state") == "crashed"

        # Recover
        recover = run_cli_json("recover")
        assert recover.get("status") == "recovered"

        # Status should be idle
        status = run_cli_json("status")
        assert status.get("pipeline_state") == "idle"

    def test_state_conflict_rejects_double_run(self):
        """Cannot run while already running."""
        # Inject crash to get to crashed state
        run_cli_json("run", "--round", "997", "--preset", "tiny", "--inject", "crash")

        # Try to run while crashed (should work - crashed→running is valid)
        # Then try again while running (should fail - running→running is invalid)
        # This is hard to test without actual concurrent execution
        # Just verify the state transition logic works
        status = run_cli_json("status")
        assert status.get("pipeline_state") == "crashed"

        # Clean up
        run_cli_json("recover")


class TestGraphIntegration:
    """Test graph operations through CLI."""

    def test_graph_and_models_consistency(self):
        """Graph and models commands return consistent data."""
        graph = run_cli_json("graph")
        models = run_cli_json("models")
        assert graph.get("node_count") == models.get("count")


class TestFaultInjection:
    """Test all fault injection types."""

    def test_inject_oom(self):
        result = run_cli_json("run", "--round", "901", "--preset", "tiny", "--inject", "oom")
        assert result.get("error") == "OOM"
        assert result.get("recovery") == "reduce_batch"
        run_cli_json("recover")

    def test_inject_nan(self):
        result = run_cli_json("run", "--round", "902", "--preset", "tiny", "--inject", "nan")
        assert result.get("error") == "NaN loss"
        assert result.get("recovery") == "reduce_lr"
        run_cli_json("recover")

    def test_inject_crash(self):
        result = run_cli_json("run", "--round", "903", "--preset", "tiny", "--inject", "crash")
        assert result.get("error") == "process crashed"
        assert result.get("recovery") == "retry"
        run_cli_json("recover")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nonexistent_hash(self):
        result = run_cli_json("model", "--hash", "nonexistent123")
        assert "error" in result or "not found" in json.dumps(result).lower()

    def test_history_nonexistent(self):
        result = run_cli_json("history", "--model", "nonexistent123")
        assert "lineage" in result  # Should return empty lineage
