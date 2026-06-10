#!/usr/bin/env python3
"""PK benchmark: sweep pk_visits, measure RAM/VRAM/time per game."""

import sys
import os
import json
import time
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collectors import ResourceSampler, get_ram_gb

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KATA_ROOT = PROJECT_ROOT / "KataGomo"
RUNNER = PROJECT_ROOT / "tools" / "headless_runner.py"
DATA_DIR = PROJECT_ROOT / "ml" / "data" / "training_data"
GAME_MODEL = KATA_ROOT / "models" / "model.bin.gz"
CANDIDATE_MODEL = DATA_DIR / "models_exported" / "b10c256nbt" / "model.bin.gz"


def gpu_env(gpu_id=0):
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    extra = []
    wsl = Path("/usr/lib/wsl/lib")
    if wsl.exists():
        extra.append(str(wsl))
    cudnn = PROJECT_ROOT / ".venv" / "lib" / f"python3.{sys.version_info.minor}" / "site-packages" / "nvidia" / "cudnn" / "lib"
    if cudnn.exists():
        extra.append(str(cudnn))
    if extra:
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = ":".join(extra) + (":" + existing if existing else "")
    return env


def find_python():
    venv = PROJECT_ROOT / ".venv" / "bin" / "python3"
    return str(venv) if venv.exists() else sys.executable


def run_pk_test(pk_visits, pk_games=10, timeout_sec=300):
    """Run PK with given visits and return resource metrics."""
    # Use same model for both sides (benchmark only)
    model = GAME_MODEL if GAME_MODEL.exists() else CANDIDATE_MODEL
    if not model.exists():
        return {"error": "No model found for PK test"}

    output = Path(f"/tmp/bench_pk_v{pk_visits}.json")
    if output.exists():
        output.unlink()

    sampler = ResourceSampler(interval=2.0)
    ram_before = get_ram_gb()

    cmd = [
        find_python(), str(RUNNER),
        "--black-model", str(model),
        "--white-model", str(model),
        "--games", str(pk_games),
        "--visits-black", str(pk_visits),
        "--visits-white", str(pk_visits),
        "--output", str(output),
    ]

    sampler.start()
    start = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, env=gpu_env())
        ok = proc.returncode == 0
    except subprocess.TimeoutExpired:
        ok = False
    wall_time = round(time.time() - start, 2)
    sampler.stop()

    ram_after = get_ram_gb()

    summary = sampler.summary()
    summary.update({
        "pk_visits": pk_visits,
        "pk_games": pk_games,
        "wall_time_sec": wall_time,
        "ram_before_gb": ram_before,
        "ram_after_gb": ram_after,
        "ram_delta_gb": round(ram_after - ram_before, 2),
        "games_per_min": round(pk_games / (wall_time / 60), 2) if wall_time > 0 else 0,
        "success": ok,
    })

    output.unlink(missing_ok=True)
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=str, default=str(Path(__file__).parent / "results" / "pk_bench.json"))
    parser.add_argument("--visits", type=str, default="64,128,256")
    args = parser.parse_args()

    visits_list = [int(x) for x in args.visits.split(",")]

    results = []
    for i, visits in enumerate(visits_list, 1):
        print(f"[{i}/{len(visits_list)}] Testing pk_visits={visits}, games={args.games}...", flush=True)
        r = run_pk_test(visits, args.games, args.timeout)
        results.append(r)
        status = "OK" if r.get("success") else "FAIL"
        print(f"  → {status} | RAM: {r.get('ram_before_gb',0):.1f}→{r.get('ram_after_gb',0):.1f} GB | "
              f"VRAM peak: {r.get('gpu_mem_peak_mb',0)} MiB | "
              f"Time: {r.get('wall_time_sec',0):.0f}s | "
              f"Games/min: {r.get('games_per_min',0):.1f}", flush=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
