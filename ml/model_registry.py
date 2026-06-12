#!/usr/bin/env python3
"""model_registry.py — Model version registry with DAG lineage tracking.

Stores model records in a JSONL file (model_registry.jsonl).
Each record captures: hash, parent, round, branch, winrate, promoted,
params, change, hypothesis, timestamp, file path.
"""

import hashlib
import json
import os
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_REGISTRY_PATH = BASE_DIR / "data" / "model_registry.jsonl"
DEFAULT_MODELS_DIR = BASE_DIR / "data" / "models"


@dataclass
class ModelRecord:
    hash: str
    parent: Optional[str]  # None for root models
    round: int
    branch: str  # "mainline" or branch name
    winrate: float
    promoted: bool
    params: dict = field(default_factory=dict)
    change: str = ""  # OpenSpec change name
    hypothesis: str = ""
    timestamp: str = ""  # ISO 8601
    file: str = ""  # relative path to model file
    sprt_result: Optional[dict] = None  # SPRT evaluation result

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "ModelRecord":
        data = json.loads(line)
        # Handle missing fields for backward compatibility
        if "sprt_result" not in data:
            data["sprt_result"] = None
        return cls(**data)


def compute_model_hash(file_path: Path) -> str:
    """Compute SHA256 of a model file, return first 12 hex chars."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def archive_model(src_path: Path, model_hash: str, models_dir: Optional[Path] = None) -> Path:
    """Copy model file to models/{hash}.bin.gz. Returns destination path."""
    dst_dir = models_dir or DEFAULT_MODELS_DIR
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{model_hash}.bin.gz"
    shutil.copy2(str(src_path), str(dst))
    return dst


class ModelRegistry:
    """JSONL-backed model registry with DAG lineage tracking."""

    def __init__(self, registry_path: Optional[Path] = None, models_dir: Optional[Path] = None):
        self.registry_path = registry_path or DEFAULT_REGISTRY_PATH
        self.models_dir = models_dir or DEFAULT_MODELS_DIR

    def append_record(self, record: ModelRecord) -> None:
        """Append a record to the registry (atomic write)."""
        # Validate no cycle before writing
        if record.parent is not None:
            self._check_cycle(record.hash, record.parent)
        line = record.to_json() + "\n"
        with open(self.registry_path, "a", encoding="utf-8") as f:
            f.write(line)

    def read_all(self) -> list[ModelRecord]:
        """Read all records from registry."""
        records = []
        if not self.registry_path.exists():
            return records
        with open(self.registry_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(ModelRecord.from_json(line))
                    except (json.JSONDecodeError, TypeError):
                        continue
        return records

    def find_by_hash(self, model_hash: str) -> Optional[ModelRecord]:
        """Find a record by hash."""
        for record in self.read_all():
            if record.hash == model_hash:
                return record
        return None

    def find_by_branch(self, branch: str) -> list[ModelRecord]:
        """Find all records belonging to a branch."""
        return [r for r in self.read_all() if r.branch == branch]

    def get_parent_chain(self, model_hash: str) -> list[ModelRecord]:
        """Get the full ancestor chain for a model (oldest first)."""
        chain = []
        current = self.find_by_hash(model_hash)
        visited = set()
        while current and current.hash not in visited:
            chain.append(current)
            visited.add(current.hash)
            if current.parent:
                current = self.find_by_hash(current.parent)
            else:
                break
        chain.reverse()
        return chain

    def _check_cycle(self, new_hash: str, parent_hash: str) -> None:
        """Raise ValueError if setting parent would create a cycle."""
        # Walk from parent to root, check if new_hash appears
        current_hash = parent_hash
        visited = set()
        while current_hash:
            if current_hash == new_hash:
                raise ValueError(f"Cycle detected: setting parent of {new_hash} to {parent_hash} would create a cycle")
            if current_hash in visited:
                break
            visited.add(current_hash)
            record = self.find_by_hash(current_hash)
            if record and record.parent:
                current_hash = record.parent
            else:
                break

    def get_latest_on_branch(self, branch: str) -> Optional[ModelRecord]:
        """Get the most recent model on a branch."""
        branch_records = self.find_by_branch(branch)
        if not branch_records:
            return None
        return branch_records[-1]

    def get_latest_promoted(self, branch: str = "mainline") -> Optional[ModelRecord]:
        """Get the most recently promoted model on a branch."""
        promoted = [r for r in self.find_by_branch(branch) if r.promoted]
        if not promoted:
            return None
        return promoted[-1]

    def get_lr_history(self, branch: str, last_n: int = 10) -> list[dict]:
        """Get lr history for a branch.

        Returns list of dicts with round, tr_lr, promoted fields.
        """
        records = self.find_by_branch(branch)[-last_n:]
        return [
            {
                "round": r.round,
                "tr_lr": r.params.get("tr_lr"),
                "promoted": r.promoted,
                "winrate": r.winrate,
            }
            for r in records
        ]

    def filter_models(
        self,
        branch: Optional[str] = None,
        promoted: Optional[bool] = None,
        min_winrate: Optional[float] = None,
    ) -> list[ModelRecord]:
        """Filter models by criteria."""
        results = self.read_all()
        if branch is not None:
            results = [r for r in results if r.branch == branch]
        if promoted is not None:
            results = [r for r in results if r.promoted == promoted]
        if min_winrate is not None:
            results = [r for r in results if r.winrate >= min_winrate]
        return results
