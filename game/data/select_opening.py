#!/usr/bin/env python3
"""select_opening.py — Randomly select an opening seed and write to selfplay config.

Usage: python3 select_opening.py [--seeds opening_seeds.json] [--cfg native_selfplay_15.cfg]
"""

import json
import random
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SEEDS = BASE_DIR / "opening_seeds.json"
DEFAULT_CFG = BASE_DIR / "training_data" / "native_selfplay_15.cfg"


def load_seeds(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("openings", [])


def select_random_opening(seeds: list[dict]) -> list[str]:
    return random.choice(seeds)["moves"]


def write_initial_moves(cfg_path: Path, moves: list[str]) -> None:
    """Write initialMoves to selfplay config. Preserves all other settings."""
    lines = cfg_path.read_text(encoding="utf-8").splitlines()

    # Remove existing initialMoves line if present
    lines = [l for l in lines if not l.strip().startswith("initialMoves")]

    # Add new initialMoves
    moves_str = ",".join(moves)
    lines.append(f"initialMoves = {moves_str}")

    cfg_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    seeds_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEEDS
    cfg_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CFG

    seeds = load_seeds(seeds_path)
    if not seeds:
        print("Error: No opening seeds found", file=sys.stderr)
        sys.exit(1)

    moves = select_random_opening(seeds)
    write_initial_moves(cfg_path, moves)

    print(json.dumps({
        "selected": moves,
        "moves_str": ",".join(moves),
        "cfg": str(cfg_path),
        "total_seeds": len(seeds),
    }))


if __name__ == "__main__":
    main()
