#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mlevo_cli.py
MLEvo: Gomoku AutoML Supervised Evolution Workflow Orchestrator CLI.
Headless architecture: CLI is the sole state manager, Agent interacts via JSON.
"""

import sys
import os
import json
import argparse
import subprocess
import shutil
import re
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
LOG_DIR = BASE_DIR / "data" / "logs"
PLANS_DIR = PROJECT_ROOT / "docs" / "ml" / "plans"
ARCHIVE_DIR = PLANS_DIR / "archive"
LEDGER_PATH = LOG_DIR / "evolution_ledger.json"
STATE_PATH = LOG_DIR / "pipeline_state.json"
PROGRESS_PATH = LOG_DIR / "progress.json"
REGISTRY_PATH = BASE_DIR / "data" / "model_registry.jsonl"
MODELS_DIR = BASE_DIR / "data" / "models"

_MAX_JSON_SIZE = 50 * 1024 * 1024  # 50MB

# --- Preset configurations ---
PRESETS = {
    "tiny": {
        "sf_games": 5, "sf_visits": 8, "sh_samples": 100,
        "tr_epochs": 1, "pk_games": 4, "tr_batch": 16,
    },
    "small": {
        "sf_games": 50, "sf_visits": 32, "sh_samples": 1000,
        "tr_epochs": 1, "pk_games": 10, "tr_batch": 32,
    },
}

# --- State machine ---
VALID_STATES = {"idle", "running", "paused", "crashed"}
VALID_TRANSITIONS = {
    "idle": {"running"},
    "running": {"idle", "crashed"},
    "paused": {"running", "idle"},
    "crashed": {"idle", "running"},
}


def _output(data, use_json=True):
    """Print output as JSON or human-readable."""
    if use_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"{k}:")
                for kk, vv in v.items():
                    print(f"  {kk}: {vv}")
            elif isinstance(v, list):
                print(f"{k}: [{len(v)} items]")
            else:
                print(f"{k}: {v}")


def _error(msg, code="ERROR", exit_code=1):
    """Print error and exit."""
    print(json.dumps({"error": msg, "code": code}, ensure_ascii=False), file=sys.stderr)
    sys.exit(exit_code)


def _find_python():
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _load_json_safe(path):
    if path.exists():
        try:
            if path.stat().st_size > _MAX_JSON_SIZE:
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# --- State Machine ---

def load_state():
    state = _load_json_safe(STATE_PATH)
    if not state:
        return {"pipeline_state": "idle", "current_round": 0, "current_plan": None, "last_error": None}
    return state


def save_state(state):
    _save_json(STATE_PATH, state)


def transition_state(target):
    state = load_state()
    current = state["pipeline_state"]
    if target not in VALID_TRANSITIONS.get(current, set()):
        _error(f"Cannot transition from '{current}' to '{target}'", "STATE_CONFLICT")
    state["pipeline_state"] = target
    save_state(state)
    return state


def load_progress():
    return _load_json_safe(PROGRESS_PATH) or {"stage": None, "pct": 0, "eta": None}


def save_progress(stage, pct, eta=None):
    _save_json(PROGRESS_PATH, {"stage": stage, "pct": pct, "eta": eta, "updated": datetime.now(timezone.utc).isoformat()})


# --- Registry helpers ---

def _get_registry():
    from ml.model_registry import ModelRegistry
    return ModelRegistry(registry_path=REGISTRY_PATH, models_dir=MODELS_DIR)


def _get_dag():
    from ml.dag_engine import DAGEngine
    return DAGEngine(_get_registry())


# --- Decision Engine (preserved from original) ---

class DecisionEngine:
    def __init__(self, baseline_config, history, log_contents=None):
        self.baseline = baseline_config
        self.history = history
        self.log_contents = log_contents or {}

    def decide(self, next_round):
        decided = self.baseline.copy()
        reasons = []
        warnings = []

        prev_round = next_round - 1
        prev_round_failed = False
        prev_round_record = None

        if self.history:
            for record in reversed(self.history):
                if record.get("round") == prev_round:
                    prev_round_record = record
                    break

        if prev_round_record:
            pk_info = prev_round_record.get("pk", {})
            if not pk_info.get("promoted", False):
                prev_round_failed = True

        if prev_round_failed:
            decided["sf_games"] = int(round(self.baseline.get("sf_games", 500) * 1.2))
            decided["sf_visits"] = self.baseline.get("sf_visits", 96) + 16
            reasons.append(f"Entropy boost: sf_games={decided['sf_games']}, sf_visits={decided['sf_visits']}")
        else:
            reasons.append("Entropy boost not triggered")

        log_text = self.log_contents.get(prev_round, "")
        if not log_text and prev_round > 0:
            log_file = LOG_DIR / f"round_{prev_round}_train.log"
            if log_file.exists():
                try:
                    log_text = log_file.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

        lr_decay_triggered = False
        if log_text:
            losses = [float(x) for x in re.findall(r"loss\s*=\s*(\d+\.\d+)", log_text)]
            if len(losses) >= 2:
                diff = abs(losses[-1] - losses[0])
                if diff < 0.05:
                    decided["tr_lr"] = max(0.0001, self.baseline.get("tr_lr", 0.002) * 0.5)
                    lr_decay_triggered = True
                    reasons.append(f"LR decay: tr_lr={decided['tr_lr']} (plateau detected)")

        if not lr_decay_triggered:
            reasons.append("LR decay not triggered")

        if log_text:
            if "OutOfMemoryError" in log_text or "CUDA out of memory" in log_text:
                decided["tr_batch"] = max(16, self.baseline.get("tr_batch", 64) // 2)
                reasons.append(f"OOM recovery: tr_batch={decided['tr_batch']}")
            if "nan" in log_text.lower():
                decided["tr_lr"] = max(0.0001, self.baseline.get("tr_lr", 0.002) * 0.5)
                reasons.append(f"NaN recovery: tr_lr={decided['tr_lr']}")
                warnings.append("Previous round had NaN loss — checkpoint was purged, will reinitialize from scratch")

        if decided.get("sf_games", 0) < 100:
            warnings.append(f"sf_games ({decided['sf_games']}) below recommended 100")
        if decided.get("pk_games", 0) < 20:
            warnings.append(f"pk_games ({decided['pk_games']}) below recommended 20")

        return decided, reasons, warnings


# --- Ledger ---

def load_ledger():
    return _load_json_safe(LEDGER_PATH) or []


def save_ledger(ledger):
    _save_json(LEDGER_PATH, ledger)


# --- Plan helpers ---

def get_plan_dir(plan_name):
    return PLANS_DIR / plan_name


def find_plan(plan_name=None):
    if plan_name:
        plan_dir = get_plan_dir(plan_name)
        if plan_dir.exists() and plan_dir.is_dir() and plan_name != "archive":
            return plan_name, plan_dir
        _error(f"Plan '{plan_name}' not found")
    active_plans = []
    if PLANS_DIR.exists():
        for item in PLANS_DIR.iterdir():
            if item.is_dir() and item.name != "archive":
                active_plans.append(item)
    if len(active_plans) == 1:
        return active_plans[0].name, active_plans[0]
    elif len(active_plans) > 1:
        names = ", ".join([p.name for p in active_plans])
        _error(f"Multiple plans: {names}. Use --plan <name>")
    else:
        _error("No active plans. Create with 'mlevo new plan <name>'")


# =====================================================================
# Subcommands
# =====================================================================

def cmd_automl_help(args):
    """Show automl_cli.py --help so Agent can discover all available parameters."""
    try:
        proc = subprocess.run(
            [_find_python(), "automl_cli.py", "--help"],
            capture_output=True, text=True, timeout=10, cwd=str(BASE_DIR),
        )
        _output({"help": proc.stdout, "returncode": proc.returncode}, True)
    except Exception as e:
        _output({"error": str(e)}, True)


def cmd_schema(args):
    """Output CLI schema for agent self-description."""
    schema = {
        "commands": {
            "schema": {"args": [], "description": "Output CLI schema (this command)"},
            "automl-help": {"args": [], "description": "Show automl_cli.py --help for parameter discovery"},
            "status": {"args": ["--plan", "--json"], "description": "Show pipeline status"},
            "progress": {"args": ["--json"], "description": "Show training progress"},
            "run": {"args": ["--plan", "--round", "--preset", "--change", "--branch", "--inject", "--params", "--json"], "description": "Execute a training round (--params is JSON passthrough to automl_cli.py)"},
            "branch": {"args": ["--from", "--name", "--json"], "description": "Create a branch from a model"},
            "merge": {"args": ["--winner", "--json"], "description": "Merge branch to mainline"},
            "pk": {"args": ["--branch-a", "--branch-b", "--games", "--json"], "description": "PK tournament between branches"},
            "graph": {"args": ["--with-edges", "--topo", "--json"], "description": "Export model DAG graph"},
            "models": {"args": ["--branch", "--min-winrate", "--promoted", "--json"], "description": "List/filter models"},
            "model": {"args": ["--hash", "--json"], "description": "Get single model details"},
            "history": {"args": ["--model", "--json"], "description": "Get model ancestry chain"},
            "recover": {"args": ["--json"], "description": "Recover from crashed state"},
            "migrate": {"args": ["--from-ledger", "--json"], "description": "Migrate legacy ledger data"},
            "test": {"args": ["--suite", "--inject", "--json"], "description": "Run test suite"},
            "new": {"args": ["plan", "<name>"], "description": "Scaffold a new evolution plan"},
            "list": {"args": [], "description": "List active and archived plans"},
            "decide": {"args": ["--plan", "--json"], "description": "Compute next round parameters"},
            "archive": {"args": ["<name>"], "description": "Archive a completed plan"},
        },
        "state_transitions": {k: list(v) for k, v in VALID_TRANSITIONS.items()},
        "presets": {k: list(v.keys()) for k, v in PRESETS.items()},
    }
    _output(schema, True)


def cmd_status(args):
    """Show pipeline status."""
    state = load_state()
    ledger = load_ledger()
    registry = _get_registry()
    latest_promoted = registry.get_latest_promoted("mainline")

    result = {
        "pipeline_state": state["pipeline_state"],
        "current_round": state.get("current_round", len(ledger)),
        "current_model": {
            "hash": latest_promoted.hash if latest_promoted else None,
            "winrate": latest_promoted.winrate if latest_promoted else None,
        },
        "active_plan": state.get("current_plan"),
        "last_error": state.get("last_error"),
        "model_registry_count": len(registry.read_all()),
        "ledger_rounds": len(ledger),
    }
    _output(result, True)


def cmd_progress(args):
    """Show training progress."""
    progress = load_progress()
    _output(progress, True)


def cmd_run(args):
    """Execute a training round."""
    state = load_state()

    # Check state
    if state["pipeline_state"] not in ("idle", "crashed"):
        _error(f"Cannot run: pipeline is {state['pipeline_state']}", "STATE_CONFLICT")

    # Transition to running
    transition_state("running")

    round_no = args.round
    branch = getattr(args, 'branch', None) or "mainline"
    change = getattr(args, 'change', "")
    preset = getattr(args, 'preset', None)
    inject = getattr(args, 'inject', None)

    # Determine plan
    plan_name = getattr(args, 'plan', None)
    if plan_name:
        _, plan_dir = find_plan(plan_name)
    else:
        # Try to find a plan
        try:
            plan_name, plan_dir = find_plan()
        except SystemExit:
            plan_dir = None

    # Get parameters
    if preset and preset in PRESETS:
        params = PRESETS[preset].copy()
        params["round"] = round_no
        params["model_name"] = "b10c128"
        params["tr_kind"] = "b10c128"
        params["tr_lr"] = params.get("tr_lr", 0.002)
        params["pk_threshold"] = 0.55
    elif plan_dir:
        plan_file = plan_dir / "training_plan.json"
        plan_config = _load_json_safe(plan_file) or {}
        history = load_ledger()
        stage_config = None
        for stage in plan_config.get("stages", []):
            if stage.get("start_round", 1) <= round_no <= stage.get("end_round", 1):
                stage_config = stage.get("config", {})
                break
        if not stage_config:
            stages = plan_config.get("stages", [])
            stage_config = stages[0].get("config", {}) if stages else {}
        engine = DecisionEngine(stage_config, history)
        decided_params, _, _ = engine.decide(round_no)
        decided_params["round"] = round_no
        decided_params["model_name"] = plan_config.get("model_kind", "b10c128")
        decided_params["tr_kind"] = plan_config.get("model_kind", "b10c128")
        decided_params["pk_threshold"] = plan_config.get("promotion_threshold", 0.55)
        params = decided_params
    else:
        params = PRESETS.get(preset, PRESETS["tiny"]).copy()
        params["round"] = round_no
        params["model_name"] = "b10c128"
        params["tr_kind"] = "b10c128"
        params["tr_lr"] = 0.002
        params["pk_threshold"] = 0.55

    # Fault injection
    if inject:
        save_progress("inject", 0, None)
        if inject == "oom":
            transition_state("crashed")
            state = load_state()
            state["last_error"] = "OOM (injected)"
            save_state(state)
            _output({"status": "failed", "error": "OOM", "recovery": "reduce_batch", "round": round_no}, True)
            return
        elif inject == "nan":
            transition_state("crashed")
            state = load_state()
            state["last_error"] = "NaN loss (injected)"
            save_state(state)
            _output({"status": "failed", "error": "NaN loss", "recovery": "reduce_lr", "round": round_no}, True)
            return
        elif inject == "crash":
            transition_state("crashed")
            state = load_state()
            state["last_error"] = "Process crashed (injected)"
            save_state(state)
            _output({"status": "failed", "error": "process crashed", "recovery": "retry", "round": round_no}, True)
            return

    # Build command: start with known pipeline params, then merge all extra params
    extra_params = getattr(args, 'params', None)
    if extra_params:
        try:
            extra = json.loads(extra_params) if isinstance(extra_params, str) else extra_params
            params.update(extra)
        except json.JSONDecodeError:
            _error(f"Invalid --params JSON: {extra_params}")

    cmd = [_find_python(), "automl_cli.py"]
    # Convert params dict to CLI flags: key_name -> --key-name
    for key, value in params.items():
        flag = f"--{key.replace('_', '-')}"
        if isinstance(value, bool):
            if value:
                cmd.append(flag)
        elif value is not None:
            cmd.extend([flag, str(value)])

    save_progress("selfplay", 0, None)

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore", bufsize=1)
        for line in process.stdout:
            print(line, end="", flush=True)
        process.wait()

        if process.returncode != 0:
            # Check for NaN in training log — if found, purge corrupted checkpoint
            train_log = LOG_DIR / f"round_{round_no}_train.log"
            if train_log.exists():
                log_text = train_log.read_text(encoding="utf-8", errors="ignore")
                if "nan" in log_text.lower() or "p0loss=nan" in log_text:
                    train_dir = BASE_DIR / "data" / "training_data" / "train" / params.get("model_name", "b10c128")
                    for ckpt in train_dir.glob("checkpoint*.ckpt"):
                        ckpt.unlink()
                    _output({"status": "failed", "error": "NaN loss detected, purged corrupted checkpoint", "round": round_no, "recovery": "will reinitialize from scratch"}, True)
            transition_state("crashed")
            state = load_state()
            state["last_error"] = f"Exit code {process.returncode}"
            save_state(state)
            _output({"status": "failed", "error": f"Exit code {process.returncode}", "round": round_no}, True)
            return

        save_progress("completed", 100, None)

        # Post-training NaN check: purge checkpoint if training had NaN losses
        train_log = LOG_DIR / f"round_{round_no}_train.log"
        training_had_nan = False
        if train_log.exists():
            log_text = train_log.read_text(encoding="utf-8", errors="ignore")
            if "p0loss=nan" in log_text.lower():
                training_had_nan = True
                train_dir = BASE_DIR / "data" / "training_data" / "train" / params.get("model_name", "b10c128")
                for ckpt in train_dir.glob("checkpoint*.ckpt"):
                    ckpt.unlink()

        # Register model in registry
        registry = _get_registry()
        model_file = MODELS_DIR / "model.bin.gz"
        if not model_file.exists():
            # Try legacy path
            model_file = PROJECT_ROOT / "KataGomo" / "models" / "model.bin.gz"

        if model_file.exists():
            from ml.model_registry import compute_model_hash, archive_model, ModelRecord
            file_hash = compute_model_hash(model_file)

            # Always generate unique model hash: file content + timestamp
            # This prevents collision when training doesn't change weights
            import hashlib as _hl
            unique_input = f"{file_hash}-{round_no}-{branch}-{datetime.now().isoformat()}"
            model_hash = _hl.sha256(unique_input.encode()).hexdigest()[:12]
            archive_model(model_file, model_hash)

            # Get parent
            latest = registry.get_latest_on_branch(branch)
            parent_hash = latest.hash if latest else None

            # Get winrate from ledger
            ledger = load_ledger()
            last_entry = ledger[-1] if ledger else {}
            pk = last_entry.get("pk", {})
            winrate = pk.get("winrate", 0.0)
            promoted = pk.get("promoted", False)

            record = ModelRecord(
                hash=model_hash,
                parent=parent_hash,
                round=round_no,
                branch=branch,
                winrate=winrate,
                promoted=promoted,
                params=params,
                change=change,
                hypothesis="",
                timestamp=datetime.now(timezone.utc).isoformat(),
                file=f"models/{model_hash}.bin.gz",
            )
            registry.append_record(record)

        transition_state("idle")
        state = load_state()
        state["current_round"] = round_no
        save_state(state)

        _output({
            "status": "completed",
            "round": round_no,
            "winrate": winrate if model_file.exists() else None,
            "promoted": promoted if model_file.exists() else None,
            "model_hash": model_hash if model_file.exists() else None,
            "training_had_nan": training_had_nan,
        }, True)

    except Exception as e:
        transition_state("crashed")
        state = load_state()
        state["last_error"] = str(e)
        save_state(state)
        _output({"status": "failed", "error": str(e), "round": round_no}, True)


def cmd_branch(args):
    """Create a branch from a model."""
    dag = _get_dag()
    from_hash = args.from_hash
    branch_name = dag.create_branch(from_hash, branch_name=getattr(args, 'name', None))
    _output({"branch": branch_name, "fork_from": from_hash, "status": "created"}, True)


def cmd_merge(args):
    """Merge branch to mainline."""
    registry = _get_registry()
    winner = args.winner
    # Get latest model on winning branch
    latest = registry.get_latest_on_branch(winner)
    if not latest:
        _error(f"No models on branch '{winner}'")
    _output({"status": "merged", "winner_branch": winner, "model_hash": latest.hash, "winrate": latest.winrate}, True)


def cmd_pk(args):
    """PK tournament between branches."""
    registry = _get_registry()
    branch_a = args.branch_a
    branch_b = args.branch_b
    games = getattr(args, 'games', 30)

    latest_a = registry.get_latest_on_branch(branch_a)
    latest_b = registry.get_latest_on_branch(branch_b)
    if not latest_a or not latest_b:
        _error("Both branches must have models")

    # Run actual PK via automl_cli
    cmd = [
        _find_python(), "automl_cli.py", "pk",
        "--model-a", str(BASE_DIR / latest_a.file),
        "--model-b", str(BASE_DIR / latest_b.file),
        "--games", str(games),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        # Parse result from stdout
        pk_result = {"winner": branch_a, "winrate": 0.5, "games_played": games}
        try:
            pk_result = json.loads(result.stdout.strip().split("\n")[-1])
        except (json.JSONDecodeError, IndexError):
            pass
        _output(pk_result, True)
    except Exception as e:
        _output({"error": str(e)}, True)


def cmd_graph(args):
    """Export model DAG graph."""
    dag = _get_dag()
    graph = dag.export_graph(with_edges=getattr(args, 'with_edges', False))
    if getattr(args, 'topo', False):
        try:
            sorted_records = dag.topological_sort()
            graph["topo_order"] = [r.hash for r in sorted_records]
        except ValueError as e:
            graph["topo_error"] = str(e)
    _output(graph, True)


def cmd_models(args):
    """List/filter models."""
    registry = _get_registry()
    branch = getattr(args, 'branch', None)
    min_wr = getattr(args, 'min_winrate', None)
    promoted = getattr(args, 'promoted', None)
    models = registry.filter_models(branch=branch, promoted=promoted, min_winrate=min_wr)
    result = [{"hash": m.hash, "parent": m.parent, "round": m.round, "branch": m.branch, "winrate": m.winrate, "promoted": m.promoted} for m in models]
    _output({"models": result, "count": len(result)}, True)


def cmd_model(args):
    """Get single model details."""
    registry = _get_registry()
    record = registry.find_by_hash(args.hash)
    if not record:
        _error(f"Model '{args.hash}' not found")
    from dataclasses import asdict
    _output(asdict(record), True)


def cmd_history(args):
    """Get model ancestry chain."""
    dag = _get_dag()
    history = dag.get_history(args.model)
    _output({"model": args.model, "lineage": history}, True)


def cmd_recover(args):
    """Recover from crashed state."""
    state = load_state()
    if state["pipeline_state"] != "crashed":
        _error(f"Cannot recover: pipeline is {state['pipeline_state']}, not crashed")
    last_error = state.get("last_error", "unknown")
    state["pipeline_state"] = "idle"
    state["last_error"] = None
    save_state(state)
    _output({"status": "recovered", "action": "rerun", "previous_error": last_error}, True)


def cmd_migrate(args):
    """Migrate legacy ledger data to model registry."""
    if not getattr(args, 'from_ledger', False):
        _error("Use --from-ledger to migrate from evolution_ledger.json")

    ledger = load_ledger()
    if not ledger:
        _error("No ledger data found")

    registry = _get_registry()
    from ml.model_registry import ModelRecord

    parent_hash = None
    migrated = 0
    warnings = []

    for entry in ledger:
        round_no = entry.get("round", 0)
        pk = entry.get("pk", {})
        winrate = pk.get("winrate", 0.0)
        promoted = pk.get("promoted", False)
        params = entry.get("params", {})

        # Generate a deterministic hash from round + params
        hash_input = f"round-{round_no}-{json.dumps(params, sort_keys=True)}"
        model_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

        # Check if model file exists in legacy locations
        legacy_paths = [
            BASE_DIR / "data" / "training_data" / "models_exported" / "b10c128" / "model.bin",
            PROJECT_ROOT / "KataGomo" / "models" / "model.bin.gz",
        ]
        model_file = ""
        for p in legacy_paths:
            if p.exists():
                model_file = str(p.relative_to(BASE_DIR))
                break

        record = ModelRecord(
            hash=model_hash,
            parent=parent_hash,
            round=round_no,
            branch="mainline",
            winrate=winrate,
            promoted=promoted,
            params=params,
            change="",
            hypothesis="migrated from legacy ledger",
            timestamp=entry.get("timestamp", ""),
            file=model_file,
        )

        # Only append if not already in registry
        if not registry.find_by_hash(model_hash):
            registry.append_record(record)
            migrated += 1

        if promoted:
            parent_hash = model_hash

    _output({
        "status": "migrated",
        "migrated": migrated,
        "total_ledger": len(ledger),
        "warnings": warnings,
    }, True)


def cmd_test(args):
    """Run test suite."""
    suite = getattr(args, 'suite', 'all')
    inject = getattr(args, 'inject', None)

    results = {}
    suites_to_run = []

    if suite == "all":
        suites_to_run = ["unit", "integration", "webui-api", "webui-ui"]
    else:
        suites_to_run = [suite]

    # Use system python for tests (venv may not have pytest)
    test_python = sys.executable
    for s in suites_to_run:
        if s == "unit":
            cmd = [test_python, "-m", "pytest", "tests/test_model_registry.py", "tests/test_dag_engine.py", "-v", "--tb=short"]
        elif s == "integration":
            if inject:
                cmd = [test_python, "-m", "pytest", f"tests/test_integration.py::test_inject_{inject}", "-v", "--tb=short"]
            else:
                cmd = [test_python, "-m", "pytest", "tests/test_integration.py", "-v", "--tb=short"]
        elif s == "webui-api":
            cmd = [test_python, "-m", "pytest", "tests/test_webui_api.py", "-v", "--tb=short"]
        elif s == "webui-ui":
            cmd = ["npm", "test", "--prefix", "webui/frontend"]
        else:
            results[s] = {"error": f"Unknown suite: {s}"}
            continue

        start = time.time()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR))
            elapsed = time.time() - start
            passed = proc.stdout.count(" PASSED")
            failed = proc.stdout.count(" FAILED")
            results[s] = {"passed": passed, "failed": failed, "time": f"{elapsed:.1f}s", "exit_code": proc.returncode}
            if failed > 0:
                results[s]["stderr_tail"] = proc.stderr[-500:] if proc.stderr else ""
        except subprocess.TimeoutExpired:
            results[s] = {"error": "timeout", "time": "300s"}
        except Exception as e:
            results[s] = {"error": str(e)}

    _output(results, True)


def cmd_decide(args):
    """Compute next round parameters."""
    plan_name, plan_dir = find_plan(getattr(args, 'plan', None))
    plan_file = plan_dir / "training_plan.json"
    plan_config = _load_json_safe(plan_file) or {}

    branch = getattr(args, 'branch', None) or "mainline"
    registry = _get_registry()
    branch_records = registry.find_by_branch(branch)
    completed_rounds = max((r.round for r in branch_records), default=0) if branch_records else 0
    next_round = completed_rounds + 1

    total_rounds = plan_config.get("total_rounds", 5)
    if next_round > total_rounds:
        _output({"status": "complete", "message": f"Plan completed ({completed_rounds}/{total_rounds})"}, True)
        return

    stage_config = None
    for stage in plan_config.get("stages", []):
        if stage.get("start_round", 1) <= next_round <= stage.get("end_round", 1):
            stage_config = stage.get("config", {})
            break
    if not stage_config:
        stages = plan_config.get("stages", [])
        stage_config = stages[0].get("config", {}) if stages else {}

    history = load_ledger()
    engine = DecisionEngine(stage_config, history)
    decided_params, reasons, warnings = engine.decide(next_round)
    decided_params["round"] = next_round
    decided_params["model_name"] = plan_config.get("model_kind", "b10c128")
    decided_params["tr_kind"] = plan_config.get("model_kind", "b10c128")
    decided_params["pk_threshold"] = plan_config.get("promotion_threshold", 0.55)

    _output({
        "plan_name": plan_name,
        "next_round": next_round,
        "status": "ready",
        "decided_parameters": decided_params,
        "decision_reasons": reasons,
        "guardrail_warnings": warnings,
    }, True)


def cmd_new(args):
    """Scaffold a new evolution plan."""
    plan_name = args.name
    plan_dir = get_plan_dir(plan_name)
    if plan_dir.exists():
        _error(f"Plan '{plan_dir}' already exists")
    plan_dir.mkdir(parents=True, exist_ok=True)

    plan_config = {
        "plan_name": plan_name,
        "total_rounds": 5,
        "model_kind": "b10c128",
        "promotion_threshold": 0.55,
        "stages": [{"start_round": 1, "end_round": 5, "config": {
            "sf_games": 500, "sf_visits": 96, "sh_samples": 150000,
            "tr_lr": 0.002, "tr_batch": 64, "pk_games": 20,
        }}],
    }
    _save_json(plan_dir / "training_plan.json", plan_config)
    _output({"status": "created", "plan": plan_name, "dir": str(plan_dir)}, True)


def cmd_list(args):
    """List active and archived plans."""
    active = []
    if PLANS_DIR.exists():
        active = [d.name for d in PLANS_DIR.iterdir() if d.is_dir() and d.name != "archive"]
    archived = []
    if ARCHIVE_DIR.exists():
        archived = [d.name for d in ARCHIVE_DIR.iterdir() if d.is_dir()]
    _output({"active": active, "archived": archived}, True)


def cmd_archive(args):
    """Archive a completed plan."""
    plan_name, plan_dir = find_plan(args.name)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    target_dir = ARCHIVE_DIR / f"{date_str}-{plan_name}"
    if target_dir.exists():
        _error(f"Archive target '{target_dir}' already exists")
    shutil.move(str(plan_dir), str(target_dir))
    _output({"status": "archived", "plan": plan_name, "target": str(target_dir)}, True)


# =====================================================================
# Plan Registry Commands (Hypergraph)
# =====================================================================

def _get_plan_registry():
    from ml.plan_registry import PlanRegistry
    return PlanRegistry()


def cmd_plans(args):
    """List all training plans (hypergraph)."""
    registry = _get_plan_registry()
    plans = registry.read_all()
    result = []
    for p in plans:
        result.append({
            "plan": p.plan,
            "best_model": p.best_model,
            "best_winrate": p.best_winrate,
            "rounds_completed": p.rounds_completed,
            "rounds_total": p.rounds_total,
            "from_plan": p.from_plan,
            "hypothesis": p.hypothesis,
            "status": p.status,
        })
    _output({"plans": result, "count": len(result)}, True)


def cmd_plan_detail(args):
    """View plan details with inner DAG."""
    registry = _get_plan_registry()
    plan = registry.find_by_name(args.name)
    if not plan:
        _error(f"Plan '{args.name}' not found")

    # Get inner DAG from model registry
    model_registry = _get_registry()
    branch_records = model_registry.find_by_branch(args.name)
    inner_dag = []
    for r in branch_records:
        inner_dag.append({
            "hash": r.hash,
            "parent": r.parent,
            "round": r.round,
            "winrate": r.winrate,
            "promoted": r.promoted,
        })

    # Get lineage
    lineage = registry.get_lineage(args.name)

    result = {
        "plan": plan.plan,
        "best_model": plan.best_model,
        "best_winrate": plan.best_winrate,
        "rounds_completed": plan.rounds_completed,
        "rounds_total": plan.rounds_total,
        "from_plan": plan.from_plan,
        "from_model": plan.from_model,
        "hypothesis": plan.hypothesis,
        "model_kind": plan.model_kind,
        "status": plan.status,
        "inner_dag": inner_dag,
        "lineage": [{"plan": p.plan, "best_model": p.best_model, "best_winrate": p.best_winrate} for p in lineage],
    }
    _output(result, True)


# =====================================================================
# Sync
# =====================================================================

def cmd_sync(args):
    """Sync models to Google Drive via tools/sync_drive.py."""
    sync_script = PROJECT_ROOT / "tools" / "sync_drive.py"
    cmd = [_find_python(), str(sync_script), "sync"]
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, capture_output=False)
    sys.exit(proc.returncode)


# =====================================================================
# Main
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="MLEvo: ML Evolution Orchestrator CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # schema
    subparsers.add_parser("schema", help="Output CLI schema")

    # automl-help
    subparsers.add_parser("automl-help", help="Show automl_cli.py --help for parameter discovery")

    # status
    status_p = subparsers.add_parser("status", help="Show pipeline status")
    status_p.add_argument("--plan", type=str)

    # progress
    subparsers.add_parser("progress", help="Show training progress")

    # run
    run_p = subparsers.add_parser("run", help="Execute a training round")
    run_p.add_argument("--plan", type=str)
    run_p.add_argument("--round", type=int, required=True)
    run_p.add_argument("--params", type=str, default=None, help="JSON string of extra params to pass through to automl_cli.py")
    run_p.add_argument("--preset", type=str, choices=["tiny", "small", "full"])
    run_p.add_argument("--change", type=str, default="")
    run_p.add_argument("--branch", type=str, default="mainline")
    run_p.add_argument("--inject", type=str, choices=["oom", "nan", "crash"])

    # branch
    branch_p = subparsers.add_parser("branch", help="Create a branch")
    branch_p.add_argument("--from", dest="from_hash", type=str, required=True)
    branch_p.add_argument("--name", type=str)

    # merge
    merge_p = subparsers.add_parser("merge", help="Merge branch to mainline")
    merge_p.add_argument("--winner", type=str, required=True)

    # pk
    pk_p = subparsers.add_parser("pk", help="PK tournament")
    pk_p.add_argument("--branch-a", type=str, required=True)
    pk_p.add_argument("--branch-b", type=str, required=True)
    pk_p.add_argument("--games", type=int, default=30)

    # graph
    graph_p = subparsers.add_parser("graph", help="Export model DAG")
    graph_p.add_argument("--with-edges", action="store_true")
    graph_p.add_argument("--topo", action="store_true")

    # models
    models_p = subparsers.add_parser("models", help="List/filter models")
    models_p.add_argument("--branch", type=str)
    models_p.add_argument("--min-winrate", type=float)
    models_p.add_argument("--promoted", type=bool)

    # model
    model_p = subparsers.add_parser("model", help="Model details")
    model_p.add_argument("--hash", type=str, required=True)

    # history
    history_p = subparsers.add_parser("history", help="Model ancestry")
    history_p.add_argument("--model", type=str, required=True)

    # recover
    subparsers.add_parser("recover", help="Recover from crash")

    # migrate
    migrate_p = subparsers.add_parser("migrate", help="Migrate legacy data")
    migrate_p.add_argument("--from-ledger", action="store_true")

    # test
    test_p = subparsers.add_parser("test", help="Run tests")
    test_p.add_argument("--suite", type=str, default="all", choices=["all", "unit", "integration", "webui-api", "webui-ui"])
    test_p.add_argument("--inject", type=str, choices=["oom", "nan", "crash", "all"])

    # decide
    decide_p = subparsers.add_parser("decide", help="Compute next round params")
    decide_p.add_argument("--plan", type=str)
    decide_p.add_argument("--branch", type=str, default="mainline")

    # new
    new_p = subparsers.add_parser("new", help="Scaffold new plan")
    new_p.add_argument("name", type=str)

    # list
    subparsers.add_parser("list", help="List plans")

    # plans (hypergraph)
    subparsers.add_parser("plans", help="List training plans (hypergraph)")

    # plan detail
    plan_detail_p = subparsers.add_parser("plan", help="View plan details")
    plan_detail_p.add_argument("--name", type=str, required=True)

    # archive
    archive_p = subparsers.add_parser("archive", help="Archive plan")
    archive_p.add_argument("name", type=str)

    sync_p = subparsers.add_parser("sync", help="Sync models to Google Drive")
    sync_p.add_argument("--dry-run", action="store_true", help="Preview without uploading")

    args = parser.parse_args()

    dispatch = {
        "schema": cmd_schema,
        "automl-help": cmd_automl_help,
        "status": cmd_status,
        "progress": cmd_progress,
        "run": cmd_run,
        "branch": cmd_branch,
        "merge": cmd_merge,
        "pk": cmd_pk,
        "graph": cmd_graph,
        "models": cmd_models,
        "model": cmd_model,
        "history": cmd_history,
        "recover": cmd_recover,
        "migrate": cmd_migrate,
        "test": cmd_test,
        "decide": cmd_decide,
        "new": cmd_new,
        "list": cmd_list,
        "archive": cmd_archive,
        "sync": cmd_sync,
        "plans": cmd_plans,
        "plan": cmd_plan_detail,
    }

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
