#!/usr/bin/env python3
"""Integration tests for branch training and merging."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = PROJECT_ROOT / "ml"
CLI = [sys.executable, str(ML_DIR / "mlevo_cli.py")]
REGISTRY_PATH = ML_DIR / "data" / "model_registry.jsonl"
MODELS_DIR = ML_DIR / "data" / "models"


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


@pytest.fixture(autouse=True)
def clean_registry():
    """Back up registry before test, restore after."""
    backup = None
    if REGISTRY_PATH.exists():
        backup = REGISTRY_PATH.read_text()
    REGISTRY_PATH.unlink(missing_ok=True)
    yield
    # Restore original registry
    if backup is not None:
        REGISTRY_PATH.write_text(backup)
    else:
        REGISTRY_PATH.unlink(missing_ok=True)


def _seed_registry(records):
    """Write seed records to registry."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


class TestBranch:
    def test_create_branch(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        result = run_cli_json("branch", "--from", "aaa111", "--name", "exp-test")
        assert result.get("branch") == "exp-test"
        assert result.get("fork_from") == "aaa111"

    def test_branch_models(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "mainline",
             "winrate": 0.7, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        result = run_cli_json("models", "--branch", "mainline")
        assert result.get("count") == 2

    def test_models_filter_promoted(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "mainline",
             "winrate": 0.3, "promoted": False, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        result = run_cli_json("models", "--promoted", "True")
        assert result.get("count") == 1


class TestGraphWithEdges:
    def test_graph_with_branches(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "init", "hypothesis": "initial",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "mainline",
             "winrate": 0.7, "promoted": True, "params": {}, "change": "raise-lr", "hypothesis": "faster convergence",
             "timestamp": "", "file": ""},
            {"hash": "ccc333", "parent": "aaa111", "round": 2, "branch": "exp-lr",
             "winrate": 0.5, "promoted": False, "params": {}, "change": "test", "hypothesis": "test",
             "timestamp": "", "file": ""},
        ])
        graph = run_cli_json("graph", "--with-edges")
        assert graph.get("node_count") == 3
        assert len(graph.get("edges", [])) == 2
        assert "mainline" in graph.get("branches", {})
        assert "exp-lr" in graph.get("branches", {})

    def test_graph_topo(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "mainline",
             "winrate": 0.7, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        graph = run_cli_json("graph", "--topo")
        assert "topo_order" in graph
        assert graph["topo_order"] == ["aaa111", "bbb222"]


class TestModelDetails:
    def test_model_detail(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {"tr_lr": 0.002},
             "change": "init", "hypothesis": "initial", "timestamp": "2026-06-07", "file": "models/aaa111.bin.gz"},
        ])
        result = run_cli_json("model", "--hash", "aaa111")
        assert result.get("hash") == "aaa111"
        assert result.get("winrate") == 0.9

    def test_model_history(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "init", "hypothesis": "initial",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "mainline",
             "winrate": 0.7, "promoted": True, "params": {}, "change": "raise-lr", "hypothesis": "faster",
             "timestamp": "", "file": ""},
            {"hash": "ccc333", "parent": "bbb222", "round": 3, "branch": "mainline",
             "winrate": 0.8, "promoted": True, "params": {}, "change": "more-data", "hypothesis": "diversity",
             "timestamp": "", "file": ""},
        ])
        result = run_cli_json("history", "--model", "ccc333")
        assert len(result.get("lineage", [])) == 3
        assert result["lineage"][0]["hypothesis"] == "initial"
        assert result["lineage"][-1]["hash"] == "ccc333"


class TestMerge:
    def test_merge_branch(self):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.5, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
            {"hash": "bbb222", "parent": "aaa111", "round": 2, "branch": "exp-lr",
             "winrate": 0.8, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        result = run_cli_json("merge", "--winner", "exp-lr")
        assert result.get("status") == "merged"
        assert result.get("winner_branch") == "exp-lr"
