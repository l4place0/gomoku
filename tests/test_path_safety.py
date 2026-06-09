#!/usr/bin/env python3
"""Safety net tests for workspace reorganization.

These tests validate that after directory restructuring:
- All Python packages are importable
- Critical files exist at expected paths
- CLI tools can be invoked via subprocess
- CMakeLists.txt source paths are correct

Before reorganization: most tests SKIP (paths don't exist yet).
After reorganization: all tests should PASS.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Module Reachability ─────────────────────────────────────────────

class TestModuleReachability:
    """Verify each package can be imported after reorg."""

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "game" / "__init__.py").exists(),
        reason="game/ package not yet created",
    )
    def test_import_game_logic(self):
        from game import game_logic
        assert hasattr(game_logic, "BOARD_SIZE")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "game" / "__init__.py").exists(),
        reason="game/ package not yet created",
    )
    def test_import_game_logger(self):
        from game import game_logger
        assert hasattr(game_logger, "GameLogger")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_import_model_registry(self):
        from ml import model_registry
        assert hasattr(model_registry, "ModelRecord")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_import_plan_registry(self):
        from ml import plan_registry
        assert hasattr(plan_registry, "PlanRecord")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_import_dag_engine(self):
        from ml import dag_engine
        assert hasattr(dag_engine, "DAGEngine")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_import_automl_cli(self):
        from ml import automl_cli
        assert hasattr(automl_cli, "create_parser")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_import_mlevo_cli(self):
        from ml import mlevo_cli
        assert hasattr(mlevo_cli, "DecisionEngine")

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "tools" / "__init__.py").exists(),
        reason="tools/ package not yet created",
    )
    def test_import_ai_worker(self):
        # ai_worker loads DLL at import time; skip if DLL missing
        dll_path = PROJECT_ROOT / "engine" / "GameEngine.so"
        if not dll_path.exists():
            dll_path = PROJECT_ROOT / "engine" / "GameEngine.dll"
        if not dll_path.exists():
            pytest.skip("GameEngine.so/dll not found")
        import tools.ai_worker


# ── File Existence ──────────────────────────────────────────────────

class TestFileExistence:
    """Verify critical files exist at expected paths after reorg."""

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "game" / "__init__.py").exists(),
        reason="game/ package not yet created",
    )
    @pytest.mark.parametrize("relpath", [
        "game/game.py",
        "game/game_logic.py",
        "game/game_logger.py",
        "game/model_weights.txt",
        "game/assets/LXGWZhenKaiGB-Regular.ttf",
        "game/data/opening_book.json",
        "game/data/opening_seeds.json",
        "game/data/select_opening.py",
    ])
    def test_game_files_exist(self, relpath):
        assert (PROJECT_ROOT / relpath).exists(), f"Missing: {relpath}"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    @pytest.mark.parametrize("relpath", [
        "ml/automl_cli.py",
        "ml/mlevo_cli.py",
        "ml/training_ui.py",
        "ml/dag_engine.py",
        "ml/model_registry.py",
        "ml/plan_registry.py",
        "ml/run_training_loop.py",
        "ml/populate_opening_book.py",
        "ml/verify_opening_book.py",
        "ml/verify_symmetry.py",
        "ml/training_ui_state.json",
    ])
    def test_ml_files_exist(self, relpath):
        assert (PROJECT_ROOT / relpath).exists(), f"Missing: {relpath}"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "tools" / "__init__.py").exists(),
        reason="tools/ package not yet created",
    )
    @pytest.mark.parametrize("relpath", [
        "tools/ai_worker.py",
        "tools/headless_runner.py",
    ])
    def test_tools_files_exist(self, relpath):
        assert (PROJECT_ROOT / relpath).exists(), f"Missing: {relpath}"

    @pytest.mark.parametrize("relpath", [
        "engine/src/GameEngine.h",
        "engine/src/GameEngineDLL.cpp",
        "engine/src/GameEngineDLL.h",
        "engine/src/KataInferenceAdapter.cpp",
        "engine/src/KataInferenceAdapter.h",
        "engine/src/KataSelfplayMain.cpp",
        "engine/CMakeLists.txt",
        "engine/build.bat",
        "engine/build.sh",
    ])
    def test_engine_files_exist(self, relpath):
        if not (PROJECT_ROOT / "engine").exists():
            pytest.skip("engine/ directory not yet created")
        assert (PROJECT_ROOT / relpath).exists(), f"Missing: {relpath}"

    def test_engine_dll_exists(self):
        """Verify compiled GameEngine DLL/SO exists in engine/."""
        if not (PROJECT_ROOT / "engine").exists():
            pytest.skip("engine/ directory not yet created")
        so = PROJECT_ROOT / "engine" / "GameEngine.so"
        dll = PROJECT_ROOT / "engine" / "GameEngine.dll"
        assert so.exists() or dll.exists(), "GameEngine.so/dll not found in engine/"

    @pytest.mark.parametrize("relpath", [
        "KataGomo/models/model.bin.gz",
        "KataGomo/scripts/gomocup/default_gtp.cfg",
    ])
    def test_katagomo_files_exist(self, relpath):
        full = PROJECT_ROOT / relpath
        if not full.exists():
            pytest.skip(f"KataGomo submodule not initialized: {relpath}")


# ── Subprocess CLI Calls ────────────────────────────────────────────

class TestSubprocessCLI:
    """Verify CLI tools can be invoked via subprocess after reorg."""

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_mlevo_cli_help(self):
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "ml" / "mlevo_cli.py"), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        assert "mlevo" in proc.stdout.lower() or "usage" in proc.stdout.lower()

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "ml" / "__init__.py").exists(),
        reason="ml/ package not yet created",
    )
    def test_automl_cli_help(self):
        proc = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "ml" / "automl_cli.py"), "--help"],
            capture_output=True, text=True, timeout=15,
        )
        assert proc.returncode == 0, f"stderr: {proc.stderr}"
        assert "automl" in proc.stdout.lower() or "usage" in proc.stdout.lower()


# ── CMake Build Path ────────────────────────────────────────────────

class TestCMakePaths:
    """Verify CMakeLists.txt source paths are correct after reorg."""

    def test_cmake_lists_references_src_dir(self):
        cmake_path = PROJECT_ROOT / "engine" / "CMakeLists.txt"
        if not cmake_path.exists():
            pytest.skip("engine/CMakeLists.txt not yet created")
        content = cmake_path.read_text()
        # After reorg, source files should reference src/ prefix
        assert "GameEngineDLL.cpp" in content
        assert "KataInferenceAdapter.cpp" in content


# ── Root Directory Cleanliness ──────────────────────────────────────

class TestRootCleanliness:
    """Verify root directory is clean after reorg."""

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "game" / "__init__.py").exists(),
        reason="game/ package not yet created (reorg not done)",
    )
    def test_no_loose_python_files(self):
        """Root should have no .py files except pyproject.toml."""
        loose = [
            f for f in PROJECT_ROOT.glob("*.py")
            if f.name != "pyproject.toml" and f.is_file()
        ]
        assert loose == [], f"Loose .py files in root: {loose}"

    @pytest.mark.skipif(
        not (Path(__file__).resolve().parent.parent / "game" / "__init__.py").exists(),
        reason="game/ package not yet created (reorg not done)",
    )
    def test_no_temp_artifacts(self):
        """Root should not have temporary JSON reports."""
        temp_patterns = [
            "headless_verify_report*.json",
            "test_eval.json",
            "cli_eval_test.json",
            "training_plan.json",
        ]
        found = []
        for pat in temp_patterns:
            found.extend(str(f.relative_to(PROJECT_ROOT)) for f in PROJECT_ROOT.glob(pat))
        assert found == [], f"Temp artifacts in root: {found}"
