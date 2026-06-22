import sys
import ctypes
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DLL_PATH = os.path.join(PROJECT_ROOT, "engine", "GameEngine.so" if sys.platform != "win32" else "GameEngine.dll")
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(PROJECT_ROOT)
dll = ctypes.CDLL(DLL_PATH)

class GameEngine(ctypes.Structure): pass
class AIMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("score", ctypes.c_int)]

dll.GetGameEngine.restype = ctypes.POINTER(GameEngine)
load_kata_model = getattr(dll, "LoadKataModel", None)
set_kata_enabled = getattr(dll, "SetKataEnabled", None)
set_kata_search_params = getattr(dll, "SetKataSearchParams", None)
is_kata_ready = getattr(dll, "IsKataReady", None)

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

dll.DoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.DoMove.restype = ctypes.c_bool
dll.UndoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.UndoMove.restype = ctypes.c_bool
dll.GetTopMoves.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.POINTER(AIMove), ctypes.c_int]
dll.GetTopMoves.restype = ctypes.c_int

env = dll.GetGameEngine()
local_history = []

def _reset_board_state():
    """Reset local board state by undoing all moves."""
    global local_history
    for x, y, r in reversed(local_history):
        dll.UndoMove(env, x, y, r)
    local_history = []

def _init_vcf():
    """Initialize VCF solver by doing a dummy move cycle to ensure zob_board is set."""
    cx, cy, cr = 7, 7, 0
    dll.DoMove(env, cx, cy, cr)
    dll.UndoMove(env, cx, cy, cr)

def main():
    global local_history
    # 从命令行参数读取模型路径与配置路径
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing model_path or config_path command args", "status": "error"}), flush=True)
        sys.exit(1)
        
    model_path = os.path.realpath(sys.argv[1])
    config_path = os.path.realpath(sys.argv[2])

    # SECURITY: Resolve symlinks and reject path traversal attempts
    for p in (model_path, config_path):
        rel = os.path.relpath(p, PROJECT_ROOT)
        if ".." in rel.split(os.sep):
            print(json.dumps({"error": f"Path traversal rejected: {p}", "status": "error"}), flush=True)
            sys.exit(1)
    
    # 载入模型
    if load_kata_model is None:
        print(json.dumps({"error": "LoadKataModel function not found in DLL", "status": "error"}), flush=True)
        sys.exit(1)
    loaded = load_kata_model(env, model_path.encode("utf-8"), config_path.encode("utf-8"))
    if not loaded:
        print(json.dumps({"error": f"Failed to load KataModel: {model_path}", "status": "error"}), flush=True)
        sys.exit(1)

    # Initialize VCF solver zob_board after model load
    _init_vcf()

    print(json.dumps({"status": "ready"}), flush=True)
    
    while True:
        line = sys.stdin.readline()
        if not line:
            # EOF, 主进程已退出，自动清理并退出
            break
            
        line = line.strip()
        if not line or line == "quit":
            break
            
        try:
            req = json.loads(line)
            action = req.get("action")
            if action == "reset":
                _reset_board_state()
                _init_vcf()
                print(json.dumps({"status": "ok"}), flush=True)
                continue
            elif action == "search":
                received_history = req.get("history", []) # List of [x, y, role]

                # Validate history moves
                valid = True
                for move in received_history:
                    if not isinstance(move, (list, tuple)) or len(move) != 3:
                        valid = False
                        break
                    mx, my, mr = move
                    if not (isinstance(mx, int) and isinstance(my, int) and isinstance(mr, int)):
                        valid = False
                        break
                    if not (0 <= mx <= 14 and 0 <= my <= 14 and mr in (0, 1)):
                        valid = False
                        break
                if not valid:
                    print(json.dumps({"error": "Invalid history move coordinates or role", "status": "error"}), flush=True)
                    continue

                # 同步本地棋盘状态
                for x, y, r in reversed(local_history):
                    dll.UndoMove(env, x, y, r)
                for x, y, r in received_history:
                    dll.DoMove(env, x, y, r)
                local_history = received_history
                # Re-initialize VCF solver zob_board after board sync
                _init_vcf()
                
                # 设置当前 AI 搜索参数
                visits = req.get("visits", 64)
                policy_blend = req.get("policy", 0.3)
                value_blend = req.get("value", 0.3)
                engine_type = req.get("engine", "MCTS")
                role = req.get("role", 1) # 默认 WHITE = 1
                
                if engine_type == "MCTS":
                    if set_kata_enabled is None or set_kata_search_params is None:
                        print(json.dumps({"error": "KataGo functions not available in DLL", "status": "error"}), flush=True)
                        continue
                    set_kata_enabled(env, True)
                    set_kata_search_params(env, visits, 0.0, policy_blend, value_blend)
                else:
                    if set_kata_enabled is not None:
                        set_kata_enabled(env, False)
                    if set_kata_search_params is not None:
                        set_kata_search_params(env, 0, 0.0, 0.0, 0.0)
                    
                # 进行决策搜索
                arr = (AIMove * 10)()
                cnt = dll.GetTopMoves(env, role, arr, 10)
                
                if cnt > 0:
                    best = arr[0]
                    resp = {
                        "x": best.x,
                        "y": best.y,
                        "score": best.score,
                        "status": "ok"
                    }
                else:
                    resp = {
                        "error": "No legal moves found",
                        "status": "error"
                    }
                print(json.dumps(resp), flush=True)
                
        except Exception as e:
            print(json.dumps({"error": f"Exception: {str(e)}", "status": "error"}), flush=True)

if __name__ == "__main__":
    main()
