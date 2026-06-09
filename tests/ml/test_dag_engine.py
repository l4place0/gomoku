#!/usr/bin/env python3
"""Unit tests for dag_engine.py."""

from pathlib import Path

import pytest

from ml.model_registry import ModelRecord, ModelRegistry
from ml.dag_engine import DAGEngine


@pytest.fixture
def dag(tmp_path):
    reg_path = tmp_path / "model_registry.jsonl"
    models_dir = tmp_path / "models"
    registry = ModelRegistry(registry_path=reg_path, models_dir=models_dir)
    return DAGEngine(registry), registry


def _make_record(hash_val, parent=None, round_n=1, branch="mainline", winrate=0.5, promoted=False, change="", hypothesis=""):
    return ModelRecord(
        hash=hash_val, parent=parent, round=round_n, branch=branch,
        winrate=winrate, promoted=promoted, params={"tr_lr": 0.002},
        change=change, hypothesis=hypothesis,
        timestamp="2026-06-07T00:00:00Z", file=f"models/{hash_val}.bin.gz",
    )


class TestTopologicalSort:
    def test_linear_chain(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1))
        registry.append_record(_make_record("b", parent="a", round_n=2))
        registry.append_record(_make_record("c", parent="b", round_n=3))
        sorted_records = engine.topological_sort()
        hashes = [r.hash for r in sorted_records]
        assert hashes == ["a", "b", "c"]

    def test_branching_dag(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1))
        registry.append_record(_make_record("b", parent="a", round_n=2, branch="mainline"))
        registry.append_record(_make_record("c", parent="a", round_n=2, branch="exp-lr"))
        sorted_records = engine.topological_sort()
        hashes = [r.hash for r in sorted_records]
        assert hashes.index("a") < hashes.index("b")
        assert hashes.index("a") < hashes.index("c")

    def test_empty_registry(self, dag):
        engine, _ = dag
        assert engine.topological_sort() == []


class TestCreateBranch:
    def test_create_branch(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None))
        branch_name = engine.create_branch("a", param_slug="lr-high")
        assert "branch-" in branch_name
        assert "lr-high" in branch_name

    def test_create_branch_custom_name(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None))
        branch_name = engine.create_branch("a", branch_name="my-experiment")
        assert branch_name == "my-experiment"

    def test_create_branch_from_nonexistent(self, dag):
        engine, _ = dag
        with pytest.raises(ValueError, match="not found"):
            engine.create_branch("nonexistent")


class TestEdgeManagement:
    def test_create_edge(self, dag):
        engine, _ = dag
        edge = engine.create_edge(
            from_hash="a", to_hash="b",
            change="test-change", hypothesis="test hypothesis",
            param_diff={"tr_lr": {"old": 0.002, "new": 0.003}},
            result={"winrate": 0.7, "promoted": True},
        )
        assert edge["from"] == "a"
        assert edge["to"] == "b"
        assert edge["change"] == "test-change"

    def test_get_edges(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1))
        registry.append_record(_make_record("b", parent="a", round_n=2, change="test-change"))
        edges = engine.get_edges()
        assert len(edges) == 1
        assert edges[0]["from"] == "a"
        assert edges[0]["to"] == "b"
        assert edges[0]["change"] == "test-change"


class TestExportGraph:
    def test_export_basic(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1))
        registry.append_record(_make_record("b", parent="a", round_n=2))
        graph = engine.export_graph()
        assert graph["node_count"] == 2
        assert graph["root"] == "a"
        assert "mainline" in graph["branches"]

    def test_export_with_edges(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1))
        registry.append_record(_make_record("b", parent="a", round_n=2))
        graph = engine.export_graph(with_edges=True)
        assert "edges" in graph
        assert len(graph["edges"]) == 1

    def test_export_empty(self, dag):
        engine, _ = dag
        graph = engine.export_graph()
        assert graph["node_count"] == 0
        assert graph["root"] is None


class TestGetHistory:
    def test_history(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, round_n=1, hypothesis="initial"))
        registry.append_record(_make_record("b", parent="a", round_n=2, hypothesis="raise lr"))
        registry.append_record(_make_record("c", parent="b", round_n=3, hypothesis="more data"))
        history = engine.get_history("c")
        assert len(history) == 3
        assert [h["hash"] for h in history] == ["a", "b", "c"]
        assert history[0]["hypothesis"] == "initial"


class TestGetBranches:
    def test_branches(self, dag):
        engine, registry = dag
        registry.append_record(_make_record("a", parent=None, branch="mainline", round_n=1))
        registry.append_record(_make_record("b", parent="a", branch="mainline", round_n=2))
        registry.append_record(_make_record("c", parent="a", branch="exp-lr", round_n=2))
        branches = engine.get_branches()
        assert "mainline" in branches
        assert "exp-lr" in branches
        assert branches["mainline"]["rounds"] == 2
