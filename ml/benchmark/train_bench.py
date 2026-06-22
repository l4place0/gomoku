#!/usr/bin/env python3
"""Training benchmark: sweep tr_batch × sh_samples, measure VRAM/throughput."""

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
TRAIN_PY = KATA_ROOT / "python" / "train.py"
DATA_DIR = PROJECT_ROOT / "ml" / "data" / "training_data"


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


def run_train_test(tr_batch, sh_samples, tr_epochs=1, timeout_sec=600):
    """Run a single training config and return resource metrics."""
    test_dir = Path(f"/tmp/bench_train_b{tr_batch}_s{sh_samples}")
    train_dir = test_dir / "train" / "bench"
    export_dir = test_dir / "export"
    if test_dir.exists():
        shutil.rmtree(test_dir)
    train_dir.mkdir(parents=True)
    export_dir.mkdir(parents=True)

    # Use existing shuffled data
    datadir = DATA_DIR / "shuffleddata" / "current"
    if not (datadir / "train" / "data0.npz").exists():
        return {"error": "No shuffled data found"}

    sampler = ResourceSampler(interval=2.0)
    ram_before = get_ram_gb()

    cmd = [
        find_python(), str(TRAIN_PY),
        "-traindir", str(train_dir),
        "-datadir", str(datadir),
        "-exportdir", str(export_dir),
        "-exportprefix", "bench",
        "-pos-len", "15",
        "-batch-size", str(tr_batch),
        "-model-kind", "b10c256nbt",
        "-max-epochs-this-instance", str(tr_epochs),
        "-samples-per-epoch", str(sh_samples),
        "-swa-scale", "1.0",
        "-lookahead-alpha", "0.5",
        "-lookahead-k", "6",
    ]

    sampler.start()
    start = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec, env=gpu_env())
        ok = proc.returncode == 0
        stderr = proc.stderr[-500:] if proc.stderr else ""
    except subprocess.TimeoutExpired:
        ok = False
        stderr = "timeout"
    wall_time = round(time.time() - start, 2)
    sampler.stop()

    ram_after = get_ram_gb()

    # Parse step times from stdout
    step_times = []
    for line in (proc.stdout or "").split("\n"):
        if "nsamp=" in line and "time=" in line:
            try:
                t = float(line.split("time=")[1].split(",")[0])
                step_times.append(t)
            except (ValueError, IndexError):
                pass

    summary = sampler.summary()
    summary.update({
        "tr_batch": tr_batch,
        "sh_samples": sh_samples,
        "tr_epochs": tr_epochs,
        "wall_time_sec": wall_time,
        "ram_before_gb": ram_before,
        "ram_after_gb": ram_after,
        "ram_delta_gb": round(ram_after - ram_before, 2),
        "steps_completed": len(step_times),
        "step_time_p50": sorted(step_times)[len(step_times) // 2] if step_times else 0,
        "step_time_p99": sorted(step_times)[int(len(step_times) * 0.99)] if step_times else 0,
        "step_time_first": step_times[0] if step_times else 0,
        "step_time_last": step_times[-1] if step_times else 0,
        "steps_per_sec": round(len(step_times) / wall_time, 4) if wall_time > 0 else 0,
        "success": ok,
        "error": stderr if not ok else "",
    })

    shutil.rmtree(test_dir, ignore_errors=True)
    return summary


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--output", type=str, default=str(Path(__file__).parent / "results" / "train_bench.json"))
    parser.add_argument("--batches", type=str, default="32,64,128")
    parser.add_argument("--samples", type=str, default="50000,100000,150000")
    args = parser.parse_args()

    batches = [int(x) for x in args.batches.split(",")]
    samples_list = [int(x) for x in args.samples.split(",")]

    results = []
    total = len(batches) * len(samples_list)
    i = 0
    for batch in batches:
        for samples in samples_list:
            i += 1
            print(f"[{i}/{total}] Testing tr_batch={batch}, sh_samples={samples}...", flush=True)
            r = run_train_test(batch, samples, timeout_sec=args.timeout)
            results.append(r)
            status = "OK" if r.get("success") else "FAIL"
            print(f"  → {status} | VRAM peak: {r.get('gpu_mem_peak_mb',0)} MiB | "
                  f"RAM: {r.get('ram_before_gb',0):.1f}→{r.get('ram_after_gb',0):.1f} GB | "
                  f"Steps: {r.get('steps_completed',0)} | "
                  f"Step p50: {r.get('step_time_p50',0):.1f}s | "
                  f"Time: {r.get('wall_time_sec',0):.0f}s", flush=True)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to {output}")


if __name__ == "__main__":
    main()
