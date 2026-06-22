#!/usr/bin/env python3
"""
Machine Benchmark Suite
Runs selfplay, train, and PK benchmarks, then produces machine_profile.json.

Usage:
  python run_benchmark.py [--full] [--selfplay-only] [--train-only] [--pk-only]
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collectors import get_gpu_stats, get_ram_gb

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PROFILE_PATH = RESULTS_DIR / "machine_profile.json"


def get_hardware_info():
    """Collect hardware metadata."""
    gpu_mem_total, _ = get_gpu_stats()
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    ram_kb = int(line.split()[1])
                    ram_gb = round(ram_kb / 1024 / 1024, 1)
                    break
    except Exception:
        ram_gb = 0

    gpu_name = "unknown"
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            timeout=5, text=True
        ).strip()
        gpu_name = out
    except Exception:
        pass

    return {
        "gpu": gpu_name,
        "vram_mb": gpu_mem_total,
        "ram_gb": ram_gb,
        "platform": "WSL2" if os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop") else "Linux",
    }


def run_selfplay_bench(games=20, timeout=300):
    """Run selfplay benchmark suite."""
    from selfplay_bench import run_selfplay_test
    threads_list = [2, 4, 8, 12, 16]
    visits_list = [64, 96, 128]
    results = []
    total = len(threads_list) * len(visits_list)
    i = 0
    for threads in threads_list:
        for visits in visits_list:
            i += 1
            print(f"[Selfplay {i}/{total}] threads={threads}, visits={visits}, games={games}", flush=True)
            r = run_selfplay_test(threads, visits, games, timeout)
            results.append(r)
            status = "OK" if r.get("success") else "FAIL"
            print(f"  → {status} | RAM: {r.get('ram_after_gb',0):.1f}GB | "
                  f"VRAM: {r.get('gpu_mem_peak_mb',0)}MiB | "
                  f"Games/min: {r.get('games_per_min',0):.1f}", flush=True)
    return results


def run_train_bench(timeout=600):
    """Run training benchmark suite."""
    from train_bench import run_train_test
    batches = [32, 64, 128]
    samples_list = [50000, 100000, 150000]
    results = []
    total = len(batches) * len(samples_list)
    i = 0
    for batch in batches:
        for samples in samples_list:
            i += 1
            print(f"[Train {i}/{total}] batch={batch}, samples={samples}", flush=True)
            r = run_train_test(batch, samples, timeout_sec=timeout)
            results.append(r)
            status = "OK" if r.get("success") else "FAIL"
            print(f"  → {status} | VRAM: {r.get('gpu_mem_peak_mb',0)}MiB | "
                  f"Step p50: {r.get('step_time_p50',0):.1f}s | "
                  f"Steps/s: {r.get('steps_per_sec',0):.4f}", flush=True)
    return results


def run_pk_bench(games=10, timeout=300):
    """Run PK benchmark suite."""
    from pk_bench import run_pk_test
    visits_list = [64, 128, 256]
    results = []
    for i, visits in enumerate(visits_list, 1):
        print(f"[PK {i}/{len(visits_list)}] visits={visits}, games={games}", flush=True)
        r = run_pk_test(visits, games, timeout)
        results.append(r)
        status = "OK" if r.get("success") else "FAIL"
        print(f"  → {status} | RAM: {r.get('ram_after_gb',0):.1f}GB | "
              f"Games/min: {r.get('games_per_min',0):.1f}", flush=True)
    return results


def find_best(results, key, metric, higher_is_better=True, safety_margin=0.8):
    """Find the best config that stays within safety margin of peak resource usage."""
    if not results:
        return None
    valid = [r for r in results if r.get("success")]
    if not valid:
        return results[0] if results else None

    # Sort by the metric
    sorted_r = sorted(valid, key=lambda r: r.get(metric, 0), reverse=higher_is_better)

    # Pick the best that's within safety limits
    for r in sorted_r:
        ram = r.get("ram_peak_gb", r.get("ram_after_gb", 0))
        vram = r.get("gpu_mem_peak_mb", 0)
        if ram < 7.7 * safety_margin and vram < 4096 * safety_margin:
            return r
    return sorted_r[0] if sorted_r else None


def build_profile(hardware, sp_results, train_results, pk_results):
    """Build machine_profile.json from benchmark results."""
    profile = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware,
        "model": "b10c256nbt",
        "params_count": 6491653,
    }

    # Selfplay analysis
    sp_valid = [r for r in sp_results if r.get("success")]
    if sp_valid:
        sp_best = find_best(sp_valid, "sf_threads", "games_per_min")
        profile["selfplay"] = {
            "best": {
                "sf_threads": sp_best.get("sf_threads") if sp_best else 8,
                "sf_visits": sp_best.get("sf_visits") if sp_best else 128,
            },
            "ram_safe_limit_gb": round(hardware["ram_gb"] * 0.7, 1),
            "results": [{k: v for k, v in r.items() if k != "samples"} for r in sp_results],
        }

    # Train analysis
    train_valid = [r for r in train_results if r.get("success")]
    if train_valid:
        train_best = find_best(train_valid, "tr_batch", "steps_per_sec")
        profile["train"] = {
            "best": {
                "tr_batch": train_best.get("tr_batch") if train_best else 64,
                "sh_samples": train_best.get("sh_samples") if train_best else 50000,
            },
            "results": [{k: v for k, v in r.items() if k != "samples"} for r in train_results],
        }

    # PK analysis
    pk_valid = [r for r in pk_results if r.get("success")]
    if pk_valid:
        pk_best = find_best(pk_valid, "pk_visits", "games_per_min")
        profile["pk"] = {
            "best": {
                "pk_visits": pk_best.get("pk_visits") if pk_best else 128,
            },
            "results": [{k: v for k, v in r.items() if k != "samples"} for r in pk_results],
        }

    return profile


def main():
    parser = argparse.ArgumentParser(description="Machine Benchmark Suite")
    parser.add_argument("--full", action="store_true", help="Run all benchmarks")
    parser.add_argument("--selfplay-only", action="store_true")
    parser.add_argument("--train-only", action="store_true")
    parser.add_argument("--pk-only", action="store_true")
    parser.add_argument("--sp-games", type=int, default=20)
    parser.add_argument("--pk-games", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    if not any([args.full, args.selfplay_only, args.train_only, args.pk_only]):
        args.full = True

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    hardware = get_hardware_info()
    print(f"Hardware: {hardware['gpu']}, VRAM: {hardware['vram_mb']}MB, RAM: {hardware['ram_gb']}GB", flush=True)
    print(f"Platform: {hardware['platform']}", flush=True)
    print("=" * 60, flush=True)

    sp_results, train_results, pk_results = [], [], []

    if args.full or args.selfplay_only:
        print("\n=== SELFPLAY BENCHMARK ===", flush=True)
        sp_results = run_selfplay_bench(args.sp_games, args.timeout)
        (RESULTS_DIR / "selfplay_bench.json").write_text(json.dumps(sp_results, indent=2))

    if args.full or args.train_only:
        print("\n=== TRAIN BENCHMARK ===", flush=True)
        train_results = run_train_bench(args.timeout)
        (RESULTS_DIR / "train_bench.json").write_text(json.dumps(train_results, indent=2))

    if args.full or args.pk_only:
        print("\n=== PK BENCHMARK ===", flush=True)
        pk_results = run_pk_bench(args.pk_games, args.timeout)
        (RESULTS_DIR / "pk_bench.json").write_text(json.dumps(pk_results, indent=2))

    # Build profile
    profile = build_profile(hardware, sp_results, train_results, pk_results)
    PROFILE_PATH.write_text(json.dumps(profile, indent=2))
    print(f"\n{'=' * 60}", flush=True)
    print(f"Machine profile saved to {PROFILE_PATH}", flush=True)
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
