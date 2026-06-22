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


class TestMarkdownAPI:
    def test_markdown_invalid_file(self, client):
        resp = client.get("/api/changes/some-plan/markdown/secrets.json")
        assert resp.status_code == 400
        assert "Invalid filename" in resp.json()["detail"]

    def test_markdown_missing_file(self, client):
        resp = client.get("/api/changes/non-existent-plan/markdown/proposal.md")
        assert resp.status_code == 404

    def test_markdown_active_proposal(self, client):
        import shutil
        from ml.webui.app import ML_DIR
        
        plan_name = "test-temp-active-plan"
        filename = "proposal.md"
        content = "# Active Proposal Content"
        
        # Write to active changes directory
        active_dir = ML_DIR.parent / "docs" / "ml" / "changes" / plan_name
        active_dir.mkdir(parents=True, exist_ok=True)
        file_path = active_dir / filename
        file_path.write_text(content, encoding="utf-8")
        
        try:
            resp = client.get(f"/api/changes/{plan_name}/markdown/{filename}")
            assert resp.status_code == 200
            assert resp.json()["content"] == content
        finally:
            shutil.rmtree(active_dir, ignore_errors=True)

    def test_markdown_archived_conclusion(self, client):
        import shutil
        from ml.webui.app import ML_DIR
        
        plan_name = "test-temp-archived-plan"
        filename = "conclusion.md"
        content = "# Archived Conclusion Content"
        
        # Write to archived changes directory
        archive_dir = ML_DIR.parent / "docs" / "ml" / "changes" / "archive" / f"2026-06-14-{plan_name}"
        archive_dir.mkdir(parents=True, exist_ok=True)
        file_path = archive_dir / filename
        file_path.write_text(content, encoding="utf-8")
        
        try:
            resp = client.get(f"/api/changes/{plan_name}/markdown/{filename}")
            assert resp.status_code == 200
            assert resp.json()["content"] == content
        finally:
            shutil.rmtree(archive_dir, ignore_errors=True)


class TestSingleServer:
    def test_serve_spa_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "html" in resp.text.lower()

    def test_serve_spa_routing(self, client):
        resp = client.get("/graph")
        assert resp.status_code == 200
        assert "html" in resp.text.lower()

    def test_unmatched_api_returns_404(self, client):
        resp = client.get("/api/nonexistent-route")
        assert resp.status_code == 404


