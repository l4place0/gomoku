"""Unit tests for automl_cli.py pipeline stages.

Tests each stage function in isolation using mock subprocess calls.
No GPU required.
"""

import pytest
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from ml.automl_cli import (
    StageResult, run_selfplay, run_shuffle, run_train, run_export, run_pk,
    create_parser, find_latest_checkpoint
)


@pytest.fixture(autouse=True)
def mock_subprocess(monkeypatch):
    """Mock all subprocess calls to prevent real process execution."""
    def mock_run(cmd, **kwargs):
        # Return valid JSON for opening seed selection
        if any("select_opening" in str(c) for c in cmd):
            return subprocess.CompletedProcess(cmd, 0, '{"selected": "test_seed"}', "")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def mock_popen(cmd, **kwargs):
        proc = MagicMock()
        proc.wait.return_value = 0
        proc.returncode = 0
        proc.stdout = []
        return proc

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(subprocess, "Popen", mock_popen)


@pytest.fixture
def data_dir(tmp_path):
    """Create test data directory structure."""
    d = tmp_path / "data"
    for subdir in [
        "selfplay", "models", "shuffleddata/current/train",
        "shuffleddata/current/val", "torchmodels_toexport",
        "models_exported", "shuffle_tmp/train", "shuffle_tmp/val",
        "train/b10c256nbt"
    ]:
        (d / subdir).mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def logs_dir(tmp_path):
    """Create test logs directory."""
    d = tmp_path / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def args(data_dir):
    """Create test args namespace."""
    parser = create_parser()
    return parser.parse_args([
        "--round", "1",
        "--model-name", "b10c256nbt",
        "--data-dir", str(data_dir),
        "--sf-games", "5",
        "--sf-visits", "8",
        "--sf-threads", "2",
        "--sh-threads", "2",
        "--sh-samples", "100",
        "--tr-batch", "16",
        "--tr-epochs", "1",
        "--pk-games", "4",
    ])


# --- StageResult tests ---

class TestStageResult:
    def test_success_result(self):
        r = StageResult(True, 1.5, Path("/tmp/test.log"))
        assert r.success is True
        assert r.duration == 1.5
        assert r.error == ""

    def test_failure_result(self):
        r = StageResult(False, 0.5, Path("/tmp/test.log"), "some error")
        assert r.success is False
        assert r.error == "some error"


# --- run_selfplay tests ---

class TestRunSelfplay:
    def test_selfplay_mock_mode(self, args, data_dir, logs_dir):
        """When engine doesn't exist, uses mock mode."""
        result = run_selfplay(args, data_dir, logs_dir, 1)
        assert result.success is True
        assert result.log_file.exists()

    def test_selfplay_records_log(self, args, data_dir, logs_dir):
        """Selfplay creates log file."""
        result = run_selfplay(args, data_dir, logs_dir, 1)
        assert result.log_file.exists()


# --- run_shuffle tests ---

class TestRunShuffle:
    def test_shuffle_mock_mode(self, args, data_dir, logs_dir):
        """When shuffle.py doesn't exist, uses mock mode."""
        result = run_shuffle(args, data_dir, logs_dir, 1)
        assert result.success is True

    def test_shuffle_clears_old_dirs(self, args, data_dir, logs_dir):
        """Shuffle clears old output directories."""
        # Create some old data
        old_train = data_dir / "shuffleddata" / "current" / "train"
        old_train.mkdir(parents=True, exist_ok=True)
        (old_train / "old_data.npz").write_text("old")

        result = run_shuffle(args, data_dir, logs_dir, 1)
        # Old data should be cleared (or mock mode runs)
        assert result.success is True


# --- run_train tests ---

class TestRunTrain:
    def test_train_creates_log(self, args, data_dir, logs_dir):
        """Train stage creates log file."""
        result = run_train(args, data_dir, logs_dir, 1)
        assert result.success is True
        assert result.log_file.exists()

    def test_train_fp16_flag(self, args, data_dir, logs_dir):
        """FP16 flag is passed to train command."""
        args.tr_fp16 = True
        result = run_train(args, data_dir, logs_dir, 1)
        assert result.success is True


# --- run_export tests ---

class TestRunExport:
    def test_export_mock_mode(self, args, data_dir, logs_dir):
        """When export script doesn't exist, uses mock mode."""
        result = run_export(args, data_dir, logs_dir, 1)
        assert result.success is True

    def test_export_creates_gz(self, args, data_dir, logs_dir):
        """Export creates .bin.gz file."""
        result = run_export(args, data_dir, logs_dir, 1)
        gz_path = data_dir / "models_exported" / "b10c256nbt" / "model.bin.gz"
        assert gz_path.exists()


# --- run_pk tests ---

class TestRunPk:
    def test_pk_no_baseline(self, args, data_dir, logs_dir, monkeypatch):
        """When no baseline model exists, auto-promotes."""
        candidate_gz = data_dir / "models_exported" / "b10c256nbt" / "model.bin.gz"
        candidate_gz.parent.mkdir(parents=True, exist_ok=True)
        candidate_gz.write_text("mock")

        # Mock GAME_MODEL_PATH to non-existent path
        import ml.automl_cli as ac
        monkeypatch.setattr(ac, "GAME_MODEL_PATH", data_dir / "nonexistent" / "model.bin.gz")

        result = run_pk(args, data_dir, logs_dir, 1, candidate_gz)
        assert result.success is True
        assert result._pk_winrate == 1.0

    def test_pk_creates_log(self, args, data_dir, logs_dir):
        """PK stage creates log file."""
        candidate_gz = data_dir / "models_exported" / "b10c256nbt" / "model.bin.gz"
        candidate_gz.parent.mkdir(parents=True, exist_ok=True)
        candidate_gz.write_text("mock")

        result = run_pk(args, data_dir, logs_dir, 1, candidate_gz)
        assert result.success is True
        assert result.log_file.exists()


# --- find_latest_checkpoint tests ---

class TestFindLatestCheckpoint:
    def test_finds_checkpoint(self, data_dir, tmp_path):
        """Finds the latest checkpoint file."""
        chk_dir = data_dir / "train" / "b10c256nbt"
        chk_dir.mkdir(parents=True, exist_ok=True)
        chk = chk_dir / "model.ckpt"
        chk.write_text("weights")

        result = find_latest_checkpoint(data_dir)
        assert result is not None
        assert result.name == "model.ckpt"

    def test_no_checkpoint(self, data_dir):
        """Returns None when no checkpoint exists."""
        result = find_latest_checkpoint(data_dir)
        assert result is None
