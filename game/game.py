import sys
import ctypes
import os
import pygame
from pygame.locals import *
import math
import subprocess
import threading
import time
import json
import logging
import builtins
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from ml.verify_symmetry import SymmetryHelper
from ml.verify_opening_book import OpeningBook
from game.game_logger import GameLogger

# -------------------------------------------------------------------
# DLL 接口封装
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# -------------------------------------------------------------------
# 状态机：GamePhase 枚举 + GameState 数据类 + Undo Stack
# -------------------------------------------------------------------

class GamePhase(Enum):
    """游戏阶段枚举，替代原有 asked_open / asked_three / ai_first_done / five_asked 等散落布尔标志。"""
    INIT        = auto()  # 开局对话框未展示（游戏刚启动）
    AI_FIRST    = auto()  # AI 天元先手（AI执黑，history=0）
    THREE_HAND  = auto()  # 三手交换决策（history=3）
    FIVE_HAND   = auto()  # 五手N打交互（history=4，current_role=BLACK）
    NORMAL      = auto()  # 常规对弈回合
    GAME_OVER   = auto()  # 胜负已分
    TERMINATED  = auto()  # 游戏彻底关闭并退出
    AI_VS_AI    = auto()  # 双 AI 自对弈阶段



@dataclass
class GameState:
    """游戏完整状态快照，可作为 undo_stack 条目存储。

    所有影响游戏逻辑的可变状态集中于此，便于序列化和回溯。
    draw() 等渲染函数从此对象读取数据，不再直接引用全局变量。
    """
    phase:          GamePhase
    history:        List[Tuple[int, int, int]] = field(default_factory=list)  # (x, y, role)
    current_role:   int = 0          # BLACK=0, WHITE=1
    human_is_black: bool = True
    winner:         Optional[int] = None
    five_candidates: List[Tuple[int, int]] = field(default_factory=list)  # 五手N打候选位置
    game_id:        Optional[str] = None
    three_asked:    bool = False     # 三手交换是否已询问决策过的标志
    
    # 双 AI 自对弈新加属性
    game_mode:      int = 0          # 0: 人机/人人, 1: 双 AI 自对弈
    ai_black_cfg:   dict = field(default_factory=lambda: {"visits": 128, "policy": 0.6, "value": 0.6, "engine": "MCTS"})
    ai_white_cfg:   dict = field(default_factory=lambda: {"visits": 64, "policy": 0.3, "value": 0.3, "engine": "MCTS"})
    ai_delay_ms:    int = 500
    is_paused:      bool = False
    white_model_path: str = ""


    def snapshot(self) -> 'GameState':
        """返回当前状态的深拷贝，用于 undo_stack 推入。"""
        return GameState(
            phase=self.phase,
            history=list(self.history),
            current_role=self.current_role,
            human_is_black=self.human_is_black,
            winner=self.winner,
            five_candidates=list(self.five_candidates),
            game_id=self.game_id,
            three_asked=self.three_asked,
            game_mode=self.game_mode,
            ai_black_cfg=dict(self.ai_black_cfg),
            ai_white_cfg=dict(self.ai_white_cfg),
            ai_delay_ms=self.ai_delay_ms,
            is_paused=self.is_paused,
            white_model_path=self.white_model_path,
        )


# Undo Stack 全局列表 — 每次 DoMove/SwapHand 前推入快照
undo_stack: List[GameState] = []


def push_checkpoint(gs: GameState):
    """在任何不可逆状态变更前推入当前状态快照。"""
    undo_stack.append(gs.snapshot())


def apply_undo(gs: GameState) -> bool:
    """弹出一步快照并恢复状态（修改 gs in-place）。

    同时调用 dll.UndoMove 复原棋盘，以及条件性 dll.SwapHand 复原角色。
    返回 True 表示成功回溯，False 表示 undo_stack 已空。
    """
    if not undo_stack:
        return False
    prev = undo_stack.pop()
    # 1. 复原棋盘：撤销 gs.history 中比 prev.history 多出的落子
    extra_moves = gs.history[len(prev.history):]
    for x, y, role in reversed(extra_moves):
        dll.UndoMove(env, x, y, role)
    # 2. 若换手状态不同，复原 DLL 侧 of human_is_black
    if gs.human_is_black != prev.human_is_black:
        dll.SwapHand(env, prev.human_is_black)
    # 3. 原地恢复所有字段
    gs.phase          = prev.phase
    gs.history        = prev.history
    gs.current_role   = prev.current_role
    gs.human_is_black = prev.human_is_black
    gs.winner         = prev.winner
    gs.five_candidates = prev.five_candidates
    gs.game_id        = prev.game_id
    gs.three_asked    = prev.three_asked
    
    # 恢复双 AI 新增字段
    gs.game_mode      = prev.game_mode
    gs.ai_black_cfg   = prev.ai_black_cfg
    gs.ai_white_cfg   = prev.ai_white_cfg
    gs.ai_delay_ms    = prev.ai_delay_ms
    gs.is_paused      = prev.is_paused
    return True

# 统一的日志持久化系统
logger = logging.getLogger("GomokuRuntime")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    # 覆盖写入日志文件 logs/runtime.log
    fh = logging.FileHandler(os.path.join(LOG_DIR, "runtime.log"), mode='w', encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

def print(*args, **kwargs):
    sep = kwargs.get('sep', ' ')
    msg = sep.join(str(arg) for arg in args)
    logger.info(msg)
    builtins.print(*args, **kwargs)

DLL_PATH = os.path.join(PROJECT_ROOT, "engine", "GameEngine.so" if sys.platform != "win32" else "GameEngine.dll")
MODEL_WEIGHTS_PATH = os.path.join(BASE_DIR, "model_weights.txt")
KATA_MODEL_PATH = os.path.join(PROJECT_ROOT, "KataGomo", "models", "model.bin.gz")
KATA_CONFIG_PATH = os.path.join(PROJECT_ROOT, "KataGomo", "scripts", "gomocup", "default_gtp.cfg")
TRAIN_CFG_PATH = os.path.join(PROJECT_ROOT, "KataGomo", "scripts", "selfplay.cfg")
TRAIN_LOG_PATH = os.path.join(LOG_DIR, "kata_training_ui.log")
SEARCH_LOG_PATH = os.path.join(LOG_DIR, "search_logs.jsonl")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(PROJECT_ROOT)
dll = ctypes.CDLL(DLL_PATH)

class GameEngine(ctypes.Structure): pass
class AIMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("score", ctypes.c_int)]

# 原型定义
dll.GetGameEngine.restype = ctypes.POINTER(GameEngine)
load_model_weights = getattr(dll, "LoadModelWeights", None)
if load_model_weights is not None:
    load_model_weights.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_char_p]
    load_model_weights.restype = ctypes.c_bool
load_kata_model = getattr(dll, "LoadKataModel", None)
set_kata_enabled = getattr(dll, "SetKataEnabled", None)
set_kata_search_params = getattr(dll, "SetKataSearchParams", None)
is_kata_ready = getattr(dll, "IsKataReady", None)
get_last_search_log_json = getattr(dll, "GetLastSearchLogJson", None)
if load_kata_model is not None:
    load_kata_model.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_char_p, ctypes.c_char_p]
    load_kata_model.restype = ctypes.c_bool
if set_kata_enabled is not None:
    set_kata_enabled.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_bool]
if set_kata_search_params is not None:
    set_kata_search_params.argtypes = [
        ctypes.POINTER(GameEngine),
        ctypes.c_int,
        ctypes.c_double,
        ctypes.c_double,
        ctypes.c_double,
    ]
if is_kata_ready is not None:
    is_kata_ready.argtypes = [ctypes.POINTER(GameEngine)]
    is_kata_ready.restype = ctypes.c_bool
if get_last_search_log_json is not None:
    get_last_search_log_json.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_char_p, ctypes.c_int]
    get_last_search_log_json.restype = ctypes.c_int
dll.CheckWin.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.CheckWin.restype = ctypes.c_bool
dll.SwapHand.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_bool]
dll.DoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.DoMove.restype = ctypes.c_bool
dll.UndoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.UndoMove.restype = ctypes.c_bool
dll.GetTopMoves.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.POINTER(AIMove), ctypes.c_int]
dll.GetTopMoves.restype = ctypes.c_int
dll.GetBoardState.argtypes = [ctypes.POINTER(GameEngine), ctypes.POINTER(ctypes.c_int), ctypes.c_bool]
dll.ReleaseEngine.argtypes = [ctypes.POINTER(GameEngine)]

# -------------------------------------------------------------------
# 常量 & 初始化
# -------------------------------------------------------------------
BOARD_SIZE = 15
CELL = 40
MARGIN = 50
STATUS_H = 80
BOARD_PIXEL = CELL * (BOARD_SIZE - 1)
BOARD_PAD = 34
BOARD_AREA_W = MARGIN + CELL * BOARD_SIZE + 20
SIDEBAR_W = 470
WIDTH = BOARD_AREA_W + SIDEBAR_W
HEIGHT = MARGIN + CELL * BOARD_SIZE + STATUS_H + 20
BLACK, WHITE = 0, 1
FIVE_MOVE_CANDIDATE_COUNT = 3
WOOD_BG = (211, 159, 89)
WOOD_LIGHT = (229, 183, 113)
WOOD_DARK = (115, 71, 34)
GRID_COLOR = (58, 36, 18)
STAR_POINTS = (3, 7, 11)

pygame.init(); pygame.font.init()
font = pygame.font.Font(os.path.join(BASE_DIR, 'assets', 'LXGWZhenKaiGB-Regular.ttf'), 24)
small_font = pygame.font.Font(os.path.join(BASE_DIR, 'assets', 'LXGWZhenKaiGB-Regular.ttf'), 18)
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('五子棋')

def _draw_loading_screen(step_text):
    """渲染启动加载进度画面，防止窗口假死黑屏。"""
    screen.fill(WOOD_BG)
    # 标题
    title_surf = font.render("五子棋 AI 对弈系统", True, WOOD_DARK)
    screen.blit(title_surf, ((WIDTH - title_surf.get_width()) // 2, HEIGHT // 2 - 80))
    # 分隔线
    pygame.draw.line(screen, WOOD_DARK,
                     (WIDTH // 2 - 200, HEIGHT // 2 - 45),
                     (WIDTH // 2 + 200, HEIGHT // 2 - 45), 2)
    # 步骤文字
    step_surf = small_font.render(step_text, True, WOOD_DARK)
    screen.blit(step_surf, ((WIDTH - step_surf.get_width()) // 2, HEIGHT // 2 - 20))
    # 提示
    hint_surf = small_font.render("首次加载较慢，请稍候...", True, (130, 90, 40))
    screen.blit(hint_surf, ((WIDTH - hint_surf.get_width()) // 2, HEIGHT // 2 + 20))
    pygame.display.flip()

# 引擎 & 缓存
env = dll.GetGameEngine()
model_loaded = False
if load_model_weights is None:
    print("[模型权重] 当前 DLL 未导出 LoadModelWeights，重新编译后可启用模型评估")
elif os.path.exists(MODEL_WEIGHTS_PATH):
    _draw_loading_screen("正在载入轻量评估权重...")
    model_loaded = load_model_weights(env, MODEL_WEIGHTS_PATH.encode("utf-8"))
    print(f"[模型权重] {'已加载' if model_loaded else '加载失败'}: {MODEL_WEIGHTS_PATH}")
else:
    print(f"[模型权重] 未找到，使用规则评估: {MODEL_WEIGHTS_PATH}")
kata_loaded = False
if load_kata_model is not None and os.path.exists(KATA_MODEL_PATH) and os.path.exists(KATA_CONFIG_PATH):
    _draw_loading_screen("正在载入 KataGomo 深度神经网络模型（CUDA 加速）...")
    kata_loaded = load_kata_model(env, KATA_MODEL_PATH.encode("utf-8"), KATA_CONFIG_PATH.encode("utf-8"))
    if set_kata_search_params is not None:
        set_kata_search_params(env, 64, 0.0, 0.25, 0.35)
    print(f"[KataGomo] {'已启用' if kata_loaded else '未启用'}: {KATA_MODEL_PATH}")
else:
    print("[KataGomo] 未找到模型或 DLL 未导出 Kata 接口，使用原 AlphaBeta")

board_buf = (ctypes.c_int * (BOARD_SIZE * BOARD_SIZE))()
history = []
current_role = BLACK
human_is_black = True
ai_first_done = False

asked_open = False
asked_three = False  # 三手交换标志
five_asked = False   # 五手N打标志
virtual_candidates = []
winner = None
ai_is_searching = False
last_ai_move_ticks = 0
white_worker_process = None
search_log_panel_open = True
search_log_all_calls = False
search_log_entries = []
opening_style = "hybrid"
book = OpeningBook(os.path.join(BASE_DIR, "data", "opening_book.json"))
current_framework_stage = "Book"
selected_search_log_index = None
last_ai_move_analysis = None
last_search_log = None
five_move_candidate_count = FIVE_MOVE_CANDIDATE_COUNT
training_process = None
training_log_lines = []
training_fields = {
    "model": "b10c256nbt",
    "batch": "128",
    "gpu": "0",
    "selfplay_games": "1000",
    "samples": "100000",
    "board_sizes": "15",
    "visits": "100",
}
training_field_order = list(training_fields.keys())
training_active_field = 0
training_ui_process = None


# 五手N打虚拟棋盘状态（供旧版 draw() 兼容使用，新版从 gs.five_candidates 读取）
virtual_candidates = []  # 虚拟候选位置

# -------------------------------------------------------------------
# 统一结构化日志器（Task 1.5）
# -------------------------------------------------------------------
game_logger = GameLogger(LOG_DIR)

# -------------------------------------------------------------------
# 辅助函数与核心解耦算法
# -------------------------------------------------------------------
from game.game_logic import (
    is_symmetric,
    is_symmetric_to_any,
    get_distance,
    rank_move_score_from_arr,
    choose_low_impact_candidates_for_black
)

def is_role_human(role):
    if 'gs' in globals() and (gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1):
        return False
    return (role == BLACK and human_is_black) or (role == WHITE and not human_is_black)

def is_role_ai(role):
    return not is_role_human(role)

def clamp_five_move_count():
    return max(2, min(5, int(five_move_candidate_count)))


def select_best_candidate_for_white(candidates):
    if not candidates:
        return None, 0
    scores = []
    for cx, cy in candidates:
        white_value = evaluate_virtual_move_for_white(cx, cy)
        scores.append(((cx, cy), white_value))
        print(f"[五手N打] 位置 {(cx, cy)} 对白方价值：{white_value}")
    return max(scores, key=lambda x: x[1])

def evaluate_virtual_move_for_white(x, y):
    """虚拟评估某步棋对白方的价值（不影响真实棋盘状态）"""
    # 临时下一个黑子
    if dll.DoMove(env, x, y, BLACK):
        # 获取白方的最佳应对
        arr = (AIMove * 5)()
        cnt = dll.GetTopMoves(env, WHITE, arr, 5)
        capture_search_log("debug_recommendation")
        white_best_score = arr[0].score if cnt > 0 else 0
        
        # 立即撤销临时棋子
        dll.UndoMove(env, x, y, BLACK)
        
        # 返回白方的得分（越高对白方越有利）
        return white_best_score
    return -9999

def get_stage_display_name(stage):
    mapping = {
        "Book": "开局库 (Book)",
        "MCTS": "MCTS (神经网络)",
        "MiniMax": "MiniMax (AB 搜索)",
        "VCF": "VCF 绝对算杀"
    }
    return mapping.get(stage, stage)

def get_board_lines():
    dll.GetBoardState(env, board_buf, human_is_black)
    grid = []
    for x in range(BOARD_SIZE):
        row = []
        for y in range(BOARD_SIZE):
            v = board_buf[x * BOARD_SIZE + y]
            if v == BLACK:
                row.append('1')
            elif v == WHITE:
                row.append('2')
            else:
                row.append('0')
        grid.append(row)
        
    lines = []
    # Horizontal
    for r in grid:
        lines.append("".join(r))
    # Vertical
    for c in range(BOARD_SIZE):
        lines.append("".join(grid[r][c] for r in range(BOARD_SIZE)))
    # Diagonals (top-left to bottom-right)
    for d in range(-10, 11):
        diag = []
        for r in range(BOARD_SIZE):
            c = r + d
            if 0 <= c < BOARD_SIZE:
                diag.append(grid[r][c])
        if len(diag) >= 5:
            lines.append("".join(diag))
    # Anti-diagonals (top-right to bottom-left)
    for d in range(4, 25):
        diag = []
        for r in range(BOARD_SIZE):
            c = d - r
            if 0 <= c < BOARD_SIZE:
                diag.append(grid[r][c])
        if len(diag) >= 5:
            lines.append("".join(diag))
    return lines

def check_threes_and_fours():
    lines = get_board_lines()
    threes_b, fours_b = 0, 0
    threes_w, fours_w = 0, 0
    
    # Active patterns for Black ('1') and White ('2')
    for line in lines:
        # Black
        if '01110' in line or '010110' in line or '011010' in line:
            threes_b += 1
        if '011110' in line or '11110' in line or '01111' in line or '10111' in line or '11011' in line or '11101' in line:
            fours_b += 1
        # White
        if '02220' in line or '020220' in line or '022020' in line:
            threes_w += 1
        if '022220' in line or '22220' in line or '02222' in line or '20222' in line or '22022' in line or '22202' in line:
            fours_w += 1
            
    return threes_b, fours_b, threes_w, fours_w

def has_active_three_or_four():
    tb, fb, tw, fw = check_threes_and_fours()
    return (tb + fb + tw + fw) > 0

def decide_search_framework(gs: GameState):
    global current_framework_stage
    turn = len(gs.history)
    
    # 1. Stage 3 (MiniMax AB Search): Turn >= 13 or active tactical threat
    if turn >= 13 or has_active_three_or_four():
        current_framework_stage = "MiniMax"
        return "MiniMax"
        
    # 2. Stage 1 (Opening Book): Turn <= 5 and hit exists
    if turn <= 5:
        if book.query([(h[0], h[1]) for h in gs.history], style=opening_style) is not None:
            current_framework_stage = "Book"
            return "Book"
            
    # 3. Stage 2 (KataGomo MCTS): Turn 6-12 (or fallback from Book)
    current_framework_stage = "MCTS"
    return "MCTS" 

def append_training_log(line):
    training_log_lines.append(line.rstrip())
    del training_log_lines[:-12]

def write_training_params():
    lines = []
    if os.path.exists(TRAIN_CFG_PATH):
        with open(TRAIN_CFG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    replacements = {
        "bSizes": training_fields["board_sizes"],
        "maxVisits": training_fields["visits"],
        "gpuToUseThread0": training_fields["gpu"],
    }
    output = []
    seen = set()
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in replacements:
            output.append(f"{key} = {replacements[key]}\n")
            seen.add(key)
        else:
            output.append(line)
    for key, value in replacements.items():
        if key not in seen:
            output.append(f"{key} = {value}\n")
    os.makedirs(os.path.dirname(TRAIN_CFG_PATH), exist_ok=True)
    with open(TRAIN_CFG_PATH, "w", encoding="utf-8") as f:
        f.writelines(output)
    append_training_log(f"Saved training cfg: {TRAIN_CFG_PATH}")

def _pump_training_output(proc):
    with open(TRAIN_LOG_PATH, "a", encoding="utf-8", errors="ignore") as log:
        while proc.poll() is None:
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                append_training_log(line)
                log.write(line)
            else:
                time.sleep(0.1)
        append_training_log(f"Process exited: {proc.returncode}")

def start_training_task(kind):
    global training_process
    if training_process is not None and training_process.poll() is None:
        append_training_log("Training task is already running")
        return
    write_training_params()
    kata_root = os.path.join(PROJECT_ROOT, "KataGomo")
    if kind == "selfplay":
        script = "./scripts/run.sh"
        args = []
    elif kind == "train":
        script = "./python/train.sh"
        args = [
            "./data",
            training_fields["model"],
            training_fields["model"],
            training_fields["batch"],
            "main",
        ]
    else:
        script = "./python/export.sh"
        args = [
            training_fields["model"],
            "./data",
            "0",
        ]
    script_path = os.path.join(kata_root, script.replace("/", os.sep).lstrip(".").lstrip(os.sep))
    if not os.path.exists(script_path):
        append_training_log(f"Missing script: {script_path}")
        return
    cmd, proc_cwd = build_bash_command(script, args, kata_root)
    try:
        training_process = subprocess.Popen(
            cmd,
            cwd=proc_cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        append_training_log("Started: " + " ".join(cmd))
        threading.Thread(target=_pump_training_output, args=(training_process,), daemon=True).start()
    except Exception as exc:
        append_training_log(f"Failed to start {kind}: {exc}")

def stop_training_task():
    global training_process
    if training_process is not None and training_process.poll() is None:
        training_process.terminate()
        append_training_log("Stop requested")
    else:
        append_training_log("No running training task")

def open_training_backend_ui():
    global training_ui_process
    if training_ui_process is not None and training_ui_process.poll() is None:
        append_training_log("Training backend UI is already running")
        return
    script = os.path.join(PROJECT_ROOT, "ml", "training_ui.py")
    try:
        training_ui_process = subprocess.Popen([sys.executable, script], cwd=BASE_DIR)
        append_training_log("Started standalone training UI")
    except Exception as exc:
        append_training_log(f"Failed to start training UI: {exc}")

def windows_path_to_wsl(path):
    drive, tail = os.path.splitdrive(os.path.abspath(path))
    if not drive:
        return path.replace("\\", "/")
    drive_letter = drive[0].lower()
    return f"/mnt/{drive_letter}" + tail.replace("\\", "/")

def shell_quote(value):
    return "'" + str(value).replace("'", "'\"'\"'") + "'"

def build_bash_command(script, args, cwd):
    bash_source = ""
    try:
        bash_source = subprocess.check_output(["where", "bash"], text=True, stderr=subprocess.DEVNULL).splitlines()[0].lower()
    except Exception:
        pass

    if "windows\\system32\\bash.exe" in bash_source or "system32\\bash.exe" in bash_source:
        wsl_cwd = windows_path_to_wsl(cwd)
        command = "cd " + shell_quote(wsl_cwd) + " && bash " + shell_quote(script)
        for arg in args:
            command += " " + shell_quote(arg)
        return ["bash", "-lc", command], None

    return ["bash", script] + args, cwd

def capture_search_log(context, force=False, chosen_move=None):
    global last_search_log, selected_search_log_index, last_ai_move_analysis
    if get_last_search_log_json is None:
        return None
    if not force and not search_log_all_calls:
        return None
    required = get_last_search_log_json(env, None, 0)
    if required <= 1:
        return None
    buf = ctypes.create_string_buffer(required)
    get_last_search_log_json(env, buf, required)
    try:
        entry = json.loads(buf.value.decode("utf-8"))
    except Exception as exc:
        entry = {"context": context, "parseError": str(exc), "raw": buf.value.decode("utf-8", errors="replace")}
    entry["context"] = context
    entry["historyLen"] = len(history)
    entry["history"] = [(int(h[0]), int(h[1])) for h in history]
    if chosen_move is not None:
        entry["chosenMove"] = {
            "x": int(chosen_move.x),
            "y": int(chosen_move.y),
            "score": int(chosen_move.score),
        }
    last_search_log = entry
    search_log_entries.append(entry)
    del search_log_entries[:-30]
    selected_search_log_index = len(search_log_entries) - 1
    if context == "ai_move":
        last_ai_move_analysis = entry
    try:
        with open(SEARCH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as exc:
        print(f"[SearchLog] failed to write: {exc}")
    return entry

def fmt_bool(value):
    return "Y" if value else "N"

def active_search_log():
    if search_log_entries:
        idx = selected_search_log_index
        if idx is None or idx < 0 or idx >= len(search_log_entries):
            return search_log_entries[-1]
        return search_log_entries[idx]
    return last_search_log

def draw_analysis_line(text, x, y, color=(30, 30, 30), max_chars=52):
    screen.blit(small_font.render(str(text)[:max_chars], True, color), (x, y))

def draw_panel_button(label, rect, color=(80, 120, 180)):
    pygame.draw.rect(screen, color, rect, border_radius=4)
    text = small_font.render(label, True, (255, 255, 255))
    screen.blit(text, (rect.x + max(6, (rect.width - text.get_width()) // 2), rect.y + 6))

def draw_collapsed_analysis_panel():
    strip = pygame.Rect(BOARD_AREA_W, 0, SIDEBAR_W, HEIGHT)
    pygame.draw.rect(screen, (238, 241, 244), strip)
    pygame.draw.line(screen, (80, 80, 80), (strip.x, 0), (strip.x, HEIGHT), 2)
    show_rect = pygame.Rect(strip.x + 18, 16, 120, 34)
    draw_panel_button("AI Panel", show_rect, (80, 150, 110))
    draw_analysis_line("Analysis panel hidden.", strip.x + 18, 62, (70, 70, 70))
    return {"show": show_rect, "history": []}

def draw_selfplay_console(panel, buttons):
    # 对决控制中心标题
    x = panel.x + 16
    y = 14
    screen.blit(font.render("对决控制中心", True, (20, 20, 20)), (x, y))
    
    # 播放控制键
    play_label = "继续对决" if gs.is_paused else "暂停对决"
    play_color = (40, 150, 110) if gs.is_paused else (180, 50, 50)
    play_rect = pygame.Rect(panel.x + 16, y + 36, 120, 32)
    draw_panel_button(play_label, play_rect, play_color)
    buttons["play_pause"] = play_rect
    
    reset_rect = pygame.Rect(panel.x + 148, y + 36, 90, 32)
    draw_panel_button("重置局势", reset_rect, (100, 100, 100))
    buttons["reset"] = reset_rect
    
    # 延迟控制按钮
    delay_label = f"延迟: {gs.ai_delay_ms}ms"
    dec_delay_rect = pygame.Rect(panel.x + 252, y + 36, 28, 32)
    inc_delay_rect = pygame.Rect(panel.x + 400, y + 36, 28, 32)
    draw_panel_button("-", dec_delay_rect, (120, 120, 120))
    draw_panel_button("+", inc_delay_rect, (120, 120, 120))
    buttons["delay_dec"] = dec_delay_rect
    buttons["delay_inc"] = inc_delay_rect
    
    delay_val_rect = pygame.Rect(panel.x + 284, y + 36, 112, 32)
    pygame.draw.rect(screen, (255, 255, 255), delay_val_rect, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), delay_val_rect, 1, border_radius=4)
    txt_delay = small_font.render(delay_label, True, (20, 20, 20))
    screen.blit(txt_delay, (delay_val_rect.x + (delay_val_rect.width - txt_delay.get_width()) // 2, delay_val_rect.y + 6))
    
    # ------------------ 黑方 AI 配置卡片 ------------------
    b_card = pygame.Rect(panel.x + 16, 96, 438, 192)
    # 正在思考时绘制发光红边框，否则常规边框
    is_black_thinking = (gs.current_role == BLACK and not gs.is_paused and gs.winner is None)
    card_border_color = (220, 50, 50) if is_black_thinking else (200, 200, 200)
    pygame.draw.rect(screen, (255, 255, 255), b_card, border_radius=6)
    pygame.draw.rect(screen, card_border_color, b_card, 2 if is_black_thinking else 1, border_radius=6)
    
    # 标题与指示灯
    screen.blit(small_font.render("🔴 黑色 AI (Black)", True, (20, 20, 20)), (b_card.x + 16, b_card.y + 12))
    if is_black_thinking:
        lbl_glow = small_font.render("● 正在决策中...", True, (220, 50, 50))
        screen.blit(lbl_glow, (b_card.x + 280, b_card.y + 12))
        
    # 决策引擎
    screen.blit(small_font.render("决策引擎:", True, (70, 70, 70)), (b_card.x + 16, b_card.y + 48))
    b_engine = gs.ai_black_cfg.get("engine", "MCTS")
    bmcts_rect = pygame.Rect(b_card.x + 96, b_card.y + 44, 88, 26)
    bminimax_rect = pygame.Rect(b_card.x + 192, b_card.y + 44, 88, 26)
    draw_panel_button("神经网络", bmcts_rect, (40, 150, 110) if b_engine == "MCTS" else (160, 160, 160))
    draw_panel_button("传统AB", bminimax_rect, (40, 150, 110) if b_engine == "MiniMax" else (160, 160, 160))
    buttons["b_mcts"] = bmcts_rect
    buttons["b_minimax"] = bminimax_rect
    
    # Visits
    screen.blit(small_font.render("模拟次数(Visits):", True, (70, 70, 70)), (b_card.x + 16, b_card.y + 92))
    b_visits = gs.ai_black_cfg.get("visits", 128)
    b_visits_dec_rect = pygame.Rect(b_card.x + 192, b_card.y + 88, 28, 26)
    b_visits_val_rect = pygame.Rect(b_card.x + 224, b_card.y + 88, 64, 26)
    b_visits_inc_rect = pygame.Rect(b_card.x + 292, b_card.y + 88, 28, 26)
    draw_panel_button("-", b_visits_dec_rect, (120, 120, 120))
    draw_panel_button("+", b_visits_inc_rect, (120, 120, 120))
    pygame.draw.rect(screen, (255, 255, 255), b_visits_val_rect, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), b_visits_val_rect, 1, border_radius=4)
    txt_v = small_font.render(str(b_visits), True, (20, 20, 20))
    screen.blit(txt_v, (b_visits_val_rect.x + (b_visits_val_rect.width - txt_v.get_width()) // 2, b_visits_val_rect.y + 3))
    buttons["b_visits_dec"] = b_visits_dec_rect
    buttons["b_visits_inc"] = b_visits_inc_rect
    
    # Policy
    screen.blit(small_font.render("直觉权重(Policy):", True, (70, 70, 70)), (b_card.x + 16, b_card.y + 136))
    b_policy = gs.ai_black_cfg.get("policy", 0.6)
    b_policy_dec_rect = pygame.Rect(b_card.x + 192, b_card.y + 132, 28, 26)
    b_policy_val_rect = pygame.Rect(b_card.x + 224, b_card.y + 132, 64, 26)
    b_policy_inc_rect = pygame.Rect(b_card.x + 292, b_card.y + 132, 28, 26)
    draw_panel_button("-", b_policy_dec_rect, (120, 120, 120))
    draw_panel_button("+", b_policy_inc_rect, (120, 120, 120))
    pygame.draw.rect(screen, (255, 255, 255), b_policy_val_rect, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), b_policy_val_rect, 1, border_radius=4)
    txt_p = small_font.render(f"{b_policy:.1f}", True, (20, 20, 20))
    screen.blit(txt_p, (b_policy_val_rect.x + (b_policy_val_rect.width - txt_p.get_width()) // 2, b_policy_val_rect.y + 3))
    buttons["b_policy_dec"] = b_policy_dec_rect
    buttons["b_policy_inc"] = b_policy_inc_rect

    # ------------------ 白方 AI 配置卡片 ------------------
    w_card = pygame.Rect(panel.x + 16, 304, 438, 192)
    is_white_thinking = (gs.current_role == WHITE and not gs.is_paused and gs.winner is None)
    card_border_color_w = (40, 100, 220) if is_white_thinking else (200, 200, 200)
    pygame.draw.rect(screen, (255, 255, 255), w_card, border_radius=6)
    pygame.draw.rect(screen, card_border_color_w, w_card, 2 if is_white_thinking else 1, border_radius=6)
    
    # 标题与指示灯
    screen.blit(small_font.render("⚪ 白色 AI (White)", True, (20, 20, 20)), (w_card.x + 16, w_card.y + 12))
    if is_white_thinking:
        lbl_glow_w = small_font.render("● 正在决策中...", True, (40, 100, 220))
        screen.blit(lbl_glow_w, (w_card.x + 280, w_card.y + 12))
        
    # 决策引擎
    screen.blit(small_font.render("决策引擎:", True, (70, 70, 70)), (w_card.x + 16, w_card.y + 44))
    w_engine = gs.ai_white_cfg.get("engine", "MCTS")
    wmcts_rect = pygame.Rect(w_card.x + 96, w_card.y + 40, 88, 26)
    wminimax_rect = pygame.Rect(w_card.x + 192, w_card.y + 40, 88, 26)
    draw_panel_button("神经网络", wmcts_rect, (40, 150, 110) if w_engine == "MCTS" else (160, 160, 160))
    draw_panel_button("传统AB", wminimax_rect, (40, 150, 110) if w_engine == "MiniMax" else (160, 160, 160))
    buttons["w_mcts"] = wmcts_rect
    buttons["w_minimax"] = wminimax_rect
    
    # Model Path Select Button & Text
    screen.blit(small_font.render("白方模型:", True, (70, 70, 70)), (w_card.x + 16, w_card.y + 76))
    w_model_sel_rect = pygame.Rect(w_card.x + 96, w_card.y + 72, 88, 26)
    w_model_reload_rect = pygame.Rect(w_card.x + 192, w_card.y + 72, 88, 26)
    draw_panel_button("浏览模型", w_model_sel_rect, (80, 120, 180))
    draw_panel_button("热重载", w_model_reload_rect, (180, 120, 40))
    buttons["w_model_select"] = w_model_sel_rect
    buttons["w_model_reload"] = w_model_reload_rect
    
    model_name_display = "默认白方模型"
    if gs.white_model_path:
        model_name_display = os.path.basename(gs.white_model_path)
    screen.blit(small_font.render(model_name_display[:25] + ("..." if len(model_name_display) > 25 else ""), True, (100, 100, 100)), (w_card.x + 290, w_card.y + 76))

    # Visits
    screen.blit(small_font.render("模拟次数(Visits):", True, (70, 70, 70)), (w_card.x + 16, w_card.y + 112))
    w_visits = gs.ai_white_cfg.get("visits", 64)
    w_visits_dec_rect = pygame.Rect(w_card.x + 192, w_card.y + 108, 28, 26)
    w_visits_val_rect = pygame.Rect(w_card.x + 224, w_card.y + 108, 64, 26)
    w_visits_inc_rect = pygame.Rect(w_card.x + 292, w_card.y + 108, 28, 26)
    draw_panel_button("-", w_visits_dec_rect, (120, 120, 120))
    draw_panel_button("+", w_visits_inc_rect, (120, 120, 120))
    pygame.draw.rect(screen, (255, 255, 255), w_visits_val_rect, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), w_visits_val_rect, 1, border_radius=4)
    txt_vw = small_font.render(str(w_visits), True, (20, 20, 20))
    screen.blit(txt_vw, (w_visits_val_rect.x + (w_visits_val_rect.width - txt_vw.get_width()) // 2, w_visits_val_rect.y + 3))
    buttons["w_visits_dec"] = w_visits_dec_rect
    buttons["w_visits_inc"] = w_visits_inc_rect
    
    # Policy
    screen.blit(small_font.render("直觉权重(Policy):", True, (70, 70, 70)), (w_card.x + 16, w_card.y + 148))
    w_policy = gs.ai_white_cfg.get("policy", 0.3)
    w_policy_dec_rect = pygame.Rect(w_card.x + 192, w_card.y + 144, 28, 26)
    w_policy_val_rect = pygame.Rect(w_card.x + 224, w_card.y + 144, 64, 26)
    w_policy_inc_rect = pygame.Rect(w_card.x + 292, w_card.y + 144, 28, 26)
    draw_panel_button("-", w_policy_dec_rect, (120, 120, 120))
    draw_panel_button("+", w_policy_inc_rect, (120, 120, 120))
    pygame.draw.rect(screen, (255, 255, 255), w_policy_val_rect, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), w_policy_val_rect, 1, border_radius=4)
    txt_pw = small_font.render(f"{w_policy:.1f}", True, (20, 20, 20))
    screen.blit(txt_pw, (w_policy_val_rect.x + (w_policy_val_rect.width - txt_pw.get_width()) // 2, w_policy_val_rect.y + 3))
    buttons["w_policy_dec"] = w_policy_dec_rect
    buttons["w_policy_inc"] = w_policy_inc_rect


    # ------------------ 实时搜索日志卡片 ------------------
    screen.blit(small_font.render("📊 实时搜索日志 (Real-time logs)", True, (20, 20, 20)), (panel.x + 16, 510))
    log_card = pygame.Rect(panel.x + 16, 532, 438, 178)
    pygame.draw.rect(screen, (248, 249, 250), log_card, border_radius=6)
    pygame.draw.rect(screen, (180, 180, 180), log_card, 1, border_radius=6)
    
    entry = active_search_log()
    if entry is None:
        draw_analysis_line("等待首步落子中...", log_card.x + 16, log_card.y + 16, (120, 120, 120))
    else:
        role_label = "🔴 黑方 AI" if entry.get("role") == "black" else "⚪ 白方 AI"
        engine_lbl = entry.get("kataStatus") or "MCTS 搜子"
        if "Book" in engine_lbl:
            engine_lbl = "开局库 (Book) 秒命中"
            
        chosen = entry.get("chosenMove") or {}
        chosen_text = f"推荐着法: ({chosen.get('x','?')},{chosen.get('y','?')})  评分: {chosen.get('score','?')}"
        stats_text = f"耗时: {entry.get('totalMs', 0):.0f}ms  深度: {entry.get('reachedDepth')}/{entry.get('targetDepth')}"
        visits_text = f"神经网络: visits={entry.get('kataVisits', 0)}  policy={entry.get('policyBlend', 0.0):.1f}"
        
        ly_offset = log_card.y + 12
        draw_analysis_line(f"ID #{entry.get('searchId')}  回合: {entry.get('turn')}手", log_card.x + 16, ly_offset, (20, 20, 20))
        ly_offset += 24
        draw_analysis_line(f"角色: {role_label}  |  方式: {engine_lbl}", log_card.x + 16, ly_offset, (50, 50, 50))
        ly_offset += 24
        draw_analysis_line(chosen_text, log_card.x + 16, ly_offset, (40, 120, 200))
        ly_offset += 24
        draw_analysis_line(stats_text, log_card.x + 16, ly_offset, (80, 80, 80))
        ly_offset += 24
        draw_analysis_line(visits_text, log_card.x + 16, ly_offset, (80, 80, 80))
        
    draw_analysis_line(f"Log: {SEARCH_LOG_PATH}", panel.x + 16, HEIGHT - 28, (120, 120, 120), 40)
    
    return buttons


def draw_search_log_panel():
    panel = pygame.Rect(BOARD_AREA_W, 0, SIDEBAR_W, HEIGHT)
    pygame.draw.rect(screen, (238, 241, 244), panel)
    pygame.draw.line(screen, (80, 80, 80), (panel.x, 0), (panel.x, HEIGHT), 2)
    buttons = {"history": []}
    
    # 3.1 对局处于双 AI 对战或自对弈阶段时，绘制专用的“双 AI 对决控制台”
    if gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1:
        return draw_selfplay_console(panel, buttons)

    x = panel.x + 16
    y = 14
    screen.blit(font.render("AI Analysis", True, (20, 20, 20)), (x, y))
    mode_label = "All calls" if search_log_all_calls else "AI only"
    mode_rect = pygame.Rect(panel.right - 152, y + 2, 84, 30)
    hide_rect = pygame.Rect(panel.right - 62, y + 2, 48, 30)
    draw_panel_button(mode_label, mode_rect, (80, 120, 180))
    draw_panel_button("Hide", hide_rect, (100, 100, 100))
    buttons["mode"] = mode_rect
    buttons["hide"] = hide_rect

    five_y = y + 38
    draw_analysis_line("五手N", x, five_y + 6, (45, 45, 45), 14)
    dec_rect = pygame.Rect(panel.right - 152, five_y, 32, 28)
    count_rect = pygame.Rect(panel.right - 114, five_y, 38, 28)
    inc_rect = pygame.Rect(panel.right - 70, five_y, 32, 28)
    draw_panel_button("-", dec_rect, (120, 120, 120))
    pygame.draw.rect(screen, (255, 255, 255), count_rect, border_radius=5)
    pygame.draw.rect(screen, (150, 150, 150), count_rect, 1, border_radius=5)
    screen.blit(small_font.render(str(clamp_five_move_count()), True, (20, 20, 20)), (count_rect.x + 13, count_rect.y + 5))
    draw_panel_button("+", inc_rect, (120, 120, 120))
    buttons["five_dec"] = dec_rect
    buttons["five_inc"] = inc_rect
    
    # 开局风格选择按钮组
    style_y = five_y + 36
    draw_analysis_line("开局风格", x, style_y + 6, (45, 45, 45), 14)
    trad_rect = pygame.Rect(panel.right - 302, style_y, 88, 28)
    nov_rect = pygame.Rect(panel.right - 204, style_y, 88, 28)
    hyb_rect = pygame.Rect(panel.right - 106, style_y, 88, 28)
    
    draw_panel_button("传统稳健", trad_rect, (40, 150, 110) if opening_style == "traditional" else (160, 160, 160))
    draw_panel_button("创新奇招", nov_rect, (40, 150, 110) if opening_style == "novelty" else (160, 160, 160))
    draw_panel_button("随机混合", hyb_rect, (40, 150, 110) if opening_style == "hybrid" else (160, 160, 160))
    
    buttons["style_trad"] = trad_rect
    buttons["style_nov"] = nov_rect
    buttons["style_hyb"] = hyb_rect
    
    y += 124

    entry = active_search_log()
    if entry is None:
        draw_analysis_line("No AI search yet.", x, y)
        draw_analysis_line(f"Log: {SEARCH_LOG_PATH}", x, HEIGHT - 28, (80, 80, 80), 56)
        return buttons

    chosen = entry.get("chosenMove") or {}
    moves = entry.get("moves", [])
    if not chosen and moves:
        chosen = {"x": moves[0].get("x"), "y": moves[0].get("y"), "score": moves[0].get("finalScore")}
    role = entry.get("role", "?")
    chosen_text = f"Move: ({chosen.get('x','?')},{chosen.get('y','?')}) score={chosen.get('score','?')}"
    
    # 局势雷达扫描
    tb, fb, tw, fw = check_threes_and_fours()
    radar_text = f"雷达(黑): 活三={tb} 冲四={fb} | (白): 活三={tw} 冲四={fw}"
    
    draw_analysis_line(f"#{entry.get('searchId')} {entry.get('context')} role={role}", x, y, (0, 0, 0))
    y += 22
    draw_analysis_line(f"当前阶段: {get_stage_display_name(current_framework_stage)}", x, y, (180, 50, 50))
    y += 22
    draw_analysis_line(radar_text, x, y, (70, 70, 70))
    y += 22

    # 决策图景动态渲染路由
    if current_framework_stage == "Book":
        draw_analysis_line("开局检索: 开局库 (Book) 命中", x, y, (0, 150, 80))
        y += 22
        draw_analysis_line(f"开局风格: {opening_style}", x, y)
        y += 22
        draw_analysis_line("对称还原: Symmetry Helper 激活", x, y)
        y += 22
        draw_analysis_line(chosen_text, x, y)
        y += 22
        draw_analysis_line("神经网络 (KataGomo): 未激活 (开局省电)", x, y, (120, 120, 120))
        y += 22
        draw_analysis_line("AB算杀 (MiniMax): 未激活 (开局省电)", x, y, (120, 120, 120))
        y += 22
    elif current_framework_stage == "MCTS":
        draw_analysis_line(chosen_text, x, y)
        y += 22
        draw_analysis_line(
            f"turn={entry.get('turn')} time={entry.get('totalMs', 0):.0f}ms depth={entry.get('reachedDepth')}/{entry.get('targetDepth')}",
            x,
            y,
        )
        y += 22
        draw_analysis_line(
            f"神经网络: KataGomo MCTS 战略搜子",
            x,
            y,
            (40, 100, 180)
        )
        y += 22
        draw_analysis_line(
            f"Kata: enabled={fmt_bool(entry.get('kataEnabled'))} ready={fmt_bool(entry.get('kataReady'))} applied={fmt_bool(entry.get('kataApplied'))}",
            x,
            y,
        )
        y += 22
        draw_analysis_line(
            f"visits={entry.get('kataVisits')} policy={entry.get('policyBlend')} value={entry.get('valueBlend')}",
            x,
            y,
        )
        y += 22
        draw_analysis_line(entry.get("kataStatus", "Status: 正在预测最佳棋路"), x, y, (70, 70, 70), 44)
        y += 22
    else:  # MiniMax or VCF
        draw_analysis_line(chosen_text, x, y)
        y += 22
        draw_analysis_line(
            f"turn={entry.get('turn')} time={entry.get('totalMs', 0):.0f}ms depth={entry.get('reachedDepth')}/{entry.get('targetDepth')}",
            x,
            y,
        )
        y += 22
        draw_analysis_line(
            f"ab={entry.get('alphaBetaMs', 0):.0f}ms nodes={entry.get('searchNodes')}",
            x,
            y,
        )
        y += 22
        draw_analysis_line(
            f"hash={entry.get('hashHitRate', 0):.1f}% betaCuts={entry.get('betaCuts')}",
            x,
            y,
        )
        y += 22
        draw_analysis_line("Kata: enabled=False ready=True applied=False", x, y, (120, 120, 120))
        y += 22
        draw_analysis_line("visits=0 (强制关停神经网络以聚焦AB算杀)", x, y, (120, 120, 120))
        y += 22

    y += 6

    pygame.draw.line(screen, (190, 190, 190), (x, y), (panel.right - 14, y), 1)
    y += 10
    draw_analysis_line("Top candidates", x, y, (0, 0, 0))
    y += 22
    headers = ["#", "pos", "final", "ab", "policy", "value", "N"]
    col_x = [x, x + 28, x + 76, x + 142, x + 208, x + 282, x + 360]
    for cx, header in zip(col_x, headers):
        screen.blit(small_font.render(header, True, (0, 0, 0)), (cx, y))
    y += 22
    for move in moves[:6]:
        color = (20, 20, 20) if move.get("rank") == 1 else (45, 45, 45)
        row = [
            str(move.get("rank", "")),
            f"{move.get('x')},{move.get('y')}",
            str(move.get("finalScore", 0)),
            str(move.get("alphaBetaScore", 0)),
            f"{move.get('kataPolicy', 0):.2f}",
            f"{move.get('kataValue', 0):.2f}",
            str(move.get("neighborCnt", 0)),
        ]
        for cx, value in zip(col_x, row):
            screen.blit(small_font.render(value[:8], True, color), (cx, y))
        y += 20

    hist_y = HEIGHT - 168
    pygame.draw.line(screen, (190, 190, 190), (x, hist_y - 8), (panel.right - 14, hist_y - 8), 1)
    draw_analysis_line("Recent searches", x, hist_y, (0, 0, 0))
    hist_y += 22
    start = max(0, len(search_log_entries) - 6)
    for idx in range(len(search_log_entries) - 1, start - 1, -1):
        item = search_log_entries[idx]
        rect = pygame.Rect(x, hist_y, panel.width - 32, 22)
        if idx == selected_search_log_index:
            pygame.draw.rect(screen, (210, 224, 242), rect, border_radius=3)
        label = f"#{item.get('searchId')} {item.get('context')} {item.get('role')} {item.get('totalMs', 0):.0f}ms"
        draw_analysis_line(label, rect.x + 4, rect.y + 2, (20, 20, 20), 40)
        buttons["history"].append((idx, rect))
        hist_y += 24

    draw_analysis_line(f"Log: {SEARCH_LOG_PATH}", x, HEIGHT - 28, (80, 80, 80), 56)
    return buttons

def draw_training_panel():
    panel = pygame.Rect(40, 40, WIDTH - 80, HEIGHT - STATUS_H - 80)
    pygame.draw.rect(screen, (245, 245, 245), panel)
    pygame.draw.rect(screen, (30, 30, 30), panel, 2)
    screen.blit(font.render("KataGomo Training", True, (0, 0, 0)), (panel.x + 16, panel.y + 12))

    field_rects = []
    y = panel.y + 55
    for idx, key in enumerate(training_field_order):
        label = small_font.render(key, True, (0, 0, 0))
        screen.blit(label, (panel.x + 20, y + 8))
        rect = pygame.Rect(panel.x + 170, y, 210, 30)
        pygame.draw.rect(screen, (255, 255, 255), rect)
        pygame.draw.rect(screen, (0, 120, 220) if idx == training_active_field else (80, 80, 80), rect, 2)
        screen.blit(small_font.render(training_fields[key], True, (0, 0, 0)), (rect.x + 6, rect.y + 6))
        field_rects.append((key, rect))
        y += 36

    buttons = {}
    labels = [("selfplay", "Selfplay"), ("train", "Train"), ("export", "Export"), ("stop", "Stop"), ("reload", "Load Model")]
    x = panel.x + 410
    y = panel.y + 60
    for key, label in labels:
        rect = pygame.Rect(x, y, 120, 34)
        pygame.draw.rect(screen, (80, 120, 180), rect)
        screen.blit(small_font.render(label, True, (255, 255, 255)), (rect.x + 8, rect.y + 8))
        buttons[key] = rect
        y += 42

    y = panel.y + panel.height - 150
    screen.blit(small_font.render("Logs", True, (0, 0, 0)), (panel.x + 20, y))
    y += 24
    for line in training_log_lines[-6:]:
        screen.blit(small_font.render(line[:95], True, (30, 30, 30)), (panel.x + 20, y))
        y += 20
    return field_rects, buttons

# -------------------------------------------------------------------
# 坐标映射：origin at top-left x→down, y→right
# -------------------------------------------------------------------
def to_screen(x, y):
    px = MARGIN + y * CELL
    py = MARGIN + x * CELL
    return px, py

def draw_stone(px, py, role):
    radius = CELL // 2 - 3
    pygame.draw.circle(screen, (80, 54, 32), (px + 3, py + 4), radius)
    if role == BLACK:
        pygame.draw.circle(screen, (8, 8, 8), (px, py), radius)
        pygame.draw.circle(screen, (38, 38, 38), (px - 5, py - 6), radius // 2)
        pygame.draw.circle(screen, (76, 76, 76), (px - 7, py - 8), 4)
    else:
        pygame.draw.circle(screen, (238, 235, 226), (px, py), radius)
        pygame.draw.circle(screen, (185, 178, 164), (px, py), radius, 1)
        pygame.draw.circle(screen, (255, 255, 250), (px - 6, py - 7), radius // 2)
        pygame.draw.circle(screen, (255, 255, 255), (px - 8, py - 9), 4)

def draw_realistic_board():
    board_rect = pygame.Rect(
        MARGIN - BOARD_PAD,
        MARGIN - BOARD_PAD,
        BOARD_PIXEL + BOARD_PAD * 2,
        BOARD_PIXEL + BOARD_PAD * 2,
    )
    pygame.draw.rect(screen, WOOD_DARK, board_rect, border_radius=5)
    inner = board_rect.inflate(-8, -8)
    pygame.draw.rect(screen, WOOD_BG, inner, border_radius=4)
    for i in range(0, inner.height, 18):
        tone = WOOD_LIGHT if (i // 18) % 2 == 0 else (203, 148, 78)
        pygame.draw.line(screen, tone, (inner.x + 6, inner.y + i), (inner.right - 8, inner.y + i + 5), 1)

    for i in range(BOARD_SIZE):
        pos = MARGIN + i * CELL
        width = 2 if i in (0, BOARD_SIZE - 1) else 1
        pygame.draw.line(screen, GRID_COLOR, (MARGIN, pos), (MARGIN + BOARD_PIXEL, pos), width)
        pygame.draw.line(screen, GRID_COLOR, (pos, MARGIN), (pos, MARGIN + BOARD_PIXEL), width)

    for sx in STAR_POINTS:
        for sy in STAR_POINTS:
            px, py = to_screen(sx, sy)
            pygame.draw.circle(screen, GRID_COLOR, (px, py), 4)

# -------------------------------------------------------------------
# 绘制棋盘与 UI
# -------------------------------------------------------------------
def draw_blocking_overlay(title, subtitle, color=(80, 120, 180)):
    if 'gs' in globals() and gs.game_mode == 1:
        return
    """在棋盘区绘制半透明锁定遮罩 + 圆角提示卡片。
    
    Args:
        title:    卡片标题（大字，使用 font）
        subtitle: 卡片副标题（小字，使用 small_font）
        color:    卡片边框与标题颜色主题（默认蓝色）
    """
    overlay = pygame.Surface((BOARD_AREA_W, HEIGHT - STATUS_H))
    overlay.set_alpha(120)
    overlay.fill((15, 15, 15))
    screen.blit(overlay, (0, 0))

    box_w, box_h = 360, 100
    box_x = (BOARD_AREA_W - box_w) // 2
    box_y = (HEIGHT - STATUS_H - box_h) // 2
    box_rect = pygame.Rect(box_x, box_y, box_w, box_h)

    pygame.draw.rect(screen, (255, 255, 255), box_rect, border_radius=10)
    pygame.draw.rect(screen, color, box_rect, 3, border_radius=10)

    t_surf = font.render(title, True, color)
    screen.blit(t_surf, (box_x + (box_w - t_surf.get_width()) // 2, box_y + 18))

    s_surf = small_font.render(subtitle, True, (100, 100, 100))
    screen.blit(s_surf, (box_x + (box_w - s_surf.get_width()) // 2, box_y + 58))
def draw(gs: GameState):
    screen.fill((184, 154, 118))
    draw_realistic_board()
    for i in range(BOARD_SIZE):
        txt = font.render(str(i), True, (0,0,0))
        screen.blit(txt, (MARGIN-30, MARGIN + i*CELL - txt.get_height()/2))
        screen.blit(txt, (MARGIN + i*CELL - txt.get_width()/2, MARGIN-30))
    
    dll.GetBoardState(env, board_buf, gs.human_is_black)
    for x in range(BOARD_SIZE):
        for y in range(BOARD_SIZE):
            v = board_buf[x * BOARD_SIZE + y]
            px, py = to_screen(x, y)
            if v == BLACK:
                draw_stone(px, py, BLACK)
            elif v == WHITE:
                draw_stone(px, py, WHITE)
            elif v == 2:
                pygame.draw.circle(screen, (180, 30, 30), (px, py), 6)
                pygame.draw.line(screen, (255, 230, 230), (px - 4, py - 4), (px + 4, py + 4), 1)
                pygame.draw.line(screen, (255, 230, 230), (px + 4, py - 4), (px - 4, py + 4), 1)
    # 高亮最后一个落子点
    if gs.history:
        lx, ly, _ = gs.history[-1]
        px, py = to_screen(lx, ly)
        rect = pygame.Rect(px - CELL//2 + 2, py - CELL//2 + 2, CELL - 4, CELL - 4)
        dash_len = 5
        color = (210, 30, 30)
        # 上边虚线
        for x_off in range(0, rect.width, dash_len*2):
            start = (rect.x + x_off, rect.y)
            end   = (min(rect.x + x_off + dash_len, rect.x + rect.width), rect.y)
            pygame.draw.line(screen, color, start, end, 2)
        # 下边虚线
        for x_off in range(0, rect.width, dash_len*2):
            start = (rect.x + x_off, rect.y + rect.height)
            end   = (min(rect.x + x_off + dash_len, rect.x + rect.width), rect.y + rect.height)
            pygame.draw.line(screen, color, start, end, 2)
        # 左边虚线
        for y_off in range(0, rect.height, dash_len*2):
            start = (rect.x, rect.y + y_off)
            end   = (rect.x, min(rect.y + y_off + dash_len, rect.y + rect.height))
            pygame.draw.line(screen, color, start, end, 2)
        # 右边虚线
        for y_off in range(0, rect.height, dash_len*2):
            start = (rect.x + rect.width, rect.y + y_off)
            end   = (rect.x + rect.width, min(rect.y + y_off + dash_len, rect.y + rect.height))
            pygame.draw.line(screen, color, start, end, 2)

    # 绘制虚拟候选位置（五手N打阶段）
    if gs.five_candidates:
        for cx, cy in gs.five_candidates:
            px, py = to_screen(cx, cy)
            pygame.draw.circle(screen, (128, 128, 128), (px, py), CELL//2-2)  # 半透明显示
            pygame.draw.circle(screen, (255, 255, 0), (px, py), CELL//2-2, 2)  # 黄色边框
    
    analysis = active_search_log() if search_log_panel_open else None
    if analysis is not None:
        for move in analysis.get("moves", [])[:10]:
            mx, my = move.get("x"), move.get("y")
            if mx is None or my is None:
                continue
            px, py = to_screen(mx, my)
            rank = int(move.get("rank", 0) or 0)
            if rank == 1:
                pygame.draw.circle(screen, (0, 180, 80), (px, py), CELL // 2 + 7, 3)
            else:
                pygame.draw.circle(screen, (40, 120, 220), (px, py), 9, 2)
            if 1 <= rank <= 10:
                label = small_font.render(str(rank), True, (0, 0, 0))
                screen.blit(label, (px - label.get_width() // 2, py - label.get_height() // 2))

    if gs.winner is not None:
        msg = f"{ '黑子' if gs.winner==BLACK else '白子' } 胜利！"
        text = font.render(msg, True, (255,0,0))
        screen.blit(text, ((BOARD_AREA_W-text.get_width())//2, HEIGHT-STATUS_H+20))
    else:
        text = font.render(f'当前手数: {len(gs.history)}', True, (0,0,0))
        screen.blit(text, (20, HEIGHT-STATUS_H+20))
        
        # 显示当前轮次信息
        role_text = "黑子" if gs.current_role == BLACK else "白子"
        player_text = "人类" if ((gs.current_role == BLACK and gs.human_is_black) or (gs.current_role == WHITE and not gs.human_is_black)) else "AI"
        stage_text = f" | 决策: {get_stage_display_name(current_framework_stage)}" if player_text == "AI" else ""
        info_text = f'{role_text} ({player_text}) 回合{stage_text}'
        text = small_font.render(info_text, True, (0,0,0))
        screen.blit(text, (20, HEIGHT-STATUS_H+45))
        
        # 五手N打提示
        if len(gs.history) == 4 and gs.current_role == BLACK:
            five_n = clamp_five_move_count()
            if gs.five_candidates:
                tip_text = f"五手N打：选择保留的候选（N={five_n}）"
            elif not gs.human_is_black:
                tip_text = f"五手N打：AI 正在提供 {five_n} 个候选"
            else:
                tip_text = f"五手N打：需要提供 {five_n} 个候选"
            text = small_font.render(tip_text, True, (255,0,0))
            screen.blit(text, (200, HEIGHT-STATUS_H+45))
    
    btn = pygame.Rect(BOARD_AREA_W-100, HEIGHT-STATUS_H+10, 80, 40)
    pygame.draw.rect(screen, (100,100,100), btn)
    screen.blit(font.render('悔棋', True, (255,255,255)), (btn.x+20, btn.y+10))
    if search_log_panel_open:
        sidebar_buttons = draw_search_log_panel()
    else:
        sidebar_buttons = draw_collapsed_analysis_panel()

    # AI 思考期视觉锁定与拦截遮罩
    if ai_is_searching:
        draw_blocking_overlay("AI 正在思考中...", "请勿落子或点击界面", (80, 120, 180))

    return btn, sidebar_buttons

# -------------------------------------------------------------------
# 弹窗
# -------------------------------------------------------------------
def confirm(gs: GameState, prompt):
    if gs.game_mode == 1:
        print(f"[确认自动同意] {prompt}")
        return True
    w,h = 380,150; x=(WIDTH-w)//2; y=(HEIGHT-STATUS_H-h)//2
    r = pygame.Rect(x,y,w,h); dragging=False; off=(0,0)
    while True:
        draw(gs); pygame.draw.rect(screen,(255,255,255),r,border_radius=8); pygame.draw.rect(screen,(0,0,0),r,2,border_radius=8)
        lbl = font.render(prompt,True,(0,0,0))
        screen.blit(lbl, (r.x + (w - lbl.get_width()) // 2, r.y+22))
        yb = pygame.Rect(r.x+60, r.y+80,90,40); nb = pygame.Rect(r.x+230,r.y+80,90,40)
        pygame.draw.rect(screen,(0,150,0),yb,border_radius=4); pygame.draw.rect(screen,(150,0,0),nb,border_radius=4)
        screen.blit(font.render('是',True,(255,255,255)), (yb.x+(yb.width-font.render('是',True,(0,0,0)).get_width())//2,yb.y+8))
        screen.blit(font.render('否',True,(255,255,255)), (nb.x+(nb.width-font.render('否',True,(0,0,0)).get_width())//2,nb.y+8))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==QUIT: pygame.quit(); sys.exit()
            if e.type==MOUSEBUTTONDOWN and e.button==1:
                if r.collidepoint(e.pos): dragging=True; off=(e.pos[0]-r.x,e.pos[1]-r.y)
                if yb.collidepoint(e.pos): return True
                if nb.collidepoint(e.pos): return False
            if e.type==MOUSEBUTTONUP and e.button==1: dragging=False
            if e.type==MOUSEMOTION and dragging: r.x, r.y = e.pos[0]-off[0], e.pos[1]-off[1]

def select_game_mode_dialog(gs: GameState):
    w, h = 420, 180
    x = (WIDTH - w) // 2
    y = (HEIGHT - STATUS_H - h) // 2
    r = pygame.Rect(x, y, w, h)
    dragging = False
    off = (0, 0)
    while True:
        draw(gs)
        pygame.draw.rect(screen, (255, 255, 255), r, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), r, 2, border_radius=8)
        
        # 居中标题
        title = font.render("请选择游戏对弈模式", True, (20, 20, 20))
        screen.blit(title, (r.x + (w - title.get_width()) // 2, r.y + 25))
        
        # 人机对弈按钮
        h_btn = pygame.Rect(r.x + 30, r.y + 90, 160, 48)
        # 双 AI 对决按钮
        ai_btn = pygame.Rect(r.x + 230, r.y + 90, 160, 48)
        
        pygame.draw.rect(screen, (80, 120, 180), h_btn, border_radius=5)
        pygame.draw.rect(screen, (40, 150, 110), ai_btn, border_radius=5)
        
        lbl_h = font.render("人机对弈", True, (255, 255, 255))
        lbl_ai = font.render("双AI自对弈", True, (255, 255, 255))
        
        screen.blit(lbl_h, (h_btn.x + (h_btn.width - lbl_h.get_width()) // 2, h_btn.y + 10))
        screen.blit(lbl_ai, (ai_btn.x + (ai_btn.width - lbl_ai.get_width()) // 2, ai_btn.y + 10))
        
        pygame.display.flip()
        
        for e in pygame.event.get():
            if e.type == QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == MOUSEBUTTONDOWN and e.button == 1:
                if r.collidepoint(e.pos):
                    dragging = True
                    off = (e.pos[0] - r.x, e.pos[1] - r.y)
                if h_btn.collidepoint(e.pos):
                    return 0
                if ai_btn.collidepoint(e.pos):
                    return 1
            elif e.type == MOUSEBUTTONUP and e.button == 1:
                dragging = False
            elif e.type == MOUSEMOTION and dragging:
                r.x, r.y = e.pos[0] - off[0], e.pos[1] - off[1]

def alert(gs: GameState, prompt):
    if gs.game_mode == 1:
        print(f"[提示自动跳过] {prompt}")
        return
    w,h = 380,150; x=(WIDTH-w)//2; y=(HEIGHT-STATUS_H-h)//2
    r = pygame.Rect(x,y,w,h); dragging=False; off=(0,0)
    while True:
        draw(gs); pygame.draw.rect(screen,(255,255,255),r,border_radius=8); pygame.draw.rect(screen,(0,0,0),r,2,border_radius=8)
        # Handle long prompt
        lines = [prompt]
        if len(prompt) > 15:
            lines = [prompt[:15], prompt[15:]]
        for idx, line in enumerate(lines):
            lbl = font.render(line,True,(0,0,0))
            screen.blit(lbl, (r.x + (w - lbl.get_width()) // 2, r.y + 20 + idx*30))
            
        ob = pygame.Rect(r.x + (w-100)//2, r.y+90, 100, 40)
        pygame.draw.rect(screen,(80,120,180),ob,border_radius=4)
        screen.blit(font.render('确定',True,(255,255,255)), (ob.x+(ob.width-font.render('确定',True,(0,0,0)).get_width())//2,ob.y+8))
        pygame.display.flip()
        for e in pygame.event.get():
            if e.type==QUIT: pygame.quit(); sys.exit()
            if e.type==MOUSEBUTTONDOWN and e.button==1:
                if r.collidepoint(e.pos): dragging=True; off=(e.pos[0]-r.x,e.pos[1]-r.y)
                if ob.collidepoint(e.pos): return
            if e.type==MOUSEBUTTONUP and e.button==1: dragging=False
            if e.type==MOUSEMOTION and dragging: r.x, r.y = e.pos[0]-off[0], e.pos[1]-off[1]
def change_phase(gs: GameState, to_phase: GamePhase, data: dict | None = None):
    """Safely transitions gs to a new phase and logs the event."""
    old_phase = gs.phase
    gs.phase = to_phase
    game_logger.phase_transition(old_phase.name, to_phase.name, data)
    print(f"[状态机转换] {old_phase.name} -> {to_phase.name}")

# -------------------------------------------------------------------
# 主循环
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# Phase Handlers & Dispatch Loop
# -------------------------------------------------------------------

def handle_init(gs: GameState):
    """INIT phase - Show swap opening dialog, setup game record."""
    try:
        print("[Debug handle_init] Entering handle_init")
        mode = select_game_mode_dialog(gs)
        if mode == 1:
            gs.game_mode = 1
            gs.is_paused = True
            h_color = "ai_black"
            a_color = "ai_white"
            game_logger.game_start(h_color, a_color)
            gs.game_id = game_logger.game_id
            change_phase(gs, GamePhase.AI_VS_AI)
            print("[双 AI 自对弈] 模式开启，初始暂停中以供配置参数。")
            return

        if confirm(gs, '是否开局换手(默认您执黑)？'):
            gs.human_is_black = not gs.human_is_black
            push_checkpoint(gs)
            dll.SwapHand(env, gs.human_is_black)
            print(f"[开局换手] 换手成功，当前人类执 {'黑' if gs.human_is_black else '白'}")
        
        # 初始化本盘对局记录
        h_color = "black" if gs.human_is_black else "white"
        a_color = "white" if gs.human_is_black else "black"
        game_logger.game_start(h_color, a_color)
        gs.game_id = game_logger.game_id
        
        # 阶段转移决策
        if not gs.human_is_black:
            # AI 执黑，首手天元由 AI_FIRST 处理
            change_phase(gs, GamePhase.AI_FIRST)
        else:
            # 人类执黑，进入常规对局
            change_phase(gs, GamePhase.NORMAL)
        print("[Debug handle_init] Leaving handle_init successfully")
    except Exception as e:
        import traceback
        print(f"[Debug handle_init] Error: {traceback.format_exc()}")
        raise e


def handle_ai_first(gs: GameState):
    """AI_FIRST phase - AI places first stone at center (Tianyuan)."""
    # 模拟 AI 思考动画，秒落子
    draw(gs)
    draw_blocking_overlay("AI 正在思考中...", "AI 开局秒落天元", (80, 120, 180))
    pygame.display.flip()
    pygame.time.wait(300)
    
    push_checkpoint(gs)
    center = BOARD_SIZE // 2
    dll.DoMove(env, center, center, BLACK)
    gs.history.append((center, center, BLACK))
    
    game_logger.move(len(gs.history), center, center, "black", "ai", phase="AI_FIRST")
    
    if dll.CheckWin(env, center, center, BLACK):
        gs.winner = BLACK
        game_logger.game_end("black", len(gs.history), reason="normal")
        change_phase(gs, GamePhase.GAME_OVER)
    else:
        gs.current_role = WHITE
        # 落天元后，轮到第二手（第1手历史棋子），进入 NORMAL 等待白棋落子（人类或AI）
        change_phase(gs, GamePhase.NORMAL)


def handle_three_hand(gs: GameState):
    """THREE_HAND phase - Three-hand swap decision."""
    if not gs.human_is_black:
        # 人类执白：人类选择是否交换
        if confirm(gs, '是否进行三手交换？'):
            push_checkpoint(gs)
            gs.human_is_black = True
            dll.SwapHand(env, gs.human_is_black)
            game_logger.swap("swap", 0, 0, "human")
            print("[三手交换] 人类选择进行三手交换，当前您执黑，AI执白")
            alert(gs, '您已换执黑棋，轮到您进行第四手落子。')
        else:
            game_logger.swap("no_swap", 0, 0, "human")
            print("[三手交换] 人类选择不交换，继续执白")
        
        # 交换决策完毕，进入 NORMAL 阶段（此时 history=3，等待第四手常规落子）
        gs.three_asked = True
        change_phase(gs, GamePhase.NORMAL)
    else:
        # AI 执白：AI 决定是否交换
        print("[三手交换] AI正在评估局势以决策是否交换...")
        draw(gs)
        draw_blocking_overlay("AI 正在评估三手交换决策...", "正在计算黑白双向最高胜率走法...", (180, 120, 40))
        pygame.display.flip()
        
        # 评估保持执白 (不交换) 的最佳估分
        arr_w = (AIMove * 5)()
        cnt_w = dll.GetTopMoves(env, WHITE, arr_w, 5)
        score_white = arr_w[0].score if cnt_w > 0 else 0
        
        # 评估换手执黑 (交换) 的最佳估分
        arr_b = (AIMove * 5)()
        cnt_b = dll.GetTopMoves(env, BLACK, arr_b, 5)
        score_black = arr_b[0].score if cnt_b > 0 else 0
        
        # 评估完毕，清空积压的点击事件
        pygame.event.clear(pygame.MOUSEBUTTONDOWN)
        pygame.event.clear(pygame.MOUSEBUTTONUP)
        
        print(f"\033[1;33m[三手交换] AI评估双向评分: 保持执白 = {score_white}, 换手执黑 = {score_black}\033[0m")
        
        if score_black > score_white:
            push_checkpoint(gs)
            gs.human_is_black = False
            dll.SwapHand(env, gs.human_is_black)
            game_logger.swap("swap", score_black, score_white, "ai")
            print(f"[三手交换] AI评估 换手执黑胜率更高 ({score_black} > {score_white})，决定进行三手交换！AI执黑，您执白")
            alert(gs, 'AI已决定进行三手交换（AI执黑，您执白）')
        else:
            game_logger.swap("no_swap", score_black, score_white, "ai")
            print(f"[三手交换] AI评估 保持执白更佳 ({score_white} >= {score_black})，决定不交换，继续执白")
            
        gs.three_asked = True
        change_phase(gs, GamePhase.NORMAL)


def handle_five_hand(gs: GameState, btn: pygame.Rect, sidebar_buttons: dict):
    """FIVE_HAND phase - Five-move N-candidates rules."""
    five_n = clamp_five_move_count()
    black_is_human = is_role_human(BLACK)
    
    # 1. 计算候选位置
    if not gs.five_candidates:
        print(f"[五手N打] 开始计算，N={five_n}")
        draw(gs)
        draw_blocking_overlay("五手N打", "正在计算评估五手N打候选位置...", (180, 120, 180))
        pygame.display.flip()
        
        arr = (AIMove * 15)()
        cnt = dll.GetTopMoves(env, BLACK, arr, 15)
        capture_search_log("five_move_candidates")
        candidates = [(m.x, m.y) for m in arr[:min(cnt, max(8, five_n * 3))]]
        
        if black_is_human:
            # 存入 state 供人类选择
            gs.five_candidates = candidates
            print(f"[五手N打] 人类执黑候选位置：{gs.five_candidates}")
        else:
            # AI 执黑：直接筛选出 N 个最平衡（对黑方影响最小）的候选
            selected = choose_low_impact_candidates_for_black(candidates, arr, cnt, five_n)
            gs.five_candidates = selected
            print(f"[五手N打] AI执黑候选位置：{gs.five_candidates}")
            pygame.event.clear(pygame.MOUSEBUTTONDOWN)
            pygame.event.clear(pygame.MOUSEBUTTONUP)
            
    # 2. 交互逻辑
    if gs.game_mode == 1:
        # 自对弈模式：白方 AI 自动决策并选择保留位置
        chosen, score = select_best_candidate_for_white(gs.five_candidates)
        if chosen is not None:
            push_checkpoint(gs)
            dll.DoMove(env, chosen[0], chosen[1], BLACK)
            gs.history.append((chosen[0], chosen[1], BLACK))
            
            # 记录日志
            logger_kwargs = {
                "role_identity": "ai_white",
                "engine_type": "MCTS",
                "visits": gs.ai_white_cfg.get("visits", 64)
            }
            game_logger.five_n(gs.five_candidates, chosen, "ai")
            game_logger.move(len(gs.history), chosen[0], chosen[1], "black", "ai", phase="FIVE_HAND", **logger_kwargs)
            
            if dll.CheckWin(env, chosen[0], chosen[1], BLACK):
                gs.winner = BLACK
                game_logger.game_end("black", len(gs.history), "normal")
                change_phase(gs, GamePhase.GAME_OVER)
            else:
                gs.current_role = WHITE
                change_phase(gs, GamePhase.NORMAL)
            gs.five_candidates = []
        return

    if black_is_human:
        # 人类选择 N 个候选，保存在一个临时列表
        # （这里利用 virtual_candidates 全局兼容变量临时存放人类选择的子集）
        global virtual_candidates
        if not isinstance(virtual_candidates, list):
            virtual_candidates = []
            
        # 确保 virtual_candidates 元素在 gs.five_candidates 中且不超过 N 个
        virtual_candidates = [c for c in virtual_candidates if c in gs.five_candidates][:five_n]
        
        for ev in pygame.event.get():
            if ev.type == QUIT:
                gs.phase = GamePhase.GAME_OVER
                return
            elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                if btn.collidepoint(ev.pos) and gs.history:
                    # 悔棋按钮支持在五手N打阶段使用
                    apply_undo(gs)
                    virtual_candidates = []
                    game_logger.undo(len(gs.history) + 1, len(gs.history))
                    return
                elif ev.pos[0] >= BOARD_AREA_W:
                    # 处理 sidebar
                    pass
                else:
                    gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                    gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                    if (gx, gy) in gs.five_candidates:
                        if (gx, gy) in virtual_candidates:
                            virtual_candidates.remove((gx, gy))
                        else:
                            if len(virtual_candidates) < five_n:
                                if not is_symmetric_to_any((gx, gy), virtual_candidates):
                                    virtual_candidates.append((gx, gy))
                                    print(f"[五手N打] 玩家选择 {(gx, gy)}（当前已选 {len(virtual_candidates)}/{five_n}）")
                                else:
                                    print(f"[五手N打] 位置 {(gx, gy)} 与已选位置对称，不允许选择")
                                    draw(gs)
                                    warning = small_font.render("不能选择对称位置！", True, (255, 0, 0))
                                    screen.blit(warning, (20, 50))
                                    pygame.display.flip()
                                    pygame.time.wait(800)
                                    
        # 如果人类选满了五手 N 打的 N 个点
        if len(virtual_candidates) == five_n:
            print(f"[五手N打] 玩家已选满 {five_n} 个候选：{virtual_candidates}")
            # AI 执白：评估并选择一个最适合白方的点保留
            draw(gs)
            draw_blocking_overlay("AI 正在评估保留点...", "正在计算对白棋最有利的候选点位...", (80, 120, 180))
            pygame.display.flip()
            
            keep_pos, keep_score = select_best_candidate_for_white(virtual_candidates)
            pygame.event.clear(pygame.MOUSEBUTTONDOWN)
            pygame.event.clear(pygame.MOUSEBUTTONUP)
            
            if keep_pos is not None:
                # 播一下保留动画
                for step in range(12):
                    draw(gs)
                    for cx, cy in virtual_candidates:
                        px, py = to_screen(cx, cy)
                        if (cx, cy) == keep_pos:
                            color_intensity = int(128 + 127 * abs(step % 6 - 3) / 3)
                            pygame.draw.circle(screen, (0, color_intensity, 0), (px, py), CELL//2 + 5, 4)
                        else:
                            pygame.draw.circle(screen, (255, 100, 100), (px, py), CELL//2, 3)
                    pygame.display.flip()
                    pygame.time.wait(80)
                
                push_checkpoint(gs)
                dll.DoMove(env, keep_pos[0], keep_pos[1], BLACK)
                gs.history.append((keep_pos[0], keep_pos[1], BLACK))
                
                game_logger.five_n(virtual_candidates, keep_pos, "ai")
                game_logger.move(len(gs.history), keep_pos[0], keep_pos[1], "black", "human", phase="FIVE_HAND")
                
                # 检查黑方是否获胜
                if dll.CheckWin(env, keep_pos[0], keep_pos[1], BLACK):
                    gs.winner = BLACK
                    game_logger.game_end("black", len(gs.history), "normal")
                    change_phase(gs, GamePhase.GAME_OVER)
                else:
                    gs.current_role = WHITE
                    change_phase(gs, GamePhase.NORMAL)
            else:
                # Fix Bug 2: keep_pos is None, 退出回 NORMAL 阶段，防止死锁
                print("[五手N打警告] AI选择保留点返回为空，直接恢复 NORMAL 状态。")
                change_phase(gs, GamePhase.NORMAL)
            
            # 清空辅助变量
            virtual_candidates = []
            gs.five_candidates = []
            
    else:
        # AI 执黑，人类执白：玩家从 AI 提供的 N 个候选中挑选一个保留
        chosen = None
        for ev in pygame.event.get():
            if ev.type == QUIT:
                gs.phase = GamePhase.GAME_OVER
                return
            elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                if btn.collidepoint(ev.pos) and gs.history:
                    apply_undo(gs)
                    gs.five_candidates = []
                    game_logger.undo(len(gs.history) + 1, len(gs.history))
                    return
                elif ev.pos[0] >= BOARD_AREA_W:
                    pass
                else:
                    gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                    gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                    if (gx, gy) in gs.five_candidates:
                        chosen = (gx, gy)
                        print(f"[五手N打] 人类选择保留位置：{chosen}")
                        
        if chosen is not None:
            push_checkpoint(gs)
            dll.DoMove(env, chosen[0], chosen[1], BLACK)
            gs.history.append((chosen[0], chosen[1], BLACK))
            
            game_logger.five_n(gs.five_candidates, chosen, "human")
            game_logger.move(len(gs.history), chosen[0], chosen[1], "black", "ai", phase="FIVE_HAND")
            
            if dll.CheckWin(env, chosen[0], chosen[1], BLACK):
                gs.winner = BLACK
                game_logger.game_end("black", len(gs.history), "normal")
                change_phase(gs, GamePhase.GAME_OVER)
            else:
                gs.current_role = WHITE
                change_phase(gs, GamePhase.NORMAL)
                
            gs.five_candidates = []


def _handle_selfplay_clicks(ev, gs: GameState, buttons: dict):
    if not buttons:
        return
        
    # 暂停 / 继续
    if buttons.get("play_pause") and buttons["play_pause"].collidepoint(ev.pos):
        gs.is_paused = not gs.is_paused
        print(f"[自对弈控制] {'暂停' if gs.is_paused else '继续'}对局")
        return
        
    # 重置
    if buttons.get("reset") and buttons["reset"].collidepoint(ev.pos):
        print("[自对弈控制] 重置局势，重新初始化棋盘...")
        for x, y, r in reversed(gs.history):
            dll.UndoMove(env, x, y, r)
        gs.history = []
        gs.current_role = BLACK
        gs.winner = None
        gs.is_paused = True
        return
        
    # 延迟调节
    if buttons.get("delay_dec") and buttons["delay_dec"].collidepoint(ev.pos):
        gs.ai_delay_ms = max(100, gs.ai_delay_ms - 100)
        return
    if buttons.get("delay_inc") and buttons["delay_inc"].collidepoint(ev.pos):
        gs.ai_delay_ms = min(3000, gs.ai_delay_ms + 100)
        return
        
    # 黑方配置 - 引擎
    if buttons.get("b_mcts") and buttons["b_mcts"].collidepoint(ev.pos):
        gs.ai_black_cfg["engine"] = "MCTS"
        return
    if buttons.get("b_minimax") and buttons["b_minimax"].collidepoint(ev.pos):
        gs.ai_black_cfg["engine"] = "MiniMax"
        return
        
    # 黑方配置 - Visits
    if buttons.get("b_visits_dec") and buttons["b_visits_dec"].collidepoint(ev.pos):
        gs.ai_black_cfg["visits"] = max(2, gs.ai_black_cfg["visits"] - 32)
        return
    if buttons.get("b_visits_inc") and buttons["b_visits_inc"].collidepoint(ev.pos):
        gs.ai_black_cfg["visits"] = min(1000, gs.ai_black_cfg["visits"] + 32)
        return
        
    # 黑方配置 - Policy
    if buttons.get("b_policy_dec") and buttons["b_policy_dec"].collidepoint(ev.pos):
        gs.ai_black_cfg["policy"] = max(0.0, gs.ai_black_cfg["policy"] - 0.1)
        return
    if buttons.get("b_policy_inc") and buttons["b_policy_inc"].collidepoint(ev.pos):
        gs.ai_black_cfg["policy"] = min(1.0, gs.ai_black_cfg["policy"] + 0.1)
        return
        
    # 白方配置 - 引擎
    if buttons.get("w_mcts") and buttons["w_mcts"].collidepoint(ev.pos):
        gs.ai_white_cfg["engine"] = "MCTS"
        return
    if buttons.get("w_minimax") and buttons["w_minimax"].collidepoint(ev.pos):
        gs.ai_white_cfg["engine"] = "MiniMax"
        return
        
    # 白方配置 - Visits
    if buttons.get("w_visits_dec") and buttons["w_visits_dec"].collidepoint(ev.pos):
        gs.ai_white_cfg["visits"] = max(2, gs.ai_white_cfg["visits"] - 32)
        return
    if buttons.get("w_visits_inc") and buttons["w_visits_inc"].collidepoint(ev.pos):
        gs.ai_white_cfg["visits"] = min(1000, gs.ai_white_cfg["visits"] + 32)
        return
        
    # 白方配置 - Policy
    if buttons.get("w_policy_dec") and buttons["w_policy_dec"].collidepoint(ev.pos):
        gs.ai_white_cfg["policy"] = max(0.0, gs.ai_white_cfg["policy"] - 0.1)
        return
    if buttons.get("w_policy_inc") and buttons["w_policy_inc"].collidepoint(ev.pos):
        gs.ai_white_cfg["policy"] = min(1.0, gs.ai_white_cfg["policy"] + 0.1)
        return

    # 白方自定义模型浏览与热重载
    if buttons.get("w_model_select") and buttons["w_model_select"].collidepoint(ev.pos):
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="选择白方 KataGomo 物理模型",
            filetypes=[("Model Files", "*.bin.gz"), ("All Files", "*.*")]
        )
        root.destroy()
        if file_path:
            gs.white_model_path = file_path
            print(f"[白方模型] 已选择模型路径: {file_path}")
            # 自动触发重新加载
            _reload_white_worker_process(gs)
        return

    if buttons.get("w_model_reload") and buttons["w_model_reload"].collidepoint(ev.pos):
        _reload_white_worker_process(gs)
        return



def handle_normal(gs: GameState, btn: pygame.Rect, sidebar_buttons: dict):
    """NORMAL phase - Ordinary turn-by-turn game loop."""
    global search_log_panel_open, search_log_all_calls, five_move_candidate_count, opening_style, selected_search_log_index, last_search_log
    # 状态机守卫：若 history 长度为 3 且还未触发三手交换决策，跳转 to THREE_HAND
    if len(gs.history) == 3 and not gs.three_asked:
        change_phase(gs, GamePhase.THREE_HAND)
        return
        
    # 状态机守卫：若 history 长度为 4，且轮到黑棋落子（第5手），进入五手N打阶段
    if len(gs.history) == 4 and gs.current_role == BLACK:
        change_phase(gs, GamePhase.FIVE_HAND)
        return
        
    is_human_turn = is_role_human(gs.current_role)
    
    if is_human_turn:
        # 人类回合，等待玩家点击
        for ev in pygame.event.get():
            if ev.type == QUIT:
                gs.phase = GamePhase.GAME_OVER
                return
            elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                # 1. 悔棋按钮
                if btn.collidepoint(ev.pos) and gs.history:
                    # 悔 2 步（人类 + AI）或 1 步
                    steps = 2 if len(gs.history) >= 2 else 1
                    prev_len = len(gs.history)
                    for _ in range(steps):
                        apply_undo(gs)
                    game_logger.undo(prev_len, len(gs.history))
                    return
                # 2. 点击右侧 Sidebar 面板
                elif search_log_panel_open and ev.pos[0] >= BOARD_AREA_W:
                    panel_buttons = sidebar_buttons
                    if panel_buttons.get("hide") and panel_buttons["hide"].collidepoint(ev.pos):
                        search_log_panel_open = False
                    elif panel_buttons.get("mode") and panel_buttons["mode"].collidepoint(ev.pos):
                        search_log_all_calls = not search_log_all_calls
                    elif panel_buttons.get("five_dec") and panel_buttons["five_dec"].collidepoint(ev.pos):
                        five_move_candidate_count = max(2, five_move_candidate_count - 1)
                    elif panel_buttons.get("five_inc") and panel_buttons["five_inc"].collidepoint(ev.pos):
                        five_move_candidate_count = min(5, five_move_candidate_count + 1)
                    elif panel_buttons.get("style_trad") and panel_buttons["style_trad"].collidepoint(ev.pos):
                        opening_style = "traditional"
                    elif panel_buttons.get("style_nov") and panel_buttons["style_nov"].collidepoint(ev.pos):
                        opening_style = "novelty"
                    elif panel_buttons.get("style_hyb") and panel_buttons["style_hyb"].collidepoint(ev.pos):
                        opening_style = "hybrid"
                    else:
                        for idx, rect in panel_buttons.get("history", []):
                            if rect.collidepoint(ev.pos):
                                selected_search_log_index = idx
                                last_search_log = search_log_entries[idx]
                                break
                elif not search_log_panel_open and ev.pos[0] >= BOARD_AREA_W:
                    if sidebar_buttons.get("show") and sidebar_buttons["show"].collidepoint(ev.pos):
                        search_log_panel_open = True
                # 3. 棋盘内落子
                else:
                    gx = (ev.pos[1] - MARGIN + CELL//2) // CELL
                    gy = (ev.pos[0] - MARGIN + CELL//2) // CELL
                    if 0 <= gx < BOARD_SIZE and 0 <= gy < BOARD_SIZE:
                        push_checkpoint(gs)
                        if dll.DoMove(env, gx, gy, gs.current_role):
                            gs.history.append((gx, gy, gs.current_role))
                            role_name = "black" if gs.current_role == BLACK else "white"
                            
                            game_logger.move(len(gs.history), gx, gy, role_name, "human", phase="NORMAL")
                            print(f"[普通回合] 人类落子：{(gx, gy)}，角色：{role_name}")
                            
                            if dll.CheckWin(env, gx, gy, gs.current_role):
                                gs.winner = gs.current_role
                                game_logger.game_end(role_name, len(gs.history), "normal")
                                change_phase(gs, GamePhase.GAME_OVER)
                            else:
                                gs.current_role = 1 - gs.current_role
    else:
        # AI 回合
        global ai_is_searching, last_ai_move_ticks
        
        # 1.3 如果处于双 AI 自对弈模式且暂停，仅处理常规事件并直接返回
        if gs.phase == GamePhase.AI_VS_AI and gs.is_paused:
            for ev in pygame.event.get():
                if ev.type == QUIT:
                    gs.phase = GamePhase.GAME_OVER
                    return
                elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                    _handle_selfplay_clicks(ev, gs, sidebar_buttons)
            return
            
        # 1.3 自对弈模式步时延迟检查
        if gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1:
            now = pygame.time.get_ticks()
            if now - last_ai_move_ticks < gs.ai_delay_ms:
                for ev in pygame.event.get():
                    if ev.type == QUIT:
                        gs.phase = GamePhase.GAME_OVER
                        return
                    elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
                        _handle_selfplay_clicks(ev, gs, sidebar_buttons)
                return

        # 2.1 动态读取对应 AI 角色的配置参数
        current_cfg = gs.ai_black_cfg if gs.current_role == BLACK else gs.ai_white_cfg
        engine_type = current_cfg.get("engine", "MCTS")
        visits = current_cfg.get("visits", 128)
        policy_blend = current_cfg.get("policy", 0.6)
        value_blend = current_cfg.get("value", 0.6)

        stage = decide_search_framework(gs)
        if stage != "Book":
            # 2.3 支持动态引擎切换
            stage = "MCTS" if engine_type == "MCTS" else "MiniMax"
            ai_is_searching = True
            draw(gs)
            pygame.display.flip()
            
        # --- 阶段 1: 开局库秒查 ---
        if stage == "Book":
            bx, by = book.query([(h[0], h[1]) for h in gs.history], style=opening_style)
            if bx is not None and by is not None:
                push_checkpoint(gs)
                if dll.DoMove(env, bx, by, gs.current_role):
                    gs.history.append((bx, by, gs.current_role))
                    role_name = "black" if gs.current_role == BLACK else "white"
                    
                    # 虚拟一个 search_log 方便 sidebar 渲染
                    entry = {
                        "searchId": len(search_log_entries) + 1,
                        "role": role_name,
                        "turn": len(gs.history),
                        "context": "ai_move",
                        "historyLen": len(gs.history) - 1,
                        "totalMs": 0.0,
                        "reachedDepth": 0,
                        "targetDepth": 0,
                        "kataEnabled": False,
                        "kataReady": False,
                        "kataApplied": False,
                        "kataVisits": 0,
                        "policyBlend": 0.0,
                        "valueBlend": 0.0,
                        "kataStatus": "决策：开局库 (Book)",
                        "chosenMove": {"x": bx, "y": by, "score": 0},
                        "moves": [{"rank": 1, "x": bx, "y": by, "finalScore": 0, "neighborCnt": 0}],
                        "history": [(int(h[0]), int(h[1])) for h in gs.history[:-1]]
                    }
                    last_search_log = entry
                    search_log_entries.append(entry)
                    del search_log_entries[:-30]
                    selected_search_log_index = len(search_log_entries) - 1
                    
                    logger_kwargs = {}
                    if gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1:
                        logger_kwargs = {
                            "role_identity": f"ai_{role_name}",
                            "engine_type": "Book",
                            "visits": 0
                        }
                    game_logger.move(len(gs.history), bx, by, role_name, "ai", phase=gs.phase.name, search_id=entry["searchId"], **logger_kwargs)
                    print(f"[普通回合] AI查库秒落子：{(bx, by)}，角色：{role_name}")
                    
                    # 更新步时计时器
                    last_ai_move_ticks = pygame.time.get_ticks()
                    
                    if dll.CheckWin(env, bx, by, gs.current_role):
                        gs.winner = gs.current_role
                        game_logger.game_end(role_name, len(gs.history), "normal")
                        change_phase(gs, GamePhase.GAME_OVER)
                    else:
                        gs.current_role = 1 - gs.current_role
                    return
            print("[普通回合] 开局库无匹配，自动进入AI搜索。")
            stage = "MCTS" if engine_type == "MCTS" else "MiniMax"
            ai_is_searching = True
            draw(gs)
            pygame.display.flip()
            
        # --- 阶段 2/3: AI 深度搜索 ---
        if stage == "MCTS":
            # 2.2 在 MCTS 时动态注入专属搜索参数
            if not (gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1):
                visits = 128 if len(gs.history) <= 6 else 64
                policy_blend = 1.0 if len(gs.history) <= 6 else 0.6
                value_blend = 1.0 if len(gs.history) <= 6 else 0.6
                
            if set_kata_enabled is not None:
                set_kata_enabled(env, True)
            if set_kata_search_params is not None:
                set_kata_search_params(env, visits, 0.0, policy_blend, value_blend)
        else: # MiniMax
            # 2.3 支持切换为 MiniMax 引擎，停用网络
            if set_kata_enabled is not None:
                set_kata_enabled(env, False)
            if set_kata_search_params is not None:
                set_kata_search_params(env, 0, 0.0, 0.0, 0.0)
                
        # 如果是白方回合，且配置了外部白方物理模型
        is_white_worker_active = (gs.current_role == WHITE and gs.white_model_path)
        
        if is_white_worker_active:
            global white_worker_process
            if white_worker_process is None:
                _reload_white_worker_process(gs)
            
            ai_is_searching = True
            draw(gs)
            pygame.display.flip()
            
            # 使用多进程白方 AI Worker 决策落子
            m = _query_white_worker_move(gs, visits, policy_blend, value_blend, engine_type)
            
            ai_is_searching = False
            pygame.event.clear(pygame.MOUSEBUTTONDOWN)
            pygame.event.clear(pygame.MOUSEBUTTONUP)
            
            if m is not None:
                # 构造一个符合 logger 规范的 search log 条目
                entry = {
                    "searchId": len(search_log_entries) + 1,
                    "role": "white",
                    "turn": len(gs.history) + 1,
                    "context": "ai_move",
                    "historyLen": len(gs.history),
                    "totalMs": 0.0,
                    "reachedDepth": 0,
                    "targetDepth": 0,
                    "kataEnabled": True,
                    "kataReady": True,
                    "kataApplied": True,
                    "kataVisits": visits,
                    "policyBlend": policy_blend,
                    "valueBlend": value_blend,
                    "kataStatus": "子进程决策 (Dual Model)",
                    "chosenMove": {"x": m.x, "y": m.y, "score": m.score},
                    "moves": [{"rank": 1, "x": m.x, "y": m.y, "finalScore": m.score, "neighborCnt": 0}],
                    "history": [(int(h[0]), int(h[1])) for h in gs.history]
                }
                last_search_log = entry
                search_log_entries.append(entry)
                del search_log_entries[:-30]
                selected_search_log_index = len(search_log_entries) - 1
                
                push_checkpoint(gs)
                if dll.DoMove(env, m.x, m.y, gs.current_role):
                    gs.history.append((m.x, m.y, gs.current_role))
                    role_name = "white"
                    
                    logger_kwargs = {
                        "role_identity": "ai_white",
                        "engine_type": engine_type,
                        "visits": visits
                    }
                    
                    game_logger.move(len(gs.history), m.x, m.y, role_name, "ai", phase=gs.phase.name, search_id=entry["searchId"], **logger_kwargs)
                    print(f"[普通回合] 白方AI(子进程)落子：{(m.x, m.y)}，得分：{m.score}")
                    
                    last_ai_move_ticks = pygame.time.get_ticks()
                    
                    if dll.CheckWin(env, m.x, m.y, gs.current_role):
                        gs.winner = gs.current_role
                        game_logger.game_end(role_name, len(gs.history), "normal")
                        change_phase(gs, GamePhase.GAME_OVER)
                    else:
                        gs.current_role = 1 - gs.current_role
            else:
                print("[普通回合] 白方AI(子进程)通信错误，未获取到合法落子！")
        else:
            # 原始内置 DLL AI 决策流
            arr = (AIMove * 10)()
            cnt = dll.GetTopMoves(env, gs.current_role, arr, 10)
            
            ai_is_searching = False
            pygame.event.clear(pygame.MOUSEBUTTONDOWN)
            pygame.event.clear(pygame.MOUSEBUTTONUP)
            
            if cnt > 0:
                m = arr[0]
                entry = capture_search_log("ai_move", force=True, chosen_move=m)
                search_id_logged = entry.get("searchId") if entry else None
                
                push_checkpoint(gs)
                if dll.DoMove(env, m.x, m.y, gs.current_role):
                    gs.history.append((m.x, m.y, gs.current_role))
                    role_name = "black" if gs.current_role == BLACK else "white"
                    
                    logger_kwargs = {}
                    if gs.phase == GamePhase.AI_VS_AI or gs.game_mode == 1:
                        logger_kwargs = {
                            "role_identity": f"ai_{role_name}",
                            "engine_type": engine_type,
                            "visits": visits if engine_type == "MCTS" else 0
                        }
                    
                    game_logger.move(len(gs.history), m.x, m.y, role_name, "ai", phase=gs.phase.name, search_id=search_id_logged, **logger_kwargs)
                    print(f"[普通回合] AI落子：{(m.x, m.y)}，决策：{stage}，评分：{m.score}")
                    
                    last_ai_move_ticks = pygame.time.get_ticks()
                    
                    if dll.CheckWin(env, m.x, m.y, gs.current_role):
                        gs.winner = gs.current_role
                        game_logger.game_end(role_name, len(gs.history), "normal")
                        change_phase(gs, GamePhase.GAME_OVER)
                    else:
                        gs.current_role = 1 - gs.current_role



def handle_game_over(gs: GameState):
    """GAME_OVER phase - Waiting for restart or exit."""
    # 渲染带有“再来一局”的结算按钮
    w_btn = pygame.Rect(BOARD_AREA_W // 2 - 80, HEIGHT - STATUS_H + 8, 160, 42)
    pygame.draw.rect(screen, (40, 150, 110), w_btn, border_radius=5)
    screen.blit(font.render('再来一局', True, (255,255,255)), (w_btn.x + 32, w_btn.y + 6))
    
    for ev in pygame.event.get():
        if ev.type == QUIT:
            gs.phase = GamePhase.TERMINATED
        elif ev.type == MOUSEBUTTONDOWN and ev.button == 1:
            if w_btn.collidepoint(ev.pos):
                print("[状态机重置] 玩家请求再来一局，初始化新状态...")
                # 重新初始化 DLL 引擎棋盘状态
                for x, y, r in reversed(gs.history):
                    dll.UndoMove(env, x, y, r)
                # 重新置空所有状态
                gs.history.clear()
                gs.five_candidates.clear()
                gs.winner = None
                gs.current_role = BLACK
                gs.human_is_black = True
                gs.game_id = None
                undo_stack.clear()
                global virtual_candidates
                virtual_candidates = []
                
                change_phase(gs, GamePhase.INIT)


# -------------------------------------------------------------------
# 子进程 Worker 通信与生命周期函数
# -------------------------------------------------------------------
def _reload_white_worker_process(gs: GameState):
    global white_worker_process
    if white_worker_process is not None:
        try:
            white_worker_process.stdin.write("quit\n")
            white_worker_process.stdin.flush()
            white_worker_process.terminate()
            white_worker_process.wait(timeout=1.0)
        except Exception:
            pass
        white_worker_process = None
        
    if not gs.white_model_path:
        return
        
    print(f"[Worker] 启动白方独立子进程，载入模型: {gs.white_model_path}")
    worker_script = os.path.join(PROJECT_ROOT, "tools", "ai_worker.py")
    try:
        # 使用 sys.executable 保持 Python 环境一致
        white_worker_process = subprocess.Popen(
            [sys.executable, worker_script, gs.white_model_path, KATA_CONFIG_PATH],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # 等待 ready 信号
        ready_line = white_worker_process.stdout.readline()
        if ready_line:
            status = json.loads(ready_line.strip())
            if status.get("status") == "ready":
                print("[Worker] 白方 AI 子进程启动成功且已就绪！")
            else:
                print(f"[Worker] 子进程启动异常: {status}")
    except Exception as e:
        print(f"[Worker] 启动子进程失败: {e}")
        white_worker_process = None

def _query_white_worker_move(gs: GameState, visits, policy, value, engine) -> Optional[AIMove]:
    global white_worker_process
    if white_worker_process is None:
        return None
        
    # 构建当前棋盘的落子历史序列传输给子进程
    # 注意: 把 GameState 序列里的 (x, y, role) 转换为子进程需要的格式
    history_list = []
    for x, y, r in gs.history:
        history_list.append([int(x), int(y), int(r)])
        
    req = {
        "action": "search",
        "history": history_list,
        "visits": int(visits),
        "policy": float(policy),
        "value": float(value),
        "engine": str(engine),
        "role": int(WHITE)
    }
    
    try:
        white_worker_process.stdin.write(json.dumps(req) + "\n")
        white_worker_process.stdin.flush()
        
        resp_line = white_worker_process.stdout.readline()
        if resp_line:
            resp = json.loads(resp_line.strip())
            if resp.get("status") == "ok":
                # 返回一个模拟的 AIMove 结构
                res = AIMove()
                res.x = int(resp["x"])
                res.y = int(resp["y"])
                res.score = int(resp["score"])
                return res
            else:
                print(f"[Worker] 搜索出错: {resp.get('error')}")
    except Exception as e:
        print(f"[Worker] 通信发送/接收着法异常: {e}")
        _reload_white_worker_process(gs)
    return None

def dispatch(gs: GameState, btn: pygame.Rect, sidebar_buttons: dict):
    """Dispatch execution logic based on gs.phase."""
    if gs.phase == GamePhase.INIT:
        handle_init(gs)
    elif gs.phase == GamePhase.AI_FIRST:
        handle_ai_first(gs)
    elif gs.phase == GamePhase.THREE_HAND:
        handle_three_hand(gs)
    elif gs.phase == GamePhase.FIVE_HAND:
        handle_five_hand(gs, btn, sidebar_buttons)
    elif gs.phase == GamePhase.NORMAL or gs.phase == GamePhase.AI_VS_AI:
        handle_normal(gs, btn, sidebar_buttons)
    elif gs.phase == GamePhase.GAME_OVER:
        handle_game_over(gs)



# -------------------------------------------------------------------
# 重新激活的精简主循环 (Task 2.8)
# -------------------------------------------------------------------
try:
    print("[Debug Startup] Creating GameState...")
    gs = GameState(phase=GamePhase.INIT)
    print("[Debug Startup] Entering main game loop...")
    while gs.phase != GamePhase.TERMINATED:
        # 1. 绘制游戏画面
        btn, sidebar_buttons = draw(gs)
        pygame.display.flip()
        
        # 2. 分发状态处理
        try:
            dispatch(gs, btn, sidebar_buttons)
        except Exception as e:
            import traceback
            err_msg = f"[主循环崩溃] 发生未知异常: {type(e).__name__}: {e}"
            print(err_msg, file=sys.stderr)
            logger.error(f"[主循环崩溃] 发生未知异常:\n{traceback.format_exc()}")
            raise e
        
        # 控制帧率，防止 CPU 空转过热
        pygame.time.wait(15)
except Exception as global_exc:
    import traceback
    crash_msg = f"[全局异常捕获] 进程即将闪退: {type(global_exc).__name__}: {global_exc}"
    print(crash_msg, file=sys.stderr)
    logger.error(f"[全局异常捕获] 进程即将闪退，堆栈信息:\n{traceback.format_exc()}")
finally:
    if 'gs' in locals():
        game_logger.session_end(len(gs.history))
    else:
        game_logger.session_end(0)
        
    # 清理外部子进程进程树
    if white_worker_process is not None:
        try:
            white_worker_process.stdin.write("quit\n")
            white_worker_process.stdin.flush()
            white_worker_process.terminate()
            white_worker_process.wait(timeout=1.0)
        except Exception:
            pass
            
    pygame.quit()
    dll.ReleaseEngine(env)
    sys.exit()

