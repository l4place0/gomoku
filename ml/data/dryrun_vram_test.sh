#!/bin/bash
# Dry-run VRAM test for b10c256nbt on GTX 1650 Ti
set -e

PROJECT_ROOT="/home/l4p/gomoku"
TRAIN_PY="$PROJECT_ROOT/KataGomo/python/train.py"
DATA_DIR="$PROJECT_ROOT/ml/data/training_data/shuffleddata/current"
EXPORT_DIR="/tmp/dryrun_export"
TRAIN_DIR="/tmp/dryrun_train"

# WSL2 CUDA libs
export LD_LIBRARY_PATH="/usr/lib/wsl/lib:$LD_LIBRARY_PATH"
CUDNN_LIB="$PROJECT_ROOT/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib"
[ -d "$CUDNN_LIB" ] && export LD_LIBRARY_PATH="$CUDNN_LIB:$LD_LIBRARY_PATH"

PYTHON="$PROJECT_ROOT/.venv/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON=python3

BATCH_SIZES="${1:-32 16 8}"

for BS in $BATCH_SIZES; do
    echo "============================================"
    echo "Testing b10c256nbt with batch_size=$BS"
    echo "============================================"

    rm -rf "$EXPORT_DIR" "$TRAIN_DIR"
    mkdir -p "$EXPORT_DIR" "$TRAIN_DIR"

    # Run training in background
    $PYTHON "$TRAIN_PY" \
        -traindir "$TRAIN_DIR" \
        -datadir "$DATA_DIR" \
        -exportdir "$EXPORT_DIR" \
        -exportprefix dryrun \
        -pos-len 15 \
        -batch-size "$BS" \
        -model-kind b10c256nbt \
        -max-epochs-this-instance 1 \
        -samples-per-epoch 200 \
        -swa-scale 1.0 \
        -lookahead-alpha 0.5 \
        -lookahead-k 6 \
        > "/tmp/dryrun_b${BS}.log" 2>&1 &
    PID=$!

    # Monitor VRAM for up to 120 seconds
    PEAK_VRAM=0
    for i in $(seq 1 60); do
        sleep 2
        if ! kill -0 $PID 2>/dev/null; then
            break
        fi
        VRAM=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -1)
        if [ -n "$VRAM" ] && [ "$VRAM" -gt "$PEAK_VRAM" ]; then
            PEAK_VRAM=$VRAM
        fi
    done

    # Wait for process to finish (or kill after timeout)
    if kill -0 $PID 2>/dev/null; then
        kill $PID 2>/dev/null
        wait $PID 2>/dev/null
        TIMEOUT=" (killed after timeout)"
    else
        wait $PID 2>/dev/null
        TIMEOUT=""
    fi

    # Check for OOM or errors
    if grep -qi "out of memory\|CUDA error\|RuntimeError" "/tmp/dryrun_b${BS}.log" 2>/dev/null; then
        STATUS="OOM/ERROR"
    elif grep -q "Hit max epochs" "/tmp/dryrun_b${BS}.log" 2>/dev/null; then
        STATUS="OK"
    else
        STATUS="UNKNOWN"
    fi

    echo "batch_size=$BS | peak_vram=${PEAK_VRAM}MB | status=$STATUS$TIMEOUT"
    echo ""

    # If OOM, skip smaller batches (they'll fail too? no, smaller = less VRAM)
    # Continue to test smaller batches
done

# Cleanup
rm -rf "$EXPORT_DIR" "$TRAIN_DIR"
echo "Done."
