import os
import sys
import ctypes
import pytest

BLACK, WHITE = 0, 1
BOARD_SIZE = 15

# 根据 platform 定位和加载 C++ DLL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DLL_PATH = os.path.join(BASE_DIR, "engine", "GameEngine.so" if sys.platform != "win32" else "GameEngine.dll")

class GameEngine(ctypes.Structure):
    pass

class AIMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("score", ctypes.c_int)]

@pytest.fixture(scope="module")
def dll():
    if not os.path.exists(DLL_PATH):
        pytest.skip(f"GameEngine.dll not found at {DLL_PATH}, skipping Tier 2 integration tests.")
    
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(BASE_DIR)
        
    try:
        loaded_dll = ctypes.CDLL(DLL_PATH)
        
        # 原型定义
        loaded_dll.GetGameEngine.restype = ctypes.POINTER(GameEngine)
        loaded_dll.CheckWin.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
        loaded_dll.CheckWin.restype = ctypes.c_bool
        loaded_dll.SwapHand.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_bool]
        loaded_dll.DoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
        loaded_dll.DoMove.restype = ctypes.c_bool
        loaded_dll.UndoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
        loaded_dll.UndoMove.restype = ctypes.c_bool
        loaded_dll.GetTopMoves.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.POINTER(AIMove), ctypes.c_int]
        loaded_dll.GetTopMoves.restype = ctypes.c_int
        loaded_dll.GetBoardState.argtypes = [ctypes.POINTER(GameEngine), ctypes.POINTER(ctypes.c_int), ctypes.c_bool]
        loaded_dll.ReleaseEngine.argtypes = [ctypes.POINTER(GameEngine)]
        
        return loaded_dll
    except Exception as e:
        pytest.skip(f"Failed to load or configure GameEngine.dll: {e}")

_move_history = []

def tracked_do_move(dll, engine, x, y, role):
    """Call dll.DoMove and track the move for automatic cleanup."""
    success = dll.DoMove(engine, x, y, role)
    if success:
        _move_history.append((x, y, role))
    return success

@pytest.fixture
def env(dll):
    engine = dll.GetGameEngine()
    _move_history.clear()

    yield engine

    # 逆序撤销本次测试所下的所有棋子
    for x, y, role in reversed(_move_history):
        dll.UndoMove(engine, x, y, role)
    _move_history.clear()

def test_dll_load_and_init(dll, env):
    # 测试 DLL 成功加载并且可以实例化 GameEngine
    assert env is not None

def test_do_and_undo_move(dll, env):
    # 测试落子与撤销落子
    # 在天元 (7, 7) 下黑子
    res = tracked_do_move(dll, env, 7, 7, BLACK)
    assert res is True

    # 验证棋盘状态已更新
    board = (ctypes.c_int * (BOARD_SIZE * BOARD_SIZE))()
    dll.GetBoardState(env, board, True)
    assert board[7 * BOARD_SIZE + 7] == BLACK

    # 撤销
    res_undo = dll.UndoMove(env, 7, 7, BLACK)
    assert res_undo is True
    _move_history.clear()  # 手动撤销后清空历史，防止 fixture 重复撤销

    # 验证棋盘状态被清除
    dll.GetBoardState(env, board, True)
    assert board[7 * BOARD_SIZE + 7] == -1  # NONE=-1

def test_check_win_horizontal(dll, env):
    # 测试水平连五获胜判定
    for i in range(4):
        tracked_do_move(dll, env, 7, i, BLACK)

    assert dll.CheckWin(env, 7, 3, BLACK) is False

    tracked_do_move(dll, env, 7, 4, BLACK)
    assert dll.CheckWin(env, 7, 4, BLACK) is True

def test_check_win_vertical(dll, env):
    # 测试垂直连五获胜判定
    for i in range(4):
        tracked_do_move(dll, env, i, 5, WHITE)

    assert dll.CheckWin(env, 3, 5, WHITE) is False

    tracked_do_move(dll, env, 4, 5, WHITE)
    assert dll.CheckWin(env, 4, 5, WHITE) is True

def test_forbidden_moves_double_three(dll, env):
    # 用全新 Engine 测试黑棋双三禁手规则判定。
    # 摆放两个活二：
    # 活三 1 横向：空(7,5) - 黑(7,6) - 黑(7,7)[待下] - 黑(7,8) - 空(7,9)
    # 这会形成 "01110" 活三模式
    tracked_do_move(dll, env, 7, 6, BLACK)
    tracked_do_move(dll, env, 7, 8, BLACK)

    # 活三 2 纵向：空(5,7) - 黑(6,7) - 黑(7,7)[待下] - 黑(8,7) - 空(9,7)
    # 这会形成 "01110" 活三模式
    tracked_do_move(dll, env, 6, 7, BLACK)
    tracked_do_move(dll, env, 8, 7, BLACK)
    
    # 检查棋盘状态
    board = (ctypes.c_int * (BOARD_SIZE * BOARD_SIZE))()
    dll.GetBoardState(env, board, True)
    
    # 打印非 -1 的格子以利于调试
    non_empty = []
    for i in range(BOARD_SIZE):
        for j in range(BOARD_SIZE):
            val = board[i * BOARD_SIZE + j]
            if val != -1:
                non_empty.append(((i, j), val))
    print(f"Non-empty board cells: {non_empty}")
    
    # 交叉点 7, 7 应该被标记为 2 (禁手点)
    assert board[7 * BOARD_SIZE + 7] == 2
