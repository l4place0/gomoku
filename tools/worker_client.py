"""
WorkerClient: Manages an ai_worker.py subprocess for PK evaluation and dual-model play.

Provides timeout-controlled IPC, process health detection, retry logic,
and board state reset — shared by headless_runner.py and game.py.
"""

import sys
import os
import json
import subprocess
import threading
import time
from typing import Optional, Dict, Any, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
WORKER_SCRIPT = os.path.join(BASE_DIR, "ai_worker.py")


class WorkerClient:
    """Manages an ai_worker.py subprocess with timeout-controlled IPC."""

    def __init__(self, model_path: str, config_path: str, timeout: float = 10.0, max_retries: int = 2):
        self.model_path = model_path
        self.config_path = config_path
        self.timeout = timeout
        self.max_retries = max_retries
        self._proc: Optional[subprocess.Popen] = None

    def start(self) -> bool:
        """Start the worker process and wait for ready signal."""
        env = os.environ.copy()
        cudnn_lib = os.path.join(PROJECT_ROOT, "KataGomo", "cudnn", "lib")
        if os.path.isdir(cudnn_lib):
            env["LD_LIBRARY_PATH"] = cudnn_lib + ":" + env.get("LD_LIBRARY_PATH", "")
        env["CUDA_VISIBLE_DEVICES"] = "0"

        try:
            self._proc = subprocess.Popen(
                [sys.executable, WORKER_SCRIPT, self.model_path, self.config_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as e:
            print(f"[WorkerClient] Failed to start worker: {e}")
            return False

        # Wait for ready signal with timeout
        ready_line = self._readline_with_timeout(self.timeout)
        if ready_line is None:
            print("[WorkerClient] Worker did not send ready signal in time")
            self.close()
            return False

        try:
            status = json.loads(ready_line.strip())
            if status.get("status") == "ready":
                return True
            else:
                print(f"[WorkerClient] Worker startup abnormal: {status}")
                self.close()
                return False
        except json.JSONDecodeError:
            print(f"[WorkerClient] Worker sent non-JSON ready: {ready_line!r}")
            self.close()
            return False

    def query(self, history: List[Tuple[int, int, int]], visits: int = 64,
              policy: float = 0.3, value: float = 0.3, engine: str = "MCTS",
              role: int = 1) -> Dict[str, Any]:
        """Send a search request to the worker. Returns structured result dict."""
        req = {
            "action": "search",
            "history": [[int(x), int(y), int(r)] for x, y, r in history],
            "visits": int(visits),
            "policy": float(policy),
            "value": float(value),
            "engine": str(engine),
            "role": int(role),
        }
        return self._send_and_receive(req)

    def reset_board(self) -> Dict[str, Any]:
        """Tell the worker to reset its local board state."""
        return self._send_and_receive({"action": "reset"})

    def is_alive(self) -> bool:
        """Check if the worker process is still running."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    def close(self):
        """Send quit and terminate the worker process."""
        if self._proc is None:
            return
        try:
            if self._proc.stdin and not self._proc.stdin.closed:
                self._proc.stdin.write("quit\n")
                self._proc.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        try:
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def _send_and_receive(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON request and read response with retry on transient failures."""
        for attempt in range(self.max_retries + 1):
            if not self.is_alive():
                return {"status": "error", "error": "WORKER_CRASHED"}

            try:
                self._proc.stdin.write(json.dumps(req) + "\n")
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                return {"status": "error", "error": f"WRITE_FAILED: {e}"}

            resp_line = self._readline_with_timeout(self.timeout)
            if resp_line is None:
                # Timeout — check if process is still alive
                if self.is_alive():
                    if attempt < self.max_retries:
                        print(f"[WorkerClient] Timeout on attempt {attempt + 1}, retrying...")
                        continue
                    return {"status": "error", "error": "TIMEOUT"}
                else:
                    return {"status": "error", "error": "WORKER_CRASHED"}

            try:
                resp = json.loads(resp_line.strip())
                return resp
            except json.JSONDecodeError:
                return {"status": "error", "error": f"JSON_PARSE_ERROR: {resp_line!r}"}

        return {"status": "error", "error": "MAX_RETRIES_EXCEEDED"}

    def _readline_with_timeout(self, timeout: float) -> Optional[str]:
        """Read a line from stdout with timeout. Returns None on timeout."""
        result = [None]
        error = [None]

        def _read():
            try:
                result[0] = self._proc.stdout.readline()
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=_read, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Timeout — thread is still blocked on readline
            return None

        if error[0] is not None:
            return None

        return result[0]
