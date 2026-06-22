#!/usr/bin/env python3
"""Selfplay benchmark: sweep sf_threads × sf_visits, measure RAM/VRAM/throughput."""

import sys
import os
import json
import time
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collectors import ResourceSampler, get_ram_gb, get_gpu_stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KATA_ROOT = PROJECT_ROOT / "KataGomo"
ENGINE = KATA_ROOT / "scripts" / "engine" / "katago"
DATA_DIR = PROJECT_ROOT / "ml" / "data" / "training_data"
CFG_SRC = DATA_DIR / "native_selfplay_15.cfg"


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


def run_selfplay_test(sf_threads, sf_visits, sf_games=20, timeout_sec=300):
    """Run a single selfplay config and return resource metrics."""
    test_dir = Path(f"/tmp/bench_sf_t{sf_threads}_v{sf_visits}")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    (test_dir / "models").mkdir(parents=True)
    (test_dir / "selfplay").mkdir(parents=True)

    # Copy model and config
    model_src = DATA_DIR / "models" / "model.bin.gz"
    if not model_src.exists():
        return {"error": "No model.bin.gz found"}
    shutil.copy2(model_src, test_dir / "models" / "model.bin.gz")
    cfg = test_dir / "selfplay.cfg"
    shutil.copy2(CFG_SRC, cfg)

    # Patch config
    text = cfg.read_text()
    for key, val in [("numGameThreads", sf_threads), ("numSearchThreads", 1)]:
        import re
        text = re.sub(rf"({key}\s*=)\s*\d+", rf"\1 {val}", text)
    cfg.write_text(text)

    sampler = ResourceSampler(interval=2.0)
    ram_before = get_ram_gb()

    cmd = [
        str(ENGINE), "selfplay",
        "-models-dir", str(test_dir / "models"),
        "-config", str(cfg),
        "-output-dir", str(test_dir / "selfplay"),
        "-max-games-total", str(sf_games),
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

    # Count output files
    npz_count = len(list((test_dir / "selfplay").rglob("*.npz")))

    summary = sampler.summary()
    summary.update({
        "sf_threads": sf_threads,
        "sf_visits": sf_visits,
        "sf_games": sf_games,
        "wall_time_sec": wall_time,
        "ram_before_gb": ram_before,
        "ram_after_gb": ram_after,
        "ram_delta_gb": round(ram_after - ram_before, 2),
        "games_completed": npz_count,
        "games_per_min": round(npz_count / (wall_time / 60), 2) if wall_time > 0 else 0,
        "success": ok,
    })

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--output", type=str, default=str(Path(__file__).parent / "results" / "selfplay_bench.json"))
    parser.add_argument("--threads", type=str, default="2,4,8,12,16")
    parser.add_argument("--visits", type=str, default="64,96,128")
    args = parser.parse_args()

    threads_list = [int(x) for x in args.threads.split(",")]
    visits_list = [int(x) for x in args.visits.split(",")]

    results = []
    total = len(threads_list) * len(visits_list)
    i = 0
    for threads in threads_list:
        for visits in visits_list:
            i += 1
            print(f"[{i}/{total}] Testing sf_threads={threads}, sf_visits={visits}, games={args.games}...", flush=True)
            r = run_selfplay_test(threads, visits, args.games, args.timeout)
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
