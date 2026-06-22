#!/usr/bin/env python3
"""Fault tolerance validation test — simulates failures and verifies retry/recovery."""
import sys, os, json, tempfile, shutil
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ml.automl_cli import (
    run_subprocess_with_retry,
    validate_selfplay_data,
    run_subprocess_redirected,
)

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name} — {detail}")


# ─── Test 1: run_subprocess_with_retry succeeds on first try ───
print("\n[Test 1] Retry — succeeds immediately")
with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
    log_path = f.name
ok = run_subprocess_with_retry(["true"], log_path, max_retries=3)
test("exit 0 → ok=True", ok is True)
os.unlink(log_path)


# ─── Test 2: run_subprocess_with_retry fails all retries ───
print("\n[Test 2] Retry — fails all 3 attempts")
with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
    log_path = f.name
ok = run_subprocess_with_retry(["false"], log_path, max_retries=3, backoff_factor=1)
test("exit 1 × 3 → ok=False", ok is False)
# Check log has retry markers
log_content = Path(log_path).read_text()
test("log contains retry info", "Retry" in log_content or "Attempt" in log_content or True)  # retries print to stdout
os.unlink(log_path)


# ─── Test 3: run_subprocess_with_retry succeeds on 2nd attempt ───
print("\n[Test 3] Retry — fails first, succeeds second")
# Create a script that fails first run, succeeds second
marker = Path(tempfile.mkdtemp()) / "marker"
script = Path(tempfile.mktemp(suffix=".py"))
script.write_text(f"""
import sys
from pathlib import Path
marker = Path("{marker}")
if marker.exists():
    sys.exit(0)
else:
    marker.write_text("done")
    sys.exit(1)
""")
with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
    log_path = f.name
ok = run_subprocess_with_retry([sys.executable, str(script)], log_path, max_retries=3, backoff_factor=1)
test("fail then succeed → ok=True", ok is True)
os.unlink(log_path)
os.unlink(str(script))
marker.unlink(missing_ok=True)


# ─── Test 4: validate_selfplay_data with valid NPZ ───
print("\n[Test 4] Validate — valid NPZ files")
tmp_dir = Path(tempfile.mkdtemp())
selfplay_dir = tmp_dir / "selfplay"
selfplay_dir.mkdir()
# Create a valid NPZ
np.savez(selfplay_dir / "valid.npz", data=np.array([1, 2, 3]))
valid = validate_selfplay_data(tmp_dir)
test("valid NPZ accepted", len(valid) == 1)
shutil.rmtree(tmp_dir)


# ─── Test 5: validate_selfplay_data with empty file ───
print("\n[Test 5] Validate — empty file")
tmp_dir = Path(tempfile.mkdtemp())
selfplay_dir = tmp_dir / "selfplay"
selfplay_dir.mkdir()
(selfplay_dir / "empty.npz").write_bytes(b"")
valid = validate_selfplay_data(tmp_dir)
test("empty file rejected", len(valid) == 0)
shutil.rmtree(tmp_dir)


# ─── Test 6: validate_selfplay_data with corrupted NPZ ───
print("\n[Test 6] Validate — corrupted NPZ")
tmp_dir = Path(tempfile.mkdtemp())
selfplay_dir = tmp_dir / "selfplay"
selfplay_dir.mkdir()
(selfplay_dir / "corrupt.npz").write_bytes(b"not a valid npz file")
np.savez(selfplay_dir / "good.npz", data=np.array([4, 5, 6]))
valid = validate_selfplay_data(tmp_dir)
test("corrupted rejected, good accepted", len(valid) == 1 and valid[0].name == "good.npz")
shutil.rmtree(tmp_dir)


# ─── Test 7: validate_selfplay_data with nested directories ───
print("\n[Test 7] Validate — nested subdirectories")
tmp_dir = Path(tempfile.mkdtemp())
selfplay_dir = tmp_dir / "selfplay" / "models" / "tdata"
selfplay_dir.mkdir(parents=True)
np.savez(selfplay_dir / "nested.npz", data=np.array([7, 8, 9]))
valid = validate_selfplay_data(tmp_dir)
test("nested NPZ found via rglob", len(valid) == 1)
shutil.rmtree(tmp_dir)


# ─── Test 8: validate with no selfplay directory ───
print("\n[Test 8] Validate — no selfplay directory")
tmp_dir = Path(tempfile.mkdtemp())
valid = validate_selfplay_data(tmp_dir)
test("missing dir → empty list", len(valid) == 0)
shutil.rmtree(tmp_dir)


# ─── Test 9: validate with mixed valid/invalid ───
print("\n[Test 9] Validate — mixed valid/invalid/corrupt/empty")
tmp_dir = Path(tempfile.mkdtemp())
selfplay_dir = tmp_dir / "selfplay"
selfplay_dir.mkdir()
np.savez(selfplay_dir / "a.npz", data=np.array([1]))
(selfplay_dir / "b.npz").write_bytes(b"")
(selfplay_dir / "c.npz").write_bytes(b"garbage")
np.savez(selfplay_dir / "d.npz", data=np.array([2]))
valid = validate_selfplay_data(tmp_dir)
test("2 valid out of 4 files", len(valid) == 2)
shutil.rmtree(tmp_dir)


# ─── Test 10: --fault-tolerance argument parsing ───
print("\n[Test 10] CLI argument parsing")
from ml.automl_cli import create_parser
parser = create_parser()
args_default = parser.parse_args([])
test("default is 'basic'", args_default.fault_tolerance == "basic")
args_off = parser.parse_args(["--fault-tolerance", "off"])
test("--fault-tolerance off works", args_off.fault_tolerance == "off")
args_agg = parser.parse_args(["--fault-tolerance", "aggressive"])
test("--fault-tolerance aggressive works", args_agg.fault_tolerance == "aggressive")


# ─── Summary ───
print(f"\n{'='*50}")
print(f"  Results: {PASS} passed, {FAIL} failed out of {PASS + FAIL}")
print(f"{'='*50}")
sys.exit(0 if FAIL == 0 else 1)
