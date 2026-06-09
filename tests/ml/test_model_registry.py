#!/usr/bin/env python3
"""Unit tests for model_registry.py."""

import json
import tempfile
from pathlib import Path

import pytest

from ml.model_registry import ModelRecord, ModelRegistry, compute_model_hash, archive_model


@pytest.fixture
def tmp_registry(tmp_path):
    """Create a temporary registry for testing."""
    reg_path = tmp_path / "model_registry.jsonl"
    models_dir = tmp_path / "models"
    return ModelRegistry(registry_path=reg_path, models_dir=models_dir)


def _make_record(hash_val, parent=None, round_n=1, branch="mainline", winrate=0.5, promoted=False, change="", hypothesis=""):
    return ModelRecord(
        hash=hash_val,
        parent=parent,
        round=round_n,
        branch=branch,
        winrate=winrate,
        promoted=promoted,
        params={"tr_lr": 0.002},
        change=change,
        hypothesis=hypothesis,
        timestamp="2026-06-07T00:00:00Z",
        file=f"models/{hash_val}.bin.gz",
    )


class TestModelRecord:
    def test_roundtrip(self):
        rec = _make_record("abc123", parent=None, winrate=0.9)
        line = rec.to_json()
        restored = ModelRecord.from_json(line)
        assert restored.hash == "abc123"
        assert restored.parent is None
        assert restored.winrate == 0.9

    def test_json_format(self):
        rec = _make_record("abc123")
        data = json.loads(rec.to_json())
        assert "hash" in data
        assert "parent" in data
        assert "winrate" in data
        assert "promoted" in data


class TestModelRegistry:
    def test_append_and_read(self, tmp_registry):
        r1 = _make_record("aaa111")
        r2 = _make_record("bbb222", parent="aaa111")
        tmp_registry.append_record(r1)
        tmp_registry.append_record(r2)

        all_records = tmp_registry.read_all()
        assert len(all_records) == 2
        assert all_records[0].hash == "aaa111"
        assert all_records[1].hash == "bbb222"

    def test_find_by_hash(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111"))
        tmp_registry.append_record(_make_record("bbb222"))
        found = tmp_registry.find_by_hash("bbb222")
        assert found is not None
        assert found.hash == "bbb222"

    def test_find_by_hash_not_found(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111"))
        assert tmp_registry.find_by_hash("nonexistent") is None

    def test_find_by_branch(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", branch="mainline"))
        tmp_registry.append_record(_make_record("bbb222", branch="exp-lr"))
        tmp_registry.append_record(_make_record("ccc333", branch="mainline"))
        mainline = tmp_registry.find_by_branch("mainline")
        assert len(mainline) == 2

    def test_parent_chain(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", parent=None, round_n=1))
        tmp_registry.append_record(_make_record("bbb222", parent="aaa111", round_n=2))
        tmp_registry.append_record(_make_record("ccc333", parent="bbb222", round_n=3))
        chain = tmp_registry.get_parent_chain("ccc333")
        assert len(chain) == 3
        assert [r.hash for r in chain] == ["aaa111", "bbb222", "ccc333"]

    def test_cycle_detection(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", parent=None))
        tmp_registry.append_record(_make_record("bbb222", parent="aaa111"))
        with pytest.raises(ValueError, match="Cycle detected"):
            tmp_registry.append_record(_make_record("aaa111", parent="bbb222"))

    def test_no_cycle_on_valid_dag(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", parent=None))
        tmp_registry.append_record(_make_record("bbb222", parent="aaa111"))
        tmp_registry.append_record(_make_record("ccc333", parent="aaa111"))
        # Should not raise - two children of same parent is valid DAG
        assert len(tmp_registry.read_all()) == 3

    def test_get_latest_on_branch(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", branch="mainline", round_n=1))
        tmp_registry.append_record(_make_record("bbb222", branch="mainline", round_n=2))
        latest = tmp_registry.get_latest_on_branch("mainline")
        assert latest.hash == "bbb222"

    def test_get_latest_promoted(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", branch="mainline", winrate=0.9, promoted=True, round_n=1))
        tmp_registry.append_record(_make_record("bbb222", branch="mainline", winrate=0.4, promoted=False, round_n=2))
        tmp_registry.append_record(_make_record("ccc333", branch="mainline", winrate=0.7, promoted=True, round_n=3))
        latest_promoted = tmp_registry.get_latest_promoted("mainline")
        assert latest_promoted.hash == "ccc333"

    def test_filter_models(self, tmp_registry):
        tmp_registry.append_record(_make_record("aaa111", branch="mainline", winrate=0.9, promoted=True))
        tmp_registry.append_record(_make_record("bbb222", branch="exp-lr", winrate=0.3, promoted=False))
        tmp_registry.append_record(_make_record("ccc333", branch="mainline", winrate=0.6, promoted=False))

        assert len(tmp_registry.filter_models(branch="mainline")) == 2
        assert len(tmp_registry.filter_models(promoted=True)) == 1
        assert len(tmp_registry.filter_models(min_winrate=0.5)) == 2

    def test_empty_registry(self, tmp_registry):
        assert tmp_registry.read_all() == []
        assert tmp_registry.find_by_hash("anything") is None
        assert tmp_registry.get_latest_on_branch("mainline") is None


class TestComputeModelHash:
    def test_hash_consistency(self, tmp_path):
        model_file = tmp_path / "test_model.bin.gz"
        model_file.write_bytes(b"fake model data for testing")
        h1 = compute_model_hash(model_file)
        h2 = compute_model_hash(model_file)
        assert h1 == h2
        assert len(h1) == 12

    def test_different_files_different_hash(self, tmp_path):
        f1 = tmp_path / "model1.bin.gz"
        f2 = tmp_path / "model2.bin.gz"
        f1.write_bytes(b"model A")
        f2.write_bytes(b"model B")
        assert compute_model_hash(f1) != compute_model_hash(f2)


class TestArchiveModel:
    def test_archive(self, tmp_path):
        src = tmp_path / "source.bin.gz"
        src.write_bytes(b"model data")
        models_dir = tmp_path / "models"
        dst = archive_model(src, "abc123", models_dir)
        assert dst.exists()
        assert dst.name == "abc123.bin.gz"
        assert dst.read_bytes() == b"model data"
