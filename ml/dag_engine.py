#!/usr/bin/env python3
"""dag_engine.py — DAG graph engine for model lineage.

Builds a directed acyclic graph from model_registry records.
Supports topological sort, branch creation, edge management, and graph export.
"""

import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ml.model_registry import ModelRecord, ModelRegistry


class DAGEngine:
    """DAG engine built on top of ModelRegistry."""

    def __init__(self, registry: ModelRegistry):
        self.registry = registry

    def build_graph(self) -> dict:
        """Build adjacency list from registry. Returns {hash: [child_hash, ...]}."""
        records = self.registry.read_all()
        children = defaultdict(list)
        all_hashes = set()
        for r in records:
            all_hashes.add(r.hash)
            if r.parent:
                children[r.parent].append(r.hash)
        return {"children": dict(children), "all_hashes": all_hashes}

    def topological_sort(self) -> list[ModelRecord]:
        """Return records in topological order (parents before children)."""
        records = self.registry.read_all()
        if not records:
            return []

        # Build in-degree map
        record_map = {r.hash: r for r in records}
        in_degree = {r.hash: 0 for r in records}
        children = defaultdict(list)

        for r in records:
            if r.parent and r.parent in record_map:
                children[r.parent].append(r.hash)
                in_degree[r.hash] += 1

        # Kahn's algorithm
        queue = deque(h for h, deg in in_degree.items() if deg == 0)
        result = []
        while queue:
            h = queue.popleft()
            result.append(record_map[h])
            for child in children.get(h, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(records):
            raise ValueError("Cycle detected in DAG")

        return result

    def create_branch(
        self,
        fork_from_hash: str,
        param_slug: str = "",
        branch_name: Optional[str] = None,
    ) -> str:
        """Create a new branch from a model. Returns branch name."""
        fork_model = self.registry.find_by_hash(fork_from_hash)
        if not fork_model:
            raise ValueError(f"Model {fork_from_hash} not found")

        if not branch_name:
            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            slug = param_slug or "exp"
            branch_name = f"branch-{date_str}-{slug}"

        return branch_name

    def create_edge(
        self,
        from_hash: str,
        to_hash: str,
        change: str = "",
        hypothesis: str = "",
        param_diff: Optional[dict] = None,
        result: Optional[dict] = None,
    ) -> dict:
        """Create an edge record (stored as part of the child model's registry entry)."""
        edge = {
            "from": from_hash,
            "to": to_hash,
            "change": change,
            "hypothesis": hypothesis,
            "param_diff": param_diff or {},
            "result": result or {},
        }
        return edge

    def get_edges(self, include_all: bool = False) -> list[dict]:
        """Get all edges from the registry (parent→child relationships)."""
        records = self.registry.read_all()
        edges = []
        for r in records:
            if r.parent:
                edges.append({
                    "from": r.parent,
                    "to": r.hash,
                    "change": r.change,
                    "hypothesis": r.hypothesis,
                    "param_diff": r.params,
                    "branch": r.branch,
                })
        return edges

    def export_graph(self, with_edges: bool = False) -> dict:
        """Export graph as JSON-serializable dict."""
        records = self.registry.read_all()
        nodes = []
        for r in records:
            nodes.append({
                "hash": r.hash,
                "parent": r.parent,
                "round": r.round,
                "branch": r.branch,
                "winrate": r.winrate,
                "promoted": r.promoted,
                "change": r.change,
                "hypothesis": r.hypothesis,
                "timestamp": r.timestamp,
                "file": r.file,
            })

        result = {
            "nodes": nodes,
            "node_count": len(nodes),
        }

        if with_edges:
            result["edges"] = self.get_edges()

        # Identify mainline and branches
        branches = defaultdict(list)
        for r in records:
            branches[r.branch].append(r.hash)
        result["branches"] = dict(branches)
        result["root"] = next((r.hash for r in records if r.parent is None), None)

        return result

    def get_history(self, model_hash: str) -> list[dict]:
        """Get the full experiment chain for a model (oldest first)."""
        chain = self.registry.get_parent_chain(model_hash)
        history = []
        for r in chain:
            history.append({
                "hash": r.hash,
                "round": r.round,
                "winrate": r.winrate,
                "promoted": r.promoted,
                "change": r.change,
                "hypothesis": r.hypothesis,
            })
        return history

    def get_branches(self) -> dict:
        """Get branch summary."""
        records = self.registry.read_all()
        branches = defaultdict(lambda: {"models": [], "rounds": 0, "latest_winrate": 0, "archived": False})
        for r in records:
            b = branches[r.branch]
            b["models"].append(r.hash)
            b["rounds"] = max(b["rounds"], r.round)
            b["latest_winrate"] = r.winrate
        return dict(branches)

    def get_branch_elo_summary(self) -> dict:
        """Get branch-level Elo summary.

        Returns {branch: {avg_elo, best_elo, best_model, model_count}}.
        """
        records = self.registry.read_all()
        branches = defaultdict(lambda: {"elos": [], "best_elo": None, "best_model": None})
        for r in records:
            b = branches[r.branch]
            if r.elo is not None:
                b["elos"].append(r.elo)
                if b["best_elo"] is None or r.elo > b["best_elo"]:
                    b["best_elo"] = r.elo
                    b["best_model"] = r.hash
        result = {}
        for branch, data in branches.items():
            elos = data["elos"]
            result[branch] = {
                "avg_elo": round(sum(elos) / len(elos), 1) if elos else None,
                "best_elo": round(data["best_elo"], 1) if data["best_elo"] is not None else None,
                "best_model": data["best_model"],
                "model_count": len(elos),
            }
        return result
