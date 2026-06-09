#!/usr/bin/env python3
"""plan_registry.py — Training plan registry for hypergraph structure.

Stores plan-level metadata in plan_registry.jsonl.
Each record captures: plan name, best model, winrate, rounds, lineage (from_plan, from_model, hypothesis).
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY_PATH = BASE_DIR / "data" / "plan_registry.jsonl"


@dataclass
class PlanRecord:
    plan: str
    best_model: str  # hash of best model
    best_winrate: float
    rounds_completed: int
    rounds_total: int
    from_plan: Optional[str] = None  # parent plan name
    from_model: Optional[str] = None  # parent model hash
    hypothesis: str = ""
    model_kind: str = "b10c128"
    timestamp: str = ""
    status: str = "active"  # active | completed | archived

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "PlanRecord":
        data = json.loads(line)
        return cls(**data)


class PlanRegistry:
    """JSONL-backed plan registry."""

    def __init__(self, registry_path: Optional[Path] = None):
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH

    def append_record(self, record: PlanRecord) -> None:
        line = record.to_json() + "\n"
        with open(self.registry_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_all(self) -> list[PlanRecord]:
        records = []
        if not self.registry_path.exists():
            return records
        with open(self.registry_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(PlanRecord.from_json(line))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return records

    def find_by_name(self, name: str) -> Optional[PlanRecord]:
        for record in self.read_all():
            if record.plan == name:
                return record
        return None

    def update_record(self, name: str, **kwargs) -> bool:
        """Update a plan record by name. Returns True if found and updated."""
        records = self.read_all()
        found = False
        for r in records:
            if r.plan == name:
                for k, v in kwargs.items():
                    if hasattr(r, k):
                        setattr(r, k, v)
                found = True
                break
        if found:
            self._rewrite_all(records)
        return found

    def _rewrite_all(self, records: list[PlanRecord]) -> None:
        with open(self.registry_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(r.to_json() + "\n")

    def get_lineage(self, name: str) -> list[PlanRecord]:
        """Get the ancestry chain for a plan (oldest first)."""
        chain = []
        current = self.find_by_name(name)
        visited = set()
        while current and current.plan not in visited:
            chain.append(current)
            visited.add(current.plan)
            if current.from_plan:
                current = self.find_by_name(current.from_plan)
            else:
                break
        chain.reverse()
        return chain
