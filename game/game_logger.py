"""
game_logger.py — 统一结构化日志模块

写入目标：logs/game_records.jsonl（每行一个 JSON 事件）

事件类型：
  game_start       每局开始，记录角色分配
  move             每次落子（AI 落子含 search_id 关联字段）
  phase_transition 状态机阶段流转
  swap             三手交换决策（含双向评分）
  five_n           五手N打候选与选择
  undo             悔棋操作
  game_end         对局结束（正常胜负或关窗口 quit）
"""

import os
import json
import datetime


class GameLogger:
    """结构化对局日志器。

    每个游戏实例创建一个 GameLogger，整个生命周期（含跨局）共享同一
    JSONL 文件（追加写入）。game_id 字段区分不同局。
    """

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, "game_records.jsonl")
        self.game_id: str | None = None
        self._game_ended = False  # 防止 session_end 重复写 game_end

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _ts(self) -> str:
        return datetime.datetime.now().isoformat()

    def _write(self, record: dict):
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            print(f"[GameLogger] 写入失败: {exc}")

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def game_start(self, human_color: str, ai_color: str):
        """每局开始调用一次，生成新 game_id。

        Args:
            human_color: "black" 或 "white"
            ai_color:    "white" 或 "black"
        """
        self.game_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._game_ended = False
        record = {
            "type": "game_start",
            "game_id": self.game_id,
            "human_color": human_color,
            "ai_color": ai_color,
            "timestamp": self._ts(),
        }
        self._write(record)
        print(f"[GameLogger] 新对局: game_id={self.game_id} 人类执{human_color}")

    def move(
        self,
        move_num: int,
        x: int,
        y: int,
        role: str,
        player: str,
        phase: str = "NORMAL",
        search_id: int | None = None,
        **kwargs,
    ):
        """记录一次真实落子。

        Args:
            move_num:  落子序号（= len(history) after append）
            x, y:     落子坐标
            role:      "black" 或 "white"
            player:    "human" 或 "ai"
            phase:     当前 GamePhase 名称（字符串）
            search_id: AI 落子时关联 search_logs.jsonl 的 searchId
            **kwargs:  其他任意结构化元数据
        """
        if self.game_id is None:
            return
        record: dict = {
            "type": "move",
            "game_id": self.game_id,
            "move_num": move_num,
            "x": x,
            "y": y,
            "role": role,
            "player": player,
            "phase": phase,
            "timestamp": self._ts(),
        }
        if search_id is not None:
            record["search_id"] = search_id
        record.update(kwargs)
        self._write(record)

    def phase_transition(self, from_phase: str, to_phase: str, data: dict | None = None):
        """记录状态机阶段转移。

        Args:
            from_phase: 转出阶段名称
            to_phase:   转入阶段名称
            data:       额外上下文（可选），如评分、换手结果等
        """
        if self.game_id is None:
            return
        record: dict = {
            "type": "phase_transition",
            "game_id": self.game_id,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "timestamp": self._ts(),
        }
        if data:
            record["data"] = data
        self._write(record)

    def swap(
        self,
        decision: str,
        score_black: int,
        score_white: int,
        by: str,
    ):
        """记录三手交换决策。

        Args:
            decision:    "swap" 或 "no_swap"
            score_black: AI 评估执黑的最佳分
            score_white: AI 评估执白的最佳分
            by:          决策方 "human" 或 "ai"
        """
        if self.game_id is None:
            return
        record = {
            "type": "swap",
            "game_id": self.game_id,
            "decision": decision,
            "score_black": score_black,
            "score_white": score_white,
            "by": by,
            "timestamp": self._ts(),
        }
        self._write(record)
        print(
            f"[GameLogger] 三手交换: by={by} decision={decision} "
            f"score_black={score_black} score_white={score_white}"
        )

    def five_n(
        self,
        candidates: list,
        chosen: tuple | None,
        by: str,
    ):
        """记录五手N打事件。

        Args:
            candidates: 候选位置列表 [(x,y), ...]
            chosen:     最终落子位置 (x, y) 或 None（未完成）
            by:         "human"（人类选择保留）或 "ai"（AI 选择保留）
        """
        if self.game_id is None:
            return
        record = {
            "type": "five_n",
            "game_id": self.game_id,
            "candidates": [list(c) for c in candidates],
            "chosen": list(chosen) if chosen else None,
            "by": by,
            "timestamp": self._ts(),
        }
        self._write(record)

    def undo(self, from_move_num: int, to_move_num: int):
        """记录悔棋操作。

        Args:
            from_move_num: 悔棋前手数
            to_move_num:   悔棋后手数
        """
        if self.game_id is None:
            return
        record = {
            "type": "undo",
            "game_id": self.game_id,
            "from_move_num": from_move_num,
            "to_move_num": to_move_num,
            "timestamp": self._ts(),
        }
        self._write(record)
        print(f"[GameLogger] 悔棋: {from_move_num} → {to_move_num} 手")

    def game_end(self, winner: str | None, total_moves: int, reason: str = "normal"):
        """记录对局结束。

        Args:
            winner:      "black"、"white" 或 None（未分胜负/quit）
            total_moves: 总手数
            reason:      "normal"（正常胜负）或 "quit"（关窗口）
        """
        if self.game_id is None:
            return
        record = {
            "type": "game_end",
            "game_id": self.game_id,
            "winner": winner,
            "total_moves": total_moves,
            "reason": reason,
            "timestamp": self._ts(),
        }
        self._write(record)
        self._game_ended = True
        print(
            f"[GameLogger] 对局结束: game_id={self.game_id} "
            f"winner={winner} moves={total_moves} reason={reason}"
        )

    def session_end(self, total_moves: int):
        """程序退出时调用（pygame.quit 前）。

        若当前局尚未记录 game_end，则补写 reason='quit' 的结束事件，
        防止对局数据丢失。

        Args:
            total_moves: 当前手数（供补写 game_end 使用）
        """
        if self.game_id is not None and not self._game_ended:
            self.game_end(winner=None, total_moves=total_moves, reason="quit")
