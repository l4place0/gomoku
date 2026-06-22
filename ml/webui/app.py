#!/usr/bin/env python3
"""webui/app.py — FastAPI backend for training console.

Thin wrapper around mlevo CLI. All operations delegate to CLI subcommands.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

ML_DIR = Path(__file__).resolve().parent.parent
CLI = [sys.executable, str(ML_DIR / "mlevo_cli.py")]

app = FastAPI(title="Gomoku ML Training Console", version="0.1.0")


def _run_cli(*args) -> dict:
    """Run mlevo CLI and return parsed JSON."""
    cmd = CLI + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    # Try to parse stdout as JSON (last line if mixed output)
    if proc.stdout.strip():
        lines = proc.stdout.strip().split("\n")
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
        # If no JSON found, try the whole stdout
        try:
            return json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            pass
    # Try stderr
    if proc.stderr.strip():
        try:
            return json.loads(proc.stderr.strip())
        except json.JSONDecodeError:
            pass
    # Return raw output as error
    raise HTTPException(status_code=500, detail=proc.stderr or proc.stdout or "CLI returned no output")


@app.get("/api/status")
def get_status():
    return _run_cli("status")


@app.get("/api/progress")
def get_progress():
    return _run_cli("progress")


@app.get("/api/graph")
def get_graph(with_edges: bool = False, topo: bool = False):
    args = ["graph"]
    if with_edges:
        args.append("--with-edges")
    if topo:
        args.append("--topo")
    return _run_cli(*args)


@app.get("/api/models")
def get_models(branch: Optional[str] = None, min_winrate: Optional[float] = None, promoted: Optional[bool] = None):
    args = ["models"]
    if branch:
        args.extend(["--branch", branch])
    if min_winrate is not None:
        args.extend(["--min-winrate", str(min_winrate)])
    if promoted is not None:
        args.extend(["--promoted", str(promoted)])
    return _run_cli(*args)


@app.get("/api/models/{model_hash}")
def get_model(model_hash: str):
    return _run_cli("model", "--hash", model_hash)


class RunRequest(BaseModel):
    round: int
    preset: Optional[str] = None
    plan: Optional[str] = None
    branch: Optional[str] = None
    change: Optional[str] = None


@app.post("/api/run")
def start_run(req: RunRequest):
    args = ["run", "--round", str(req.round)]
    if req.preset:
        args.extend(["--preset", req.preset])
    if req.plan:
        args.extend(["--plan", req.plan])
    if req.branch:
        args.extend(["--branch", req.branch])
    if req.change:
        args.extend(["--change", req.change])
    return _run_cli(*args)


class BranchRequest(BaseModel):
    from_hash: str
    name: Optional[str] = None


@app.post("/api/branch")
def create_branch(req: BranchRequest):
    args = ["branch", "--from", req.from_hash]
    if req.name:
        args.extend(["--name", req.name])
    return _run_cli(*args)


class MergeRequest(BaseModel):
    winner: str


@app.post("/api/merge")
def merge_branch(req: MergeRequest):
    return _run_cli("merge", "--winner", req.winner)


@app.get("/api/schema")
def get_schema():
    return _run_cli("schema")


def _read_log_file(path: Path) -> str:
    """Read a log file with automatic encoding detection.

    Tries UTF-8 first, then falls back to GBK/CP936 (common on Windows/WSL).
    Uses 'replace' so garbled bytes show as U+FFFD instead of being silently dropped.
    """
    raw = path.read_bytes()
    for enc in ("utf-8", "gbk", "cp936", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


@app.get("/api/logs")
def get_logs(round: Optional[int] = None, level: Optional[str] = None):
    """Read log files from logs/ directory."""
    log_dir = ML_DIR / "data" / "logs"
    if not log_dir.exists():
        return {"logs": []}

    entries = []
    for log_file in sorted(log_dir.glob("*"), reverse=True):
        if not log_file.is_file():
            continue
        # Include .log, .txt, and extensionless files (e.g. logs from KataGo)
        if log_file.suffix not in (".log", ".txt", "") and log_file.suffix != "":
            continue
        try:
            content = _read_log_file(log_file)
        except Exception:
            continue
        # Filter by round if specified
        if round is not None:
            if f"round_{round}" not in log_file.name and f"Round {round}" not in content:
                continue
        # Filter by level if specified
        if level:
            lines = [l for l in content.split("\n") if level.upper() in l.upper()]
            content = "\n".join(lines)
        entries.append({
            "file": log_file.name,
            "content": content[-8000:],  # Last 8000 chars
        })

    return {"logs": entries, "count": len(entries)}


@app.get("/api/history/{model_hash}")
def get_history(model_hash: str):
    return _run_cli("history", "--model", model_hash)


@app.get("/api/plans")
def get_plans():
    return _run_cli("plans")


@app.get("/api/plans/{plan_name}")
def get_plan_detail(plan_name: str):
    return _run_cli("plan", "--name", plan_name)


@app.get("/api/changes/{plan_name}/markdown/{filename}")
def get_change_markdown(plan_name: str, filename: str):
    """Retrieve active or archived proposal/design/conclusion markdown files."""
    if filename not in ("proposal.md", "design.md", "conclusion.md", "tasks.md"):
        raise HTTPException(status_code=400, detail="Invalid filename requested")
    
    # 1. Search in active changes: docs/ml/changes/{plan_name}/{filename}
    active_path = ML_DIR.parent / "docs" / "ml" / "changes" / plan_name / filename
    if active_path.exists() and active_path.is_file():
        try:
            return {"content": _read_log_file(active_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")
            
    # 2. Search in archived changes: docs/ml/changes/archive/*-{plan_name}/{filename}
    archive_dir = ML_DIR.parent / "docs" / "ml" / "changes" / "archive"
    if archive_dir.exists() and archive_dir.is_dir():
        for p in archive_dir.glob(f"*-{plan_name}"):
            if p.is_dir():
                target_path = p / filename
                if target_path.exists() and target_path.is_file():
                    try:
                        return {"content": _read_log_file(target_path)}
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")
        for p in archive_dir.glob(plan_name):
            if p.is_dir():
                target_path = p / filename
                if target_path.exists() and target_path.is_file():
                    try:
                        return {"content": _read_log_file(target_path)}
                    except Exception as e:
                        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    raise HTTPException(status_code=404, detail="Markdown file not found")


@app.get("/{catchall:path}")
def serve_spa(catchall: str):
    """Serve React SPA frontend static files or index.html for React Router."""
    if catchall.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    dist_dir = ML_DIR.parent / "webui" / "frontend" / "dist"
    
    # Try serving static asset directly
    file_path = dist_dir / catchall
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
        
    # Serve index.html as fallback for React Router path refreshes
    index_path = dist_dir / "index.html"
    if index_path.exists() and index_path.is_file():
        return FileResponse(index_path)
        
    raise HTTPException(status_code=404, detail="Static files not found. Run npm run build first.")

