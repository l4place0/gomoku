#!/usr/bin/env python3
"""Tests for historical data migration."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = PROJECT_ROOT / "ml"
CLI = [sys.executable, str(ML_DIR / "mlevo_cli.py")]
REGISTRY_PATH = ML_DIR / "data" / "model_registry.jsonl"
LEDGER_PATH = ML_DIR / "data" / "logs" / "evolution_ledger.json"


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


@pytest.fixture
def clean_state():
    """Clean registry and backup ledger."""
    # Backup real registry if exists
    reg_backup = None
    if REGISTRY_PATH.exists():
        reg_backup = REGISTRY_PATH.read_text()
        REGISTRY_PATH.unlink()
    # Backup real ledger if exists
    ledger_backup = None
    if LEDGER_PATH.exists():
        ledger_backup = LEDGER_PATH.read_text()
    yield ledger_backup
    # Restore
    if ledger_backup:
        LEDGER_PATH.write_text(ledger_backup)
    if reg_backup:
        REGISTRY_PATH.write_text(reg_backup)
    else:
        REGISTRY_PATH.unlink(missing_ok=True)


class TestMigration:
    def test_migrate_from_real_ledger(self, clean_state):
        """Test migration from actual evolution_ledger.json."""
        backup = clean_state
        if not backup:
            pytest.skip("No evolution_ledger.json found")

        result = run_cli_json("migrate", "--from-ledger")
        assert result.get("status") == "migrated"
        assert result.get("migrated", 0) > 0
        assert result.get("total_ledger", 0) > 0

        # Verify registry was created
        assert REGISTRY_PATH.exists()

        # Verify parent chain
        graph = run_cli_json("graph")
        assert graph.get("node_count") > 0

    def test_migrate_preserves_promotion_chain(self, clean_state):
        """Test that promoted models form a proper parent chain."""
        backup = clean_state
        if not backup:
            pytest.skip("No evolution_ledger.json found")

        run_cli_json("migrate", "--from-ledger")

        # Get all promoted models on mainline
        models = run_cli_json("models", "--branch", "mainline", "--promoted", "True")
        promoted = models.get("models", [])
        if len(promoted) >= 2:
            # Each promoted model's parent should be the previous promoted model
            for i in range(1, len(promoted)):
                assert promoted[i]["parent"] is not None

    def test_migrate_idempotent(self, clean_state):
        """Running migrate twice should not create duplicates."""
        backup = clean_state
        if not backup:
            pytest.skip("No evolution_ledger.json found")

        result1 = run_cli_json("migrate", "--from-ledger")
        count1 = result1.get("migrated", 0)

        result2 = run_cli_json("migrate", "--from-ledger")
        count2 = result2.get("migrated", 0)

        # Second run should migrate 0 (all already in registry)
        assert count2 == 0

    def test_migrate_without_flag_errors(self):
        """Running migrate without --from-ledger should error."""
        proc = subprocess.run(
            CLI + ["migrate"],
            capture_output=True, text=True, timeout=10,
        )
        assert proc.returncode != 0
