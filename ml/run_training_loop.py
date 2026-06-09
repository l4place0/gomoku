#!/usr/bin/env python3
"""run_training_loop.py — Automate multi-round Gomoku training loop.

Drives `mlevo_cli.py run` for rounds 1..N, tracks progress via the ledger,
and stops on early-stopping conditions (target winrate, consecutive failures).
Resumable: re-run to pick up where the last completed round left off.
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PLAN_NAME = "gomoku-gtx1650ti"
LEDGER_PATH = BASE_DIR / "data" / "logs" / "evolution_ledger.json"
PLAN_FILE = PROJECT_ROOT / "docs" / "ml" / "plans" / PLAN_NAME / "training_plan.json"
LOOP_STATE_PATH = BASE_DIR / "data" / "logs" / "loop_state.json"

MAX_CONSECUTIVE_FAILURES = 3


def load_json(path):
    if path.exists():
        try:
            if path.stat().st_size > 50 * 1024 * 1024:
                print(f"Warning: {path} exceeds 50MB, skipping", file=sys.stderr)
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_plan():
    plan = load_json(PLAN_FILE)
    if not plan:
        print(f"Error: Plan file not found at {PLAN_FILE}", file=sys.stderr)
        sys.exit(1)
    return plan


def get_completed_rounds():
    """Return set of completed round numbers from the ledger."""
    ledger = load_json(LEDGER_PATH) or []
    return {r.get("round") for r in ledger if r.get("round")}


def get_last_round_result(round_no):
    """Get the PK result for a specific round from the ledger."""
    ledger = load_json(LEDGER_PATH) or []
    for r in reversed(ledger):
        if r.get("round") == round_no:
            return r.get("pk", {})
    return None


def run_round(round_no):
    """Execute one training round via mlevo_cli.py. Returns True on success."""
    cmd = [
        sys.executable, str(BASE_DIR / "mlevo_cli.py"),
        "run",
        "--plan", PLAN_NAME,
        "--round", str(round_no),
    ]
    print(f"\n{'='*72}")
    print(f"  STARTING ROUND {round_no}")
    print(f"{'='*72}")
    print(f"Command: {' '.join(cmd)}\n", flush=True)

    start = time.time()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="ignore", bufsize=1,
        )
        for line in proc.stdout:
            print(line, end="", flush=True)
        proc.wait()
        elapsed = time.time() - start

        if proc.returncode != 0:
            print(f"\nRound {round_no} FAILED with exit code {proc.returncode} "
                  f"(elapsed: {elapsed/60:.1f}m)", file=sys.stderr)
            return False

        print(f"\nRound {round_no} completed in {elapsed/60:.1f}m", flush=True)
        return True

    except Exception as e:
        print(f"\nRound {round_no} ERROR: {e}", file=sys.stderr)
        return False


def check_early_stop(plan, round_no):
    """Check if early stopping conditions are met. Returns (should_stop, reason)."""
    early = plan.get("early_stopping", {})
    target_wr = early.get("target_winrate", 0.85)

    pk = get_last_round_result(round_no)
    if pk and pk.get("winrate", 0) >= target_wr:
        return True, f"Target winrate {target_wr:.0%} reached (got {pk['winrate']:.2%})"

    return False, None


def main():
    plan = load_plan()
    total_rounds = plan.get("total_rounds", 10)
    completed = get_completed_rounds()

    print(f"Plan: {plan.get('plan_name', PLAN_NAME)}")
    print(f"Total rounds: {total_rounds}")
    print(f"Completed rounds: {sorted(completed)}")
    print(f"Promotion threshold: {plan.get('promotion_threshold', 0.55)}")

    # Find next round to run
    next_round = 1
    for r in range(1, total_rounds + 1):
        if r not in completed:
            next_round = r
            break
    else:
        print(f"\nAll {total_rounds} rounds already completed!")
        return

    print(f"Next round: {next_round}")
    print(f"Rounds remaining: {total_rounds - next_round + 1}")

    consecutive_failures = 0

    for r in range(next_round, total_rounds + 1):
        success = run_round(r)

        if success:
            consecutive_failures = 0
            # Check early stopping
            should_stop, reason = check_early_stop(plan, r)
            if should_stop:
                print(f"\n*** EARLY STOP: {reason} ***")
                break
        else:
            consecutive_failures += 1
            print(f"\nConsecutive failures: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}")
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                print(f"Too many consecutive failures. Stopping loop.", file=sys.stderr)
                sys.exit(1)

        # Brief cooldown between rounds
        if r < total_rounds:
            print(f"\nWaiting 5s before next round...\n")
            time.sleep(5)

    # Final summary
    completed = get_completed_rounds()
    print(f"\n{'='*72}")
    print(f"  TRAINING LOOP COMPLETE")
    print(f"{'='*72}")
    print(f"Completed rounds: {sorted(completed)}")

    # Print round-by-round summary
    ledger = load_json(LEDGER_PATH) or []
    print(f"\n{'Round':<6} {'Winrate':<10} {'Promoted':<10}")
    print("-" * 28)
    for entry in sorted(ledger, key=lambda e: e.get("round", 0)):
        r = entry.get("round", "?")
        pk = entry.get("pk", {})
        wr = pk.get("winrate", 0)
        promoted = "YES" if pk.get("promoted") else "NO"
        print(f"{r:<6} {wr:<10.2%} {promoted:<10}")


if __name__ == "__main__":
    main()
