#!/usr/bin/env python3
"""Resource collectors for GPU, RAM, and CPU monitoring."""

import subprocess
import time
import threading
import json
from pathlib import Path


def get_gpu_stats():
    """Return (memory_used_mb, utilization_pct) from nvidia-smi."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            timeout=5, text=True
        ).strip()
        parts = out.split(",")
        return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        return 0, 0


def get_ram_gb():
    """Return used RAM in GB from /proc/meminfo."""
    try:
        with open("/proc/meminfo") as f:
            info = {}
            for line in f:
                parts = line.split()
                info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        return round((total - avail) / 1024 / 1024, 2)
    except Exception:
        return 0.0


def get_ram_delta():
    """Return (before_gb, after_gb) context manager usage."""
    return get_ram_gb()


class ResourceSampler:
    """Background thread that samples GPU/RAM at fixed interval."""

    def __init__(self, interval=2.0):
        self.interval = interval
        self.samples = []
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        self.samples = []
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self):
        while not self._stop.is_set():
            gpu_mem, gpu_util = get_gpu_stats()
            ram = get_ram_gb()
            self.samples.append({
                "ts": time.time(),
                "gpu_mem_mb": gpu_mem,
                "gpu_util_pct": gpu_util,
                "ram_gb": ram,
            })
            self._stop.wait(self.interval)

    def summary(self):
        if not self.samples:
            return {}
        gpu_mems = [s["gpu_mem_mb"] for s in self.samples]
        gpu_utils = [s["gpu_util_pct"] for s in self.samples]
        rams = [s["ram_gb"] for s in self.samples]
        return {
            "gpu_mem_peak_mb": max(gpu_mems),
            "gpu_mem_avg_mb": round(sum(gpu_mems) / len(gpu_mems)),
            "gpu_util_avg_pct": round(sum(gpu_utils) / len(gpu_utils)),
            "ram_peak_gb": max(rams),
            "ram_avg_gb": round(sum(rams) / len(rams), 2),
            "samples": len(self.samples),
        }


def timed_run(fn, *args, **kwargs):
    """Run a function and return (result, wall_time_seconds)."""
    start = time.time()
    result = fn(*args, **kwargs)
    elapsed = time.time() - start
    return result, round(elapsed, 2)
