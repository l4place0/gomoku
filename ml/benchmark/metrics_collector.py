#!/usr/bin/env python3
"""
Passive metrics collector for embedding into automl_cli.py.

Usage in automl_cli.py:
    from ml.benchmark.metrics_collector import StageMetrics

    # Before a stage:
    m = StageMetrics(round_no, "selfplay")
    m.start()

    # ... run stage ...

    # After a stage:
    m.finish()
    m.append_to_log(LOG_DIR / "metrics.jsonl")

For per-step training metrics:
    m.log_step(step=0, step_time=41.2, p0loss=5.42, vloss=1.30)
"""

import json
import time
import threading
from pathlib import Path
from datetime import datetime, timezone


def _gpu_stats():
    try:
        import subprocess
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            timeout=5, text=True
        ).strip()
        parts = out.split(",")
        return int(parts[0].strip()), int(parts[1].strip())
    except Exception:
        return 0, 0


def _ram_gb():
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


class StageMetrics:
    """Collects resource metrics for a single pipeline stage."""

    def __init__(self, round_no: int, stage: str):
        self.round_no = round_no
        self.stage = stage
        self.start_time = None
        self.end_time = None
        self.ram_before = 0.0
        self.ram_after = 0.0
        self.gpu_mem_peak = 0
        self.gpu_util_avg = 0
        self.steps = []
        self.extra = {}

        self._gpu_samples = []
        self._sampler_stop = None
        self._sampler_thread = None

    def start(self):
        """Call before the stage begins."""
        self.start_time = time.time()
        self.ram_before = _ram_gb()
        gpu_mem, gpu_util = _gpu_stats()
        self.gpu_mem_peak = gpu_mem
        self._gpu_samples = []

        # Background sampler
        self._sampler_stop = threading.Event()
        self._sampler_thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._sampler_thread.start()

    def _sample_loop(self):
        while not self._sampler_stop.is_set():
            gpu_mem, gpu_util = _gpu_stats()
            self._gpu_samples.append((gpu_mem, gpu_util))
            if gpu_mem > self.gpu_mem_peak:
                self.gpu_mem_peak = gpu_mem
            self._sampler_stop.wait(5.0)

    def log_step(self, step: int, **kwargs):
        """Log a training step's metrics."""
        entry = {"step": step, "ts": time.time()}
        entry.update(kwargs)
        self.steps.append(entry)

    def finish(self, **extra):
        """Call after the stage ends."""
        self._sampler_stop.set()
        self._sampler_thread.join(timeout=6)
        self.end_time = time.time()
        self.ram_after = _ram_gb()
        self.extra = extra

        if self._gpu_samples:
            utils = [s[1] for s in self._gpu_samples]
            self.gpu_util_avg = round(sum(utils) / len(utils))

    def to_dict(self):
        """Serialize to a flat dict suitable for JSONL."""
        d = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "round": self.round_no,
            "stage": self.stage,
            "wall_time_sec": round(self.end_time - self.start_time, 2) if self.end_time else 0,
            "ram_before_gb": self.ram_before,
            "ram_after_gb": self.ram_after,
            "ram_delta_gb": round(self.ram_after - self.ram_before, 2),
            "gpu_mem_peak_mb": self.gpu_mem_peak,
            "gpu_util_avg_pct": self.gpu_util_avg,
        }
        d.update(self.extra)
        return d

    def append_to_log(self, path):
        """Append summary to a JSONL metrics log."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(self.to_dict(), ensure_ascii=False) + "\n")

        # Also write per-step data if any
        if self.steps:
            step_path = path.with_name(f"{path.stem}_steps_r{self.round_no}_{self.stage}.jsonl")
            with open(step_path, "a") as f:
                for s in self.steps:
                    f.write(json.dumps(s, ensure_ascii=False) + "\n")
