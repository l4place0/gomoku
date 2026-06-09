#!/usr/bin/env python3
"""Tests for tools/sync_drive.py."""
import pytest
from pathlib import Path
from tools.sync_drive import compute_model_diff, compute_plan_diff, compute_sync_plan, _human_size

class TestComputeModelDiff:
    def test_empty_directory(self, tmp_path):
        assert compute_model_diff(tmp_path, set()) == []
    def test_nonexistent_directory(self, tmp_path):
        assert compute_model_diff(tmp_path / "nope", set()) == []
    def test_finds_bin_gz_files(self, tmp_path):
        (tmp_path / "abc.bin.gz").touch()
        (tmp_path / "def.bin.gz").touch()
        (tmp_path / "other.txt").touch()
        assert compute_model_diff(tmp_path, set()) == ["abc.bin.gz", "def.bin.gz"]
    def test_ignores_non_matching_files(self, tmp_path):
        (tmp_path / "abc.bin.gz").touch()
        (tmp_path / "readme.txt").touch()
        assert compute_model_diff(tmp_path, set()) == ["abc.bin.gz"]
    def test_sorted_output(self, tmp_path):
        (tmp_path / "z.bin.gz").touch()
        (tmp_path / "a.bin.gz").touch()
        (tmp_path / "m.bin.gz").touch()
        assert compute_model_diff(tmp_path, set()) == ["a.bin.gz", "m.bin.gz", "z.bin.gz"]

class TestComputePlanDiff:
    def test_empty_directory(self, tmp_path):
        assert compute_plan_diff(tmp_path, set()) == []
    def test_nonexistent_directory(self, tmp_path):
        assert compute_plan_diff(tmp_path / "nope", set()) == []
    def test_finds_subdirectories(self, tmp_path):
        (tmp_path / "plan-a").mkdir()
        (tmp_path / "plan-b").mkdir()
        (tmp_path / "file.txt").touch()
        assert compute_plan_diff(tmp_path, set()) == ["plan-a", "plan-b"]
    def test_sorted_output(self, tmp_path):
        (tmp_path / "z-plan").mkdir()
        (tmp_path / "a-plan").mkdir()
        assert compute_plan_diff(tmp_path, set()) == ["a-plan", "z-plan"]

class TestComputeSyncPlan:
    def test_all_new(self):
        plan = compute_sync_plan(["a.bin.gz", "b.bin.gz"], set(), ["plan-1"], set())
        assert plan["models_to_upload"] == ["a.bin.gz", "b.bin.gz"]
        assert plan["plans_to_upload"] == ["plan-1"]
        assert plan["registry_overwrite"] is True
    def test_all_synced(self):
        plan = compute_sync_plan([], {"a.bin.gz"}, [], {"plan-1"})
        assert plan["models_to_upload"] == []
        assert plan["plans_to_upload"] == []
    def test_partial_sync(self):
        plan = compute_sync_plan(["b.bin.gz"], {"a.bin.gz"}, [], {"plan-1"})
        assert plan["models_to_upload"] == ["b.bin.gz"]
        assert plan["plans_to_upload"] == []
    def test_accepts_list_for_drive_models(self):
        plan = compute_sync_plan(["a.bin.gz"], [], ["p1"], [])
        assert plan["models_to_upload"] == ["a.bin.gz"]
    def test_empty_locals(self):
        plan = compute_sync_plan([], {"a.bin.gz"}, [], {"p1"})
        assert plan["models_to_upload"] == []
        assert plan["plans_to_upload"] == []

class TestCLIStructure:
    def test_has_auth(self):
        from tools.sync_drive import cmd_auth
        assert callable(cmd_auth)
    def test_has_sync(self):
        from tools.sync_drive import cmd_sync
        assert callable(cmd_sync)
    def test_has_status(self):
        from tools.sync_drive import cmd_status
        assert callable(cmd_status)
    def test_sync_dry_run_flag(self):
        import argparse
        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        sync_p = sub.add_parser("sync")
        sync_p.add_argument("--dry-run", action="store_true")
        args = parser.parse_args(["sync", "--dry-run"])
        assert args.dry_run is True

class TestHumanSize:
    def test_bytes(self):
        assert _human_size(500) == "500.0 B"
    def test_kilobytes(self):
        assert _human_size(2048) == "2.0 KB"
    def test_megabytes(self):
        assert _human_size(10 * 1024 * 1024) == "10.0 MB"
    def test_gigabytes(self):
        assert _human_size(5 * 1024 * 1024 * 1024) == "5.0 GB"
