import gzip
import json
import os
import queue
import shlex
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
KATA_ROOT = PROJECT_ROOT / "KataGomo"
PY_DIR = KATA_ROOT / "python"
DEFAULT_DATA_DIR = KATA_ROOT / "training_data"
LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "kata_training_backend.log"
STATE_PATH = BASE_DIR / "training_ui_state.json"
GAME_MODEL_PATH = KATA_ROOT / "models" / "model.bin.gz"
NATIVE_SELFPLAY_CFG = DEFAULT_DATA_DIR / "native_selfplay_15.cfg"


def now_text():
    return time.strftime("%H:%M:%S")


def quote_cmd(cmd):
    if os.name == "nt":
        return subprocess.list2cmdline([str(part) for part in cmd])
    return " ".join(shlex.quote(str(part)) for part in cmd)


class TrainingBackendUI:
    def __init__(self, root):
        self.root = root
        self.root.title("KataGomo Training Backend")
        self.proc = None
        self.proc_name = None
        self.log_queue = queue.Queue()
        self.vars = {}
        self.status_vars = {}

        self._build_vars()
        self._load_state()
        self._build_ui()
        self.refresh_status()
        self.root.after(100, self._drain_log_queue)

    def _build_vars(self):
        default_worker_threads = str(max(1, min(4, (os.cpu_count() or 4) // 2)))
        defaults = {
            "python_cmd": "uv run python",
            "kata_root": str(KATA_ROOT),
            "data_dir": str(DEFAULT_DATA_DIR),
            "engine_path": str(KATA_ROOT / "scripts" / "engine" / ("katago" if sys.platform != "win32" else "katago.exe")),
            "selfplay_cfg": str(NATIVE_SELFPLAY_CFG),
            "model_name": "b10c256nbt",
            "model_kind": "b10c256nbt",
            "batch_size": "128",
            "gpu": "0",
            "max_games": "4000",
            "selfplay_threads": default_worker_threads,
            "selfplay_visits": "50",
            "shuffle_threads": default_worker_threads,
            "samples_per_epoch": "200000",
            "tmp_dir": str(DEFAULT_DATA_DIR / "shuffle_tmp"),
            "checkpoint": "",
            "use_fp16": "0",
            # Train loss/optimizer params
            "pos_len": "15",
            "soft_policy_weight_scale": "8.0",
            "value_loss_scale": "0.6",
            "td_value_loss_scales": "0.6,0.6,0.6",
            "lookahead_alpha": "0.5",
            "lookahead_k": "6",
            "swa_scale": "1.0",
            # Shuffle params
            "expand_window_per_row": "0.3",
            "taper_window_exponent": "0.8",
            "approx_rows_per_file": "50000",
        }
        for key, value in defaults.items():
            self.vars[key] = tk.StringVar(value=value)

    _MAX_JSON_SIZE = 50 * 1024 * 1024  # 50MB

    def _load_state(self):
        if not STATE_PATH.exists():
            return
        try:
            if STATE_PATH.stat().st_size > self._MAX_JSON_SIZE:
                print(f"Warning: {STATE_PATH} exceeds 50MB limit, skipping load", file=sys.stderr)
                return
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        for key, value in data.items():
            if key in self.vars:
                self.vars[key].set(str(value))

    def _save_state(self):
        data = {key: var.get() for key, var in self.vars.items()}
        STATE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log("Saved settings")

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=10)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        paths = ttk.LabelFrame(outer, text="Paths")
        paths.grid(row=0, column=0, sticky="ew")
        paths.columnconfigure(1, weight=1)
        self._add_path_row(paths, 0, "Kata root", "kata_root", directory=True)
        self._add_path_row(paths, 1, "Data dir", "data_dir", directory=True)
        self._add_path_row(paths, 2, "Engine exe", "engine_path", file=True)
        self._add_path_row(paths, 3, "Selfplay cfg", "selfplay_cfg", file=True)
        self._add_path_row(paths, 4, "Checkpoint", "checkpoint", file=True)

        params = ttk.LabelFrame(outer, text="Parameters")
        params.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        for i in range(6):
            params.columnconfigure(i, weight=1)
        fields = [
            ("Python", "python_cmd"),
            ("Model name", "model_name"),
            ("Model kind", "model_kind"),
            ("Batch", "batch_size"),
            ("GPU", "gpu"),
            ("Games", "max_games"),
            ("Selfplay threads", "selfplay_threads"),
            ("Selfplay visits", "selfplay_visits"),
            ("Shuffle threads", "shuffle_threads"),
            ("Samples/epoch", "samples_per_epoch"),
            ("Tmp dir", "tmp_dir"),
        ]
        for idx, (label, key) in enumerate(fields):
            row = idx // 3
            col = (idx % 3) * 2
            ttk.Label(params, text=label).grid(row=row, column=col, sticky="w", padx=(6, 4), pady=4)
            ttk.Entry(params, textvariable=self.vars[key]).grid(row=row, column=col + 1, sticky="ew", padx=(0, 8), pady=4)

        fp16_row = (len(fields)) // 3
        fp16_col = ((len(fields)) % 3) * 2
        ttk.Label(params, text="FP16").grid(row=fp16_row, column=fp16_col, sticky="w", padx=(6, 4), pady=4)
        self._fp16_var = tk.BooleanVar(value=(self.vars["use_fp16"].get() == "1"))
        fp16_cb = ttk.Checkbutton(params, variable=self._fp16_var, command=lambda: self.vars["use_fp16"].set("1" if self._fp16_var.get() else "0"))
        fp16_cb.grid(row=fp16_row, column=fp16_col + 1, sticky="w", padx=(0, 8), pady=4)

        actions = ttk.Frame(outer)
        actions.grid(row=2, column=0, sticky="ew", pady=8)
        for text, command in [
            ("Refresh", self.refresh_status),
            ("Check Deps", self.check_deps),
            ("Native Init", self.native_init),
            ("Init Dirs", self.init_dirs),
            ("Selfplay", self.start_selfplay),
            ("Shuffle", self.start_shuffle),
            ("Train", self.start_train),
            ("Export", self.start_export),
            ("Use Exported Model", self.use_exported_model),
            ("Stop", self.stop_task),
            ("Save Settings", self._save_state),
        ]:
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=3)

        body = ttk.PanedWindow(outer, orient="horizontal")
        body.grid(row=3, column=0, sticky="nsew")

        status = ttk.LabelFrame(body, text="Status")
        status.columnconfigure(1, weight=1)
        body.add(status, weight=1)
        for idx, key in enumerate(["kata_root", "python_dir", "engine", "native_init", "model", "data_selfplay", "data_shuffled", "latest_export"]):
            ttk.Label(status, text=key).grid(row=idx, column=0, sticky="w", padx=6, pady=3)
            var = tk.StringVar(value="-")
            self.status_vars[key] = var
            ttk.Label(status, textvariable=var).grid(row=idx, column=1, sticky="w", padx=6, pady=3)

        logs = ttk.LabelFrame(body, text="Log")
        logs.rowconfigure(0, weight=1)
        logs.columnconfigure(0, weight=1)
        body.add(logs, weight=3)
        self.log_text = tk.Text(logs, height=24, wrap="word")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(logs, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _add_path_row(self, parent, row, label, key, directory=False, file=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(parent, textvariable=self.vars[key]).grid(row=row, column=1, sticky="ew", padx=4, pady=4)

        def browse():
            if directory:
                value = filedialog.askdirectory(initialdir=self.vars[key].get() or str(BASE_DIR))
            elif file:
                value = filedialog.askopenfilename(initialdir=str(Path(self.vars[key].get() or BASE_DIR).parent))
            else:
                value = ""
            if value:
                self.vars[key].set(value)
                self.refresh_status()

        ttk.Button(parent, text="Browse", command=browse).grid(row=row, column=2, padx=4, pady=4)

    def log(self, message):
        line = f"[{now_text()}] {message}"
        self.log_queue.put(line)
        with LOG_PATH.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(line + "\n")

    def _drain_log_queue(self):
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
        self.root.after(100, self._drain_log_queue)

    def refresh_status(self):
        kata_root = Path(self.vars["kata_root"].get())
        data_dir = Path(self.vars["data_dir"].get())
        engine = Path(self.vars["engine_path"].get())
        self.status_vars["kata_root"].set("OK" if kata_root.exists() else "missing")
        self.status_vars["python_dir"].set("OK" if (kata_root / "python" / "train.py").exists() else "missing")
        self.status_vars["engine"].set("OK" if engine.exists() else f"missing {engine.name}")
        native_cfg = Path(self.vars["selfplay_cfg"].get())
        native_models = data_dir / "models"
        self.status_vars["native_init"].set("OK" if native_cfg.exists() and native_models.exists() else "missing")
        self.status_vars["model"].set("OK" if GAME_MODEL_PATH.exists() else "missing Game UI model")
        self.status_vars["data_selfplay"].set(str(len(list((data_dir / "selfplay").rglob("*.npz")))) + " npz" if (data_dir / "selfplay").exists() else "missing")
        self.status_vars["data_shuffled"].set("OK" if (data_dir / "shuffleddata" / "current").exists() else "missing")
        latest = self.find_latest_exported_bin()
        self.status_vars["latest_export"].set(str(latest) if latest else "missing")

    def init_dirs(self):
        data_dir = Path(self.vars["data_dir"].get())
        for path in [
            data_dir,
            data_dir / "selfplay",
            data_dir / "models",
            data_dir / "shuffleddata" / "current",
            data_dir / "torchmodels_toexport",
            data_dir / "models_exported",
            Path(self.vars["tmp_dir"].get()),
            GAME_MODEL_PATH.parent,
        ]:
            path.mkdir(parents=True, exist_ok=True)
        self.log("Initialized training directories")
        self.refresh_status()

    def native_init(self):
        self.init_dirs()
        cfg_path = Path(self.vars["selfplay_cfg"].get())
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        if not cfg_path.exists():
            cfg_path.write_text(self.native_selfplay_cfg_text(), encoding="utf-8")
            self.log(f"Wrote native 15x15 selfplay config: {cfg_path}")
        else:
            self.ensure_native_cfg_keys(cfg_path)
            self.log(f"Keeping existing selfplay config: {cfg_path}")
        self.sync_native_runtime_cfg(cfg_path)
        self.log("Native init ready: an empty models-dir will make KataGomo selfplay use the random bootstrap model.")
        self.refresh_status()

    def sync_native_runtime_cfg(self, cfg_path):
        updates = {
            "gpuToUseThread0": self.vars["gpu"].get(),
            "numGameThreads": self.vars["selfplay_threads"].get(),
            "maxVisits": self.vars["selfplay_visits"].get(),
            "nnMaxBatchSize": self.vars["batch_size"].get(),
            "dataBoardLen": self.vars["pos_len"].get(),
            "bSizes": self.vars["pos_len"].get(),
        }
        text = cfg_path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        seen = set()
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                lines[idx] = f"{key} = {updates[key]}"
                seen.add(key)
        for key, value in updates.items():
            if key not in seen:
                lines.append(f"{key} = {value}")
        cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def ensure_native_cfg_keys(self, cfg_path):
        text = cfg_path.read_text(encoding="utf-8", errors="ignore")
        existing = set()
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            existing.add(stripped.split("=", 1)[0].strip())
        missing_lines = []
        for line in self.native_required_cfg_tail().splitlines():
            if not line.strip() or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key not in existing:
                missing_lines.append(line)
        if missing_lines:
            with cfg_path.open("a", encoding="utf-8") as f:
                f.write("\n# Native bootstrap defaults added by training_ui.py\n")
                f.write("\n".join(missing_lines))
                f.write("\n")
            self.log(f"Patched missing native config keys: {', '.join(line.split('=', 1)[0].strip() for line in missing_lines)}")

    def native_required_cfg_tail(self):
        return """\
stopIfNewNet = false
quietSelfplay = false
numSearchThreads = 1
allowResignation = false
resignThreshold = -0.90
resignConsecTurns = 3
allowEarlyDraw = false
earlyDrawThreshold = 0.99
earlyDrawConsecTurns = 10
earlyDrawProbSelfplay = 0.0
policySurpriseDataWeight = 0.0
valueSurpriseDataWeight = 0.0
sidePositionProb = 0.0
basicRules = FREESTYLE
VCNRules = NOVC
firstPassWinRules = false
"""

    def native_selfplay_cfg_text(self):
        return f"""\
numNNServerThreadsPerModel = 1
gpuToUseThread0 = {self.vars["gpu"].get()}

useGraphSearch=true

numGameThreads = {self.vars["selfplay_threads"].get()}
numSearchThreads = 1
nnMaxBatchSize = {self.vars["batch_size"].get()}

nnCacheSizePowerOfTwo = 20
nnMutexPoolSizePowerOfTwo = 16
nnRandomize = true

maxVisits = {self.vars["selfplay_visits"].get()}
cheapSearchProb = 0.0
cheapSearchVisits = 10
reducedVisitsMin = 10

dataBoardLen = {self.vars["pos_len"].get()}
bSizes = {self.vars["pos_len"].get()}
bSizeRelProbs = 1
allowRectangleProb = 0.00
maxMovesPerGame = 400

basicRules = FREESTYLE
VCNRules = NOVC
firstPassWinRules = false

logSearchInfo = false
logMoves = false
logGamesEvery = 20
logToStdout = true

switchNetsMidGame=false
stopIfNewNet = false
quietSelfplay = false
validationProp=0.0

maxDataQueueSize = 20000
maxRowsPerTrainFile = 25000
maxRowsPerValFile = 5000
firstFileRandMinProp = 0.15

initGamesWithPolicy = true
allowResignation = false
resignThreshold = -0.90
resignConsecTurns = 3
allowEarlyDraw = false
earlyDrawThreshold = 0.99
earlyDrawConsecTurns = 10
earlyDrawProbSelfplay = 0.0
policyInitAreaTemperature=1.6
policyInitAvgMoveNum = 6

chosenMoveTemperatureEarly = 0.75
chosenMoveTemperatureHalflife = 6
chosenMoveTemperature = 0.15
chosenMoveSubtract = 0
chosenMovePrune = 1

cheapSearchTargetWeight = 0.0
reduceVisits = true
reduceVisitsThreshold = 0.90
reduceVisitsThresholdLookback = 3
reducedVisitsWeight = 0.1
policySurpriseDataWeight = 0.0
valueSurpriseDataWeight = 0.0
sidePositionProb = 0.0

normalAsymmetricPlayoutProb = 0.1
maxAsymmetricRatio = 4.0
"""

    def python_cmd(self):
        return shlex.split(self.vars["python_cmd"].get())

    def missing_modules(self, modules):
        code = (
            "import importlib.util,sys;"
            "mods=sys.argv[1:];"
            "missing=[m for m in mods if importlib.util.find_spec(m) is None];"
            "print('\\n'.join(missing));"
            "sys.exit(1 if missing else 0)"
        )
        cmd = self.python_cmd() + ["-c", code] + list(modules)
        try:
            result = subprocess.run(cmd, cwd=str(PY_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
        except Exception as exc:
            self.log(f"Dependency check failed to start: {exc}")
            return list(modules)
        missing = [line.strip() for line in result.stdout.splitlines() if line.strip() in modules]
        return missing

    def require_modules(self, modules, purpose):
        missing = self.missing_modules(modules)
        if not missing:
            return True
        self.log(f"Missing Python modules for {purpose}: {', '.join(missing)}")
        install_cmd = "uv pip install " + " ".join(missing)
        self.log(f"Install command: {install_cmd}")
        messagebox.showerror("Missing Python modules", f"{purpose} needs: {', '.join(missing)}\n\nRun:\n{install_cmd}")
        return False

    def check_deps(self):
        missing = self.missing_modules(["psutil", "numpy", "torch"])
        if missing:
            self.log(f"Missing Python modules: {', '.join(missing)}")
            self.log("Install lightweight deps with: uv pip install psutil numpy")
            self.log("Install PyTorch before Train/Export with the wheel matching your CUDA/Python setup.")
        else:
            self.log("Python dependencies OK: psutil, numpy, torch")
            try:
                import torch
                cuda_ok = torch.cuda.is_available()
                self.log(f"PyTorch CUDA available: {cuda_ok}")
                if cuda_ok:
                    devices = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
                    self.log(f"CUDA devices: {', '.join(devices)}")
                else:
                    self.log("Train will run on CPU until a CUDA-enabled PyTorch wheel is installed.")
            except Exception as exc:
                self.log(f"Could not query PyTorch CUDA status: {exc}")

    def start_process(self, name, cmd, cwd, env=None, on_success=None):
        if self.proc is not None and self.proc.poll() is None:
            messagebox.showwarning("Task running", "A training task is already running.")
            return
        self._save_state()
        self.proc_name = name
        self.log(f"Starting {name}: {quote_cmd(cmd)}")
        self.proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        threading.Thread(target=self._pump_process, args=(self.proc, name, on_success), daemon=True).start()

    def _pump_process(self, proc, name, on_success):
        assert proc.stdout is not None
        for line in proc.stdout:
            self.log(line.rstrip())
        code = proc.wait()
        self.log(f"{name} exited with code {code}")
        if code == 0 and on_success is not None:
            try:
                on_success()
            except Exception as exc:
                self.log(f"post-step failed: {exc}")
        self.refresh_status()

    def stop_task(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            self.log(f"Stop requested for {self.proc_name}")
        else:
            self.log("No running task")

    def start_selfplay(self):
        engine = Path(self.vars["engine_path"].get())
        if not engine.exists():
            self.log(f"Cannot selfplay: engine missing: {engine}")
            messagebox.showerror("Missing engine", "Build the CUDA target first so scripts/engine/katago[.exe] exists.")
            return
        cfg = Path(self.vars["selfplay_cfg"].get())
        if not cfg.exists():
            self.native_init()
        else:
            self.sync_native_runtime_cfg(cfg)
        data_dir = Path(self.vars["data_dir"].get())
        models_dir = data_dir / "models"
        has_model = any(models_dir.rglob("*")) if models_dir.exists() else False
        if has_model:
            self.log("Selfplay will use GPU for neural net inference if the selected model is CUDA-loadable.")
        else:
            self.log("Selfplay is using the random bootstrap model; GPU usage is expected to be near zero.")
        self.log(f"Selfplay CPU workers: {self.vars['selfplay_threads'].get()}, visits/game search: {self.vars['selfplay_visits'].get()}")
        cmd = [
            str(engine),
            "selfplay",
            "-models-dir", str(data_dir / "models"),
            "-config", self.vars["selfplay_cfg"].get(),
            "-output-dir", str(data_dir / "selfplay"),
            "-max-games-total", self.vars["max_games"].get(),
        ]
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.vars["gpu"].get()
        
        def selfplay_success():
            self.log("[挖掘器] 自对弈顺利完成！启动高胜率定式挖掘器...")
            try:
                self.mine_high_winrate_openings()
            except Exception as e:
                self.log(f"[挖掘器] 运行异常: {e}")

        self.start_process("selfplay", cmd, Path(self.vars["kata_root"].get()), env=env, on_success=selfplay_success)

    def mine_high_winrate_openings(self):
        import json
        from ml.verify_symmetry import SymmetryHelper
        from verify_opening_book import OpeningBook
        
        search_log_path = Path(self.vars["kata_root"].get()) / "logs" / "search_logs.jsonl"
        if not search_log_path.exists():
            search_log_path = Path("logs/search_logs.jsonl")
        if not search_log_path.exists():
            search_log_path = Path("search_logs.jsonl")
            
        if not search_log_path.exists():
            self.log(f"[挖掘器] 未找到搜索日志文件: search_logs.jsonl")
            return
            
        self.log(f"[挖掘器] 正在解析搜索日志: {search_log_path}")
        book_path = "opening_book.json"
        book = OpeningBook(book_path)
        
        count = 0
        with open(search_log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except Exception:
                    continue
                    
                # 1. 步数限制 <= 8 (落子手数 <= 8)
                history_len = entry.get("historyLen", 0)
                if history_len > 8:
                    continue
                    
                # 2. Visits 限制 >= 800
                visits = entry.get("kataVisits", 0)
                if visits < 800:
                    continue
                    
                role = entry.get("role", "").lower()
                
                # 3. 寻找 chosenMove 并确定其 winrate
                chosen = entry.get("chosenMove")
                if not chosen:
                    continue
                    
                chosen_x = chosen.get("x")
                chosen_y = chosen.get("y")
                chosen_value = None
                for m in entry.get("moves", []):
                    if m.get("x") == chosen_x and m.get("y") == chosen_y:
                        chosen_value = m.get("kataValue", 0.0)
                        break
                        
                if chosen_value is None:
                    continue
                    
                # Winrate: map from [-1.0, 1.0] to [0.0, 1.0]
                winrate = (chosen_value + 1.0) / 2.0 if chosen_value < 0 or chosen_value > 1.0 else chosen_value
                
                # 4. 胜率过滤: 黑棋 > 65% 或 白棋 > 53%
                is_valid = False
                if role == "black" and winrate > 0.65:
                    is_valid = True
                elif role == "white" and winrate > 0.53:
                    is_valid = True
                    
                if not is_valid:
                    continue
                    
                hist_moves = entry.get("history")
                if hist_moves is None:
                    continue
                    
                hist_coords = [(int(h[0]), int(h[1])) for h in hist_moves]
                
                # Canonicalize
                canon_history, sym_index = SymmetryHelper.get_canonical_sequence(hist_coords)
                canon_next = list(SymmetryHelper.transform_point(chosen_x, chosen_y, sym_index))
                
                # Save to DB
                book.add_move(canon_history, canon_next, source="AI_NOVELTY", weight=1.5, winrate=winrate, visits=visits)
                self.log(f"[挖掘器] 挖掘到高胜率定式：历史={hist_coords} -> 下一手=({chosen_x},{chosen_y})，胜率={winrate:.2%}, visits={visits}")
                count += 1
                
        self.log(f"[挖掘器] 定式挖掘完成，共新增/更新了 {count} 条定式到 {book_path}。")

    def start_shuffle(self):
        if not self.require_modules(["psutil", "numpy"], "Shuffle"):
            return
        self.log(f"Shuffle is CPU-only; using {self.vars['shuffle_threads'].get()} worker processes.")
        data_dir = Path(self.vars["data_dir"].get())
        tmp_dir = Path(self.vars["tmp_dir"].get())
        stats = self.selfplay_data_stats(data_dir / "selfplay")
        if stats["files"] <= 0 or stats["rows"] <= 0:
            self.log("Cannot shuffle: no selfplay npz data found.")
            return
        random_bootstrap = stats["nonrandom_rows"] <= 0
        train_rows = min(self.safe_int(self.vars["samples_per_epoch"].get(), 200000), stats["rows"])
        val_rows = min(51200, stats["rows"])
        if random_bootstrap:
            self.log(
                "Detected random bootstrap data only; using bootstrap shuffle mode "
                f"({stats['files']} files, {stats['rows']} rows)."
            )
        else:
            self.log(
                f"Detected model selfplay data ({stats['files']} files, "
                f"{stats['rows']} rows, {stats['nonrandom_rows']} non-random rows)."
            )
        self.remove_generated_dir(data_dir / "shuffleddata" / "current" / "train", data_dir, "old train shuffle output")
        self.remove_generated_dir(data_dir / "shuffleddata" / "current" / "val", data_dir, "old val shuffle output")
        self.remove_generated_dir(tmp_dir / "train", tmp_dir, "old train shuffle temp")
        self.remove_generated_dir(tmp_dir / "val", tmp_dir, "old val shuffle temp")
        (tmp_dir / "train").mkdir(parents=True, exist_ok=True)
        (tmp_dir / "val").mkdir(parents=True, exist_ok=True)
        train_cmd = self.python_cmd() + [
            "shuffle.py",
            str(data_dir / "selfplay"),
            "-expand-window-per-row", self.vars["expand_window_per_row"].get(),
            "-taper-window-exponent", self.vars["taper_window_exponent"].get(),
            "-out-dir", str(data_dir / "shuffleddata" / "current" / "train"),
            "-out-tmp-dir", str(tmp_dir / "train"),
            "-approx-rows-per-out-file", self.vars["approx_rows_per_file"].get(),
            "-num-processes", self.vars["shuffle_threads"].get(),
            "-batch-size", self.vars["batch_size"].get(),
            "-min-rows", str(max(1, train_rows)),
            "-keep-target-rows", str(max(1, train_rows)),
            "-output-npz",
        ]
        if not random_bootstrap:
            train_cmd += [
                "-only-include-md5-path-prop-lbound", "0.00",
                "-only-include-md5-path-prop-ubound", "0.97",
            ]
        val_cmd = self.python_cmd() + [
            "shuffle.py",
            str(data_dir / "selfplay"),
            "-expand-window-per-row", self.vars["expand_window_per_row"].get(),
            "-taper-window-exponent", self.vars["taper_window_exponent"].get(),
            "-out-dir", str(data_dir / "shuffleddata" / "current" / "val"),
            "-out-tmp-dir", str(tmp_dir / "val"),
            "-approx-rows-per-out-file", self.vars["approx_rows_per_file"].get(),
            "-num-processes", self.vars["shuffle_threads"].get(),
            "-batch-size", self.vars["batch_size"].get(),
            "-min-rows", str(max(1, val_rows)),
            "-keep-target-rows", str(max(1, val_rows)),
            "-output-npz",
        ]
        if not random_bootstrap:
            val_cmd += [
                "-only-include-md5-path-prop-lbound", "0.97",
                "-only-include-md5-path-prop-ubound", "1.00",
            ]
        if os.name == "nt":
            cmd = ["cmd", "/c", quote_cmd(train_cmd) + " && " + quote_cmd(val_cmd)]
        else:
            cmd = ["bash", "-c", quote_cmd(train_cmd) + " && " + quote_cmd(val_cmd)]
        self.start_process("shuffle", cmd, PY_DIR)

    def safe_int(self, text, default):
        try:
            return int(str(text).strip())
        except Exception:
            return default

    def npz_num_rows(self, path):
        import numpy as np

        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            name = "binaryInputNCHWPacked"
            if name not in names:
                name = "binaryInputNCHWPacked.npy"
            if name not in names:
                raise KeyError(f"binaryInputNCHWPacked missing in {path}")
            with zf.open(name) as npy_file:
                version = np.lib.format.read_magic(npy_file)
                shape, _fortran, _dtype = np.lib.format._read_array_header(npy_file, version)
                return int(shape[0])

    def selfplay_data_stats(self, selfplay_dir):
        stats = {"files": 0, "rows": 0, "random_rows": 0, "nonrandom_rows": 0}
        if not selfplay_dir.exists():
            return stats
        for path in selfplay_dir.rglob("*.npz"):
            try:
                rows = self.npz_num_rows(path)
            except Exception as exc:
                self.log(f"Skipping unreadable selfplay file: {path} ({exc})")
                continue
            path_text = str(path)
            stats["files"] += 1
            stats["rows"] += rows
            if "random\\tdata\\" in path_text or "random/tdata/" in path_text:
                stats["random_rows"] += rows
            else:
                stats["nonrandom_rows"] += rows
        return stats

    def remove_generated_dir(self, path, root, label):
        try:
            resolved_path = path.resolve()
            resolved_root = root.resolve()
            resolved_path.relative_to(resolved_root)
        except Exception:
            self.log(f"Refusing to remove {label}: {path}")
            raise
        if resolved_path.exists():
            shutil.rmtree(resolved_path)
            self.log(f"Removed {label}: {resolved_path}")

    def start_train(self):
        if not self.require_modules(["numpy", "torch"], "Train"):
            return
        model_kind = self.vars["model_kind"].get().strip()
        if not self.validate_model_kind(model_kind):
            return
        try:
            import torch
            if torch.cuda.is_available():
                self.log(f"Train will use CUDA device {self.vars['gpu'].get()}: {torch.cuda.get_device_name(int(self.vars['gpu'].get()))}")
            else:
                self.log("Train will run on CPU because torch.cuda.is_available() is false.")
        except Exception as exc:
            self.log(f"Could not query train CUDA status: {exc}")
        data_dir = Path(self.vars["data_dir"].get())
        name = self.vars["model_name"].get()
        cmd = self.python_cmd() + [
            "train.py",
            "-traindir", str(data_dir / "train" / name),
            "-datadir", str(data_dir / "shuffleddata" / "current"),
            "-exportdir", str(data_dir / "torchmodels_toexport"),
            "-exportprefix", name,
            "-pos-len", self.vars["pos_len"].get(),
            "-batch-size", self.vars["batch_size"].get(),
            "-model-kind", model_kind,
            "-max-epochs-this-instance", "1",
            "-samples-per-epoch", self.vars["samples_per_epoch"].get(),
            "-soft-policy-weight-scale", self.vars["soft_policy_weight_scale"].get(),
            "-value-loss-scale", self.vars["value_loss_scale"].get(),
            "-td-value-loss-scales", self.vars["td_value_loss_scales"].get(),
            "-lookahead-alpha", self.vars["lookahead_alpha"].get(),
            "-lookahead-k", self.vars["lookahead_k"].get(),
            "-swa-scale", self.vars["swa_scale"].get(),
        ]
        if self.vars["use_fp16"].get() == "1":
            cmd.append("-use-fp16")
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = self.vars["gpu"].get()
        self.start_process("train", cmd, PY_DIR, env=env)

    def validate_model_kind(self, model_kind):
        try:
            import sys
            sys.path.insert(0, str(PY_DIR))
            import modelconfigs
        except Exception as exc:
            self.log(f"Could not validate model kind: {exc}")
            return True
        if model_kind in modelconfigs.config_of_name:
            return True
        suggestions = [name for name in modelconfigs.base_config_of_name.keys() if name.startswith(model_kind[:4])]
        if not suggestions:
            suggestions = ["b10c128", "b10c256nbt", "b20c256"]
        self.log(f"Invalid model kind: {model_kind}")
        self.log(f"Try one of: {', '.join(suggestions[:8])}")
        messagebox.showerror("Invalid model kind", f"Unknown model kind: {model_kind}\n\nTry: {', '.join(suggestions[:8])}")
        return False

    def find_latest_checkpoint(self):
        checkpoint = self.vars["checkpoint"].get().strip()
        if checkpoint and Path(checkpoint).exists():
            return Path(checkpoint)
        data_dir = Path(self.vars["data_dir"].get())
        candidates = list((data_dir / "torchmodels_toexport").rglob("model.ckpt"))
        candidates += list((data_dir / "train").rglob("model.ckpt"))
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def start_export(self):
        if not self.require_modules(["numpy", "torch"], "Export"):
            return
        checkpoint = self.find_latest_checkpoint()
        if checkpoint is None:
            self.log("Cannot export: no model.ckpt found")
            messagebox.showerror("Missing checkpoint", "Train first, or select a model.ckpt in the Checkpoint field.")
            return
        export_dir = Path(self.vars["data_dir"].get()) / "models_exported" / self.vars["model_name"].get()
        export_dir.mkdir(parents=True, exist_ok=True)
        cmd = self.python_cmd() + [
            "export_model_pytorch.py",
            "-checkpoint", str(checkpoint),
            "-export-dir", str(export_dir),
            "-model-name", self.vars["model_name"].get(),
            "-filename-prefix", "model",
        ]
        swa = self.vars.get("swa_scale")
        if swa is None or float(swa.get() or 1.0) > 0:
            cmd.append("-use-swa")
        self.start_process("export", cmd, PY_DIR, on_success=lambda: self._gzip_export(export_dir))

    def _gzip_export(self, export_dir):
        raw = Path(export_dir) / "model.bin"
        gz = Path(export_dir) / "model.bin.gz"
        if raw.exists():
            with raw.open("rb") as src, gzip.open(gz, "wb") as dst:
                shutil.copyfileobj(src, dst)
            self.log(f"Compressed exported model: {gz}")
        elif gz.exists():
            self.log(f"Exported model already compressed: {gz}")
        else:
            self.log(f"Export finished but model.bin was not found in {export_dir}")

    def find_latest_exported_bin(self):
        data_dir = Path(self.vars["data_dir"].get())
        candidates = list((data_dir / "models_exported").rglob("model.bin.gz"))
        candidates += list((data_dir / "models").rglob("model.bin.gz"))
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def use_exported_model(self):
        latest = self.find_latest_exported_bin()
        if latest is None:
            messagebox.showerror("No exported model", "No model.bin.gz found under the training data directory.")
            return
        GAME_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(latest, GAME_MODEL_PATH)
        self.log(f"Copied {latest} -> {GAME_MODEL_PATH}")
        self.refresh_status()


def main():
    root = tk.Tk()
    root.geometry("1180x720")
    TrainingBackendUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
