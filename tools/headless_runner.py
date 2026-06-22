#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gomoku Headless Runner
Enforces international Gomoku rules (Three-hand swap, Five-hand N-play)
Directly loads GameEngine shared library for Black AI and communicates with ai_worker.py for White AI if a custom model is supplied.
Outputs a structured JSON match report when all games complete.
"""

import sys
import os
import json
import ctypes
import argparse
import time
import math
from pathlib import Path
from typing import List, Tuple, Optional

# Ensure project root is in sys.path for module imports
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.worker_client import WorkerClient

# SPRT: use ml/sprt.py if available, fall back to local implementation
try:
    from ml.sprt import sprt_check as _sprt_check, compute_sprt_result
    _HAS_SPRT_MODULE = True
except ImportError:
    _HAS_SPRT_MODULE = False

    def _sprt_check(wins, losses, alpha=0.05, beta=0.05, elo_diff=35):
        if wins + losses < 1:
            return None
        p1 = 1.0 / (1.0 + 10.0 ** (-elo_diff / 400.0))
        p0 = 0.5
        llr = 0.0
        if wins > 0:
            llr += wins * math.log(p1 / p0)
        if losses > 0:
            llr += losses * math.log((1 - p1) / (1 - p0))
        a = math.log(beta / (1 - alpha))
        b = math.log((1 - beta) / alpha)
        if llr >= b:
            return "candidate_wins"
        elif llr <= a:
            return "baseline_wins"
        return None

    def compute_sprt_result(wins, losses, alpha=0.05, beta=0.05, elo_diff=35.0):
        total = wins + losses
        winrate = wins / total if total > 0 else 0.5
        decision_raw = _sprt_check(wins, losses, alpha, beta, elo_diff)
        decision = "accept" if decision_raw == "candidate_wins" else "reject" if decision_raw == "baseline_wins" else "undecided"
        return type("SPRTResult", (), {
            "decision": decision, "llr": 0.0, "elo_diff": 0.0,
            "ci_lower": 0.0, "ci_upper": 0.0, "winrate": winrate,
            "wins": wins, "losses": losses, "total": total,
            "to_dict": lambda self: {"decision": self.decision, "winrate": self.winrate,
                                     "wins": self.wins, "losses": self.losses, "total": self.total}
        })()

# Constants
BOARD_SIZE = 15
BLACK, WHITE = 0, 1
FIVE_MOVE_CANDIDATE_COUNT = 3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DLL_PATH = os.path.join(PROJECT_ROOT, "engine", "GameEngine.so" if sys.platform != "win32" else "GameEngine.dll")
KATA_CONFIG_PATH = os.path.join(PROJECT_ROOT, "KataGomo", "scripts", "gomocup", "default_gtp.cfg")
OPENING_BOOK_PATH = os.path.join(PROJECT_ROOT, "game", "data", "opening_book.json")

# Add DLL directory to PATH if Windows Python 3.8+
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(PROJECT_ROOT)

# Load GameEngine shared library
try:
    dll = ctypes.CDLL(DLL_PATH)
except Exception as e:
    print(f"[Error] Failed to load GameEngine shared library: {e}")
    sys.exit(1)

class GameEngine(ctypes.Structure): pass
class AIMove(ctypes.Structure):
    _fields_ = [("x", ctypes.c_int), ("y", ctypes.c_int), ("score", ctypes.c_int)]

# DLL bindings
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

dll.CheckWin.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.CheckWin.restype = ctypes.c_bool
dll.SwapHand.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_bool]
dll.DoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.DoMove.restype = ctypes.c_bool
dll.UndoMove.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.c_int, ctypes.c_int]
dll.UndoMove.restype = ctypes.c_bool
dll.GetTopMoves.argtypes = [ctypes.POINTER(GameEngine), ctypes.c_int, ctypes.POINTER(AIMove), ctypes.c_int]
dll.GetTopMoves.restype = ctypes.c_int
dll.ReleaseEngine.argtypes = [ctypes.POINTER(GameEngine)]

# Load opening book
sys.path.insert(0, PROJECT_ROOT)
from ml.verify_opening_book import OpeningBook
try:
    opening_book = OpeningBook(OPENING_BOOK_PATH)
except Exception as e:
    print(f"[Warning] Failed to load opening book: {e}")
    opening_book = None

# Global handle for white worker client
white_worker_client: Optional[WorkerClient] = None

def _start_white_worker(white_model_path: str) -> Optional[WorkerClient]:
    """Start a WorkerClient for the given white model."""
    if not white_model_path:
        return None
    print(f"[Worker] Spawning White AI Worker with model: {white_model_path}")
    client = WorkerClient(white_model_path, KATA_CONFIG_PATH, timeout=10.0, max_retries=2)
    if client.start():
        print("[Worker] White AI Worker successfully initialized and ready!")
        return client
    else:
        print("[Worker] Failed to start White AI Worker")
        return None

def is_symmetric(pos1, pos2, center_x=BOARD_SIZE//2, center_y=BOARD_SIZE//2):
    x1, y1 = pos1
    x2, y2 = pos2
    if (2*center_x - x1 == x2) and (2*center_y - y1 == y2):
        return True
    if x1 == x2 and abs(y1 - center_y) == abs(y2 - center_y) and y1 != y2:
        return True
    if y1 == y2 and abs(x1 - center_x) == abs(x2 - center_x) and x1 != x2:
        return True
    if abs(x1 - center_x) == abs(y1 - center_y) and abs(x2 - center_x) == abs(y2 - center_y):
        if (x1 - center_x) == (y1 - center_y) and (x2 - center_x) == (y2 - center_y):
            return True
        if (x1 - center_x) == -(y1 - center_y) and (x2 - center_x) == -(y2 - center_y):
            return True
    return False

def get_distance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

def is_symmetric_to_any(pos, selected):
    return any(is_symmetric(prev, pos) for prev in selected)

def rank_move_score_from_arr(arr, cnt, pos):
    return next((arr[i].score for i in range(cnt) if (arr[i].x, arr[i].y) == pos), 0)

def choose_low_impact_candidates_for_black(candidates, arr, cnt, n):
    ranked = sorted(
        candidates,
        key=lambda pos: (rank_move_score_from_arr(arr, cnt, pos), -get_distance(pos, (BOARD_SIZE // 2, BOARD_SIZE // 2)))
    )
    selected = []
    for pos in ranked:
        if pos not in selected and not is_symmetric_to_any(pos, selected):
            selected.append(pos)
        if len(selected) >= n:
            break
    for pos in ranked:
        if len(selected) >= n:
            break
        if pos not in selected:
            selected.append(pos)
    return selected[:n]

def evaluate_virtual_move_for_white(env, x, y):
    if dll.DoMove(env, x, y, BLACK):
        arr = (AIMove * 5)()
        cnt = dll.GetTopMoves(env, WHITE, arr, 5)
        white_best_score = arr[0].score if cnt > 0 else 0
        dll.UndoMove(env, x, y, BLACK)
        return white_best_score
    return -9999

def select_best_candidate_for_white(env, candidates):
    if not candidates:
        return None
    scores = []
    for cx, cy in candidates:
        white_value = evaluate_virtual_move_for_white(env, cx, cy)
        scores.append(((cx, cy), white_value))
    return max(scores, key=lambda x: x[1])[0]

def parse_args():
    parser = argparse.ArgumentParser(description="Gomoku Headless Match Runner")
    parser.add_argument(
        "--black-model",
        type=str,
        default="",
        help="Path to Black AI model (.bin.gz)."
    )
    parser.add_argument(
        "--white-model",
        type=str,
        default="",
        help="Path to White AI model (.bin.gz)."
    )
    parser.add_argument(
        "--games",
        type=int,
        default=10,
        help="Total number of games to play."
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent match threads (fixed to 1 currently)."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="eval_result.json",
        help="Path to output JSON result report."
    )
    parser.add_argument(
        "--visits-black",
        type=int,
        default=128,
        help="MCTS search visits for Black AI."
    )
    parser.add_argument(
        "--visits-white",
        type=int,
        default=64,
        help="MCTS search visits for White AI."
    )
    parser.add_argument(
        "--early-stop",
        action="store_true",
        default=False,
        help="Enable SPRT early termination when result is statistically significant."
    )
    parser.add_argument(
        "--min-games",
        type=int,
        default=20,
        help="Minimum number of games before SPRT early stop can trigger (default: 20)."
    )
    parser.add_argument(
        "--sprt-h1",
        type=float,
        default=35.0,
        help="SPRT H1 hypothesis: Elo difference to detect (default: 35)."
    )
    parser.add_argument(
        "--sprt-alpha",
        type=float,
        default=0.05,
        help="SPRT Type I error rate (default: 0.05)."
    )
    parser.add_argument(
        "--sprt-beta",
        type=float,
        default=0.05,
        help="SPRT Type II error rate (default: 0.05)."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    print("=" * 60)
    print("Gomoku Headless Runner Initialized")
    print(f"Model A (candidate): {args.black_model or 'Default DLL Model'}")
    print(f"Model B (baseline):  {args.white_model or 'Default DLL Model'}")
    print(f"Games: {args.games}")
    print(f"Output Report: {args.output}")
    print(f"Early Stop: {args.early_stop}")
    if args.early_stop:
        print(f"  SPRT H1: {args.sprt_h1} Elo, Alpha: {args.sprt_alpha}, Beta: {args.sprt_beta}")
        print(f"  Min Games: {args.min_games}")
    print("=" * 60)

    # Spin up White worker subprocess if custom white model configured
    if args.white_model:
        white_worker_client = _start_white_worker(args.white_model)

    results = []
    black_wins = 0
    white_wins = 0
    active_history = []  # Precise singleton undo tracker
    sprt_result_data = None  # SPRT result if early stop triggered

    # Color-balanced tracking: candidate = black_model (model A)
    candidate_black_wins = 0   # candidate wins when playing black
    candidate_white_wins = 0   # candidate wins when playing white
    baseline_black_wins = 0    # baseline wins when playing black
    baseline_white_wins = 0    # baseline wins when playing white
    last_white_model = None    # track last white model to avoid unnecessary reloads

    try:
        for game_idx in range(args.games):
            # Release previous engine and get a fresh one for clean board state
            if game_idx > 0:
                dll.ReleaseEngine(env)
            env = dll.GetGameEngine()

            # Alternate colors: even games → candidate=black, odd games → baseline=black
            candidate_is_black = (game_idx % 2 == 0)
            if candidate_is_black:
                current_black_model = args.black_model  # candidate
                current_white_model = args.white_model  # baseline
                print(f"\n[Game {game_idx + 1}/{args.games}] Starting... (candidate=BLACK, baseline=WHITE)")
            else:
                current_black_model = args.white_model  # baseline
                current_white_model = args.black_model  # candidate
                print(f"\n[Game {game_idx + 1}/{args.games}] Starting... (baseline=BLACK, candidate=WHITE)")

            active_history.clear()

            # Load black model for this game
            if current_black_model:
                if load_kata_model is None:
                    print("  [ERROR] LoadKataModel function not found in DLL, cannot load black model", file=sys.stderr)
                    sys.exit(1)
                load_kata_model(env, current_black_model.encode("utf-8"), KATA_CONFIG_PATH.encode("utf-8"))

            # Reload white worker only when model changes
            if current_white_model and current_white_model != last_white_model:
                if white_worker_client is not None:
                    white_worker_client.close()
                white_worker_client = _start_white_worker(current_white_model)
                last_white_model = current_white_model

            # Reset board state for color symmetry (both sides start clean)
            if white_worker_client is not None:
                white_worker_client.reset_board()

            history = []
            winner = None
            current_role = BLACK
            three_asked = False
            five_asked = False
            five_candidates = []
            
            step_count = 0
            while winner is None and step_count < 225:
                # 1. Opening Book
                if len(history) < 5 and opening_book is not None:
                    res = opening_book.query([(h[0], h[1]) for h in history], style="hybrid")
                    if res is not None:
                        bx, by = res
                        dll.DoMove(env, bx, by, current_role)
                        history.append((bx, by, current_role))
                        active_history.append((bx, by, current_role))
                        print(f"  Step {len(history)} (Book): AI { 'BLACK' if current_role == BLACK else 'WHITE' } places at {(bx, by)}")
                        current_role = 1 - current_role
                        step_count += 1
                        continue

                # 2. Three-Hand Swap Rule Check
                if len(history) == 3 and not three_asked:
                    print("  [Three-Hand Swap] Evaluating swap decision...")
                    # Evaluate Black advantage
                    arr_b = (AIMove * 5)()
                    cnt_b = dll.GetTopMoves(env, BLACK, arr_b, 5)
                    score_black = arr_b[0].score if cnt_b > 0 else 0
                    
                    # Evaluate White advantage
                    arr_w = (AIMove * 5)()
                    cnt_w = dll.GetTopMoves(env, WHITE, arr_w, 5)
                    score_white = arr_w[0].score if cnt_w > 0 else 0
                    
                    three_asked = True
                    if score_black > score_white:
                        print(f"  [Three-Hand Swap] Swapping! BlackAdvantage ({score_black} > {score_white})")
                        dll.SwapHand(env, False)
                    else:
                        print(f"  [Three-Hand Swap] No swap. WhiteAdvantage ({score_white} >= {score_black})")
                    continue

                # 3. Five-Hand N-play Rule Check
                if len(history) == 4 and current_role == BLACK and not five_asked:
                    print("  [Five-Hand N-play] Selecting 3 candidate moves...")
                    arr = (AIMove * 15)()
                    cnt = dll.GetTopMoves(env, BLACK, arr, 15)
                    raw_candidates = [(m.x, m.y) for m in arr[:min(cnt, 9)]]
                    five_candidates = choose_low_impact_candidates_for_black(raw_candidates, arr, cnt, FIVE_MOVE_CANDIDATE_COUNT)
                    five_asked = True
                    
                    # White AI automatically selects the best candidate
                    chosen = select_best_candidate_for_white(env, five_candidates)
                    if chosen is not None:
                        dll.DoMove(env, chosen[0], chosen[1], BLACK)
                        history.append((chosen[0], chosen[1], BLACK))
                        active_history.append((chosen[0], chosen[1], BLACK))
                        print(f"  Step {len(history)} (Five-Hand N-play): WHITE AI filters candidates {five_candidates} -> chosen {(chosen[0], chosen[1])}")
                        current_role = WHITE
                        step_count += 1
                    continue

                # 4. Standard move search
                if current_role == BLACK:
                    # Built-in Black AI MCTS search
                    if set_kata_enabled is not None:
                        set_kata_enabled(env, True)
                        set_kata_search_params(env, args.visits_black, 0.0, 0.3, 0.3)
                    arr = (AIMove * 10)()
                    cnt = dll.GetTopMoves(env, BLACK, arr, 10)
                    if cnt > 0:
                        m = arr[0]
                        dll.DoMove(env, m.x, m.y, BLACK)
                        history.append((m.x, m.y, BLACK))
                        active_history.append((m.x, m.y, BLACK))
                        print(f"  Step {len(history)}: BLACK places at {(m.x, m.y)} (score={m.score})")
                        if dll.CheckWin(env, m.x, m.y, BLACK):
                            winner = BLACK
                        else:
                            current_role = WHITE
                    else:
                        print("  [Error] No legal moves for Black!")
                        break
                else:
                    # White AI Move
                    if args.white_model and white_worker_client is not None:
                        # WorkerClient White AI
                        resp = white_worker_client.query(history, args.visits_white, 0.3, 0.3, "MCTS", WHITE)
                        if resp.get("status") == "ok":
                            wx, wy, wscore = int(resp["x"]), int(resp["y"]), int(resp["score"])
                            dll.DoMove(env, wx, wy, WHITE)
                            history.append((wx, wy, WHITE))
                            active_history.append((wx, wy, WHITE))
                            print(f"  Step {len(history)}: WHITE (worker) places at {(wx, wy)} (score={wscore})")
                            if dll.CheckWin(env, wx, wy, WHITE):
                                winner = WHITE
                            else:
                                current_role = BLACK
                        elif resp.get("error") == "WORKER_CRASHED":
                            # Attempt to restart worker and retry once
                            print("  [Recovery] Worker crashed, restarting...")
                            white_worker_client.close()
                            white_worker_client = _start_white_worker(current_white_model)
                            if white_worker_client is not None:
                                white_worker_client.reset_board()
                                resp2 = white_worker_client.query(history, args.visits_white, 0.3, 0.3, "MCTS", WHITE)
                                if resp2.get("status") == "ok":
                                    wx, wy, wscore = int(resp2["x"]), int(resp2["y"]), int(resp2["score"])
                                    dll.DoMove(env, wx, wy, WHITE)
                                    history.append((wx, wy, WHITE))
                                    active_history.append((wx, wy, WHITE))
                                    print(f"  Step {len(history)}: WHITE (worker) places at {(wx, wy)} (score={wscore}) [recovered]")
                                    if dll.CheckWin(env, wx, wy, WHITE):
                                        winner = WHITE
                                    else:
                                        current_role = BLACK
                                else:
                                    print(f"  [Error] Worker still failing after restart: {resp2.get('error')}")
                                    break
                            else:
                                print("  [Error] Failed to restart worker")
                                break
                        else:
                            print(f"  [Error] White worker error: {resp.get('error')}")
                            break
                    else:
                        # Built-in White AI DLL MCTS search
                        if set_kata_enabled is not None:
                            set_kata_enabled(env, True)
                            set_kata_search_params(env, args.visits_white, 0.0, 0.3, 0.3)
                        arr = (AIMove * 10)()
                        cnt = dll.GetTopMoves(env, WHITE, arr, 10)
                        if cnt > 0:
                            m = arr[0]
                            dll.DoMove(env, m.x, m.y, WHITE)
                            history.append((m.x, m.y, WHITE))
                            active_history.append((m.x, m.y, WHITE))
                            print(f"  Step {len(history)}: WHITE places at {(m.x, m.y)} (score={m.score})")
                            if dll.CheckWin(env, m.x, m.y, WHITE):
                                winner = WHITE
                            else:
                                current_role = BLACK
                        else:
                            print("  [Error] No legal moves for White!")
                            break

                step_count += 1

            if winner == BLACK:
                black_wins += 1
                winner_str = "BLACK"
                if candidate_is_black:
                    candidate_black_wins += 1
                else:
                    baseline_black_wins += 1
            elif winner == WHITE:
                white_wins += 1
                winner_str = "WHITE"
                if candidate_is_black:
                    baseline_white_wins += 1
                else:
                    candidate_white_wins += 1
            else:
                winner_str = "DRAW"

            candidate_total = candidate_black_wins + candidate_white_wins
            baseline_total = baseline_black_wins + baseline_white_wins
            print(f"[Game {game_idx + 1}] Finished! Winner: {winner_str} in {len(history)} moves")
            print(f"  Score: candidate={candidate_total} baseline={baseline_total}")
            results.append({
                "game_id": game_idx + 1,
                "winner": winner_str,
                "candidate_is_black": candidate_is_black,
                "moves": len(history),
                "history": [(int(x), int(y), int(r)) for x, y, r in history]
            })

            # Early termination check
            if args.early_stop and game_idx >= args.min_games - 1:
                candidate_total = candidate_black_wins + candidate_white_wins
                baseline_total = baseline_black_wins + baseline_white_wins
                decision = _sprt_check(candidate_total, baseline_total,
                                       alpha=args.sprt_alpha, beta=args.sprt_beta,
                                       elo_diff=args.sprt_h1)
                if decision is not None:
                    sprt_result = compute_sprt_result(candidate_total, baseline_total,
                                                      alpha=args.sprt_alpha, beta=args.sprt_beta,
                                                      elo_diff=args.sprt_h1)
                    sprt_result_data = sprt_result.to_dict() if hasattr(sprt_result, 'to_dict') else {
                        "decision": sprt_result.decision, "winrate": sprt_result.winrate,
                        "wins": sprt_result.wins, "losses": sprt_result.losses, "total": sprt_result.total
                    }
                    print(f"\n[SPRT] Early termination after {game_idx + 1} games! Decision: {decision}")
                    print(f"  Candidate wins: {candidate_total} (as black: {candidate_black_wins}, as white: {candidate_white_wins})")
                    print(f"  Baseline wins:  {baseline_total} (as black: {baseline_black_wins}, as white: {baseline_white_wins})")
                    print(f"  Elo diff: {sprt_result.elo_diff:.1f} [{sprt_result.ci_lower:.1f}, {sprt_result.ci_upper:.1f}]")
                    break

    finally:
        # Standard cleanups for sub-processes
        if white_worker_client is not None:
            white_worker_client.close()
        dll.ReleaseEngine(env)

    # Save summary report
    total_played = len(results)
    candidate_total = candidate_black_wins + candidate_white_wins
    baseline_total = baseline_black_wins + baseline_white_wins
    report = {
        "summary": {
            "total_games": total_played,
            "black_wins": black_wins,
            "white_wins": white_wins,
            "draws": total_played - (black_wins + white_wins),
            "candidate_wins": candidate_total,
            "baseline_wins": baseline_total,
            "candidate_win_rate": float(candidate_total) / total_played if total_played > 0 else 0,
            "candidate_black_wins": candidate_black_wins,
            "candidate_white_wins": candidate_white_wins,
            "baseline_black_wins": baseline_black_wins,
            "baseline_white_wins": baseline_white_wins,
        },
        "games": results
    }

    # Add SPRT result if early stop was triggered
    if sprt_result_data is not None:
        report["sprt_result"] = sprt_result_data

    # Also compute final SPRT result if early stop was enabled but didn't trigger
    if args.early_stop and sprt_result_data is None and candidate_total + baseline_total > 0:
        final_sprt = compute_sprt_result(candidate_total, baseline_total,
                                         alpha=args.sprt_alpha, beta=args.sprt_beta,
                                         elo_diff=args.sprt_h1)
        report["sprt_result"] = final_sprt.to_dict() if hasattr(final_sprt, 'to_dict') else {
            "decision": final_sprt.decision, "winrate": final_sprt.winrate,
            "wins": final_sprt.wins, "losses": final_sprt.losses, "total": final_sprt.total
        }

    try:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("\n" + "=" * 60)
        print(f"Match report successfully saved to: {args.output}")
        print(f"Black Wins: {black_wins} | White Wins: {white_wins}")
        print("=" * 60)
    except Exception as e:
        print(f"[Error] Failed to write report: {e}")

if __name__ == "__main__":
    main()
