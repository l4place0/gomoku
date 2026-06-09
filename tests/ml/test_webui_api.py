#!/usr/bin/env python3
"""Tests for WebUI FastAPI backend."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ML_DIR = PROJECT_ROOT / "ml"
REGISTRY_PATH = ML_DIR / "data" / "model_registry.jsonl"

# Import FastAPI test client
try:
    from fastapi.testclient import TestClient
    from ml.webui.app import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

pytestmark = pytest.mark.skipif(not HAS_FASTAPI, reason="FastAPI not installed")


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_registry():
    """Back up registry before test, restore after."""
    backup = None
    if REGISTRY_PATH.exists():
        backup = REGISTRY_PATH.read_text()
        REGISTRY_PATH.unlink()
    yield
    if backup is not None:
        REGISTRY_PATH.write_text(backup)
    else:
        REGISTRY_PATH.unlink(missing_ok=True)


def _seed_registry(records):
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")


class TestStatusAPI:
    def test_status(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipeline_state" in data


class TestProgressAPI:
    def test_progress(self, client):
        resp = client.get("/api/progress")
        assert resp.status_code == 200
        data = resp.json()
        assert "stage" in data


class TestGraphAPI:
    def test_graph_empty(self, client):
        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data

    def test_graph_with_edges(self, client):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "init", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        resp = client.get("/api/graph?with_edges=true")
        assert resp.status_code == 200
        data = resp.json()
        assert "edges" in data


class TestModelsAPI:
    def test_models_empty(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_model_by_hash(self, client):
        _seed_registry([
            {"hash": "aaa111", "parent": None, "round": 1, "branch": "mainline",
             "winrate": 0.9, "promoted": True, "params": {}, "change": "", "hypothesis": "",
             "timestamp": "", "file": ""},
        ])
        resp = client.get("/api/models/aaa111")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hash"] == "aaa111"


class TestRunAPI:
    @pytest.mark.skip(reason="Requires actual training infra (GPU + automl_cli binary)")
    def test_run_endpoint_exists(self, client):
        resp = client.post("/api/run", json={"round": 900, "preset": "tiny"})
        assert resp.status_code in (200, 500)


class TestSchemaAPI:
    def test_schema(self, client):
        resp = client.get("/api/schema")
        assert resp.status_code == 200
        data = resp.json()
        assert "commands" in data


class TestLogsAPI:
    def test_logs(self, client):
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
