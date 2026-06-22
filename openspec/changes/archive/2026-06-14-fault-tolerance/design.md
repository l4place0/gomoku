# Design: Multi-Tier Fault Tolerance

## 当前失败点分析

| 阶段 | 失败模式 | 当前行为 |
|------|----------|----------|
| selfplay | 进程崩溃/OOM/超时 | `StageResult(False)` → 整轮失败 |
| shuffle | NPZ 损坏/空目录 | 警告但继续 |
| train | NaN/OOM/crash | NaN 有检测，其他直接失败 |
| export | checkpoint 缺失 | 直接失败 |
| PK | worker 进程崩溃 | `StageResult(False)` |
| pipeline | parallel 模式失败 | 已有 fallback to serial |

## 设计方案

### Layer 1: 进程级重试

在 `run_subprocess_redirected()` 中添加重试逻辑：

```python
def run_subprocess_with_retry(cmd, log_path, max_retries=3, backoff_factor=2, env=None):
    for attempt in range(max_retries):
        ok = run_subprocess_redirected(cmd, log_path, env=env)
        if ok:
            return True
        if attempt < max_retries - 1:
            wait = backoff_factor ** attempt
            print(f"  [Retry] Attempt {attempt+1}/{max_retries} failed, retrying in {wait}s...")
            time.sleep(wait)
    return False
```

应用范围：
- `run_selfplay()` — 替换 `run_subprocess_redirected` 为 `run_subprocess_with_retry`
- `run_train()` — 同上

### Layer 2: 检查点恢复

train.py 已支持从 checkpoint 恢复（通过 `-resume` 参数或自动检测 traindir 下的 checkpoint）。关键改动：

- train 崩溃后，检查 `traindir` 下是否有 `checkpoint*.ckpt`
- 如果有，下次 train 自动从该 checkpoint 恢复（train.py 已原生支持）
- 如果没有（checkpoint 也被损坏），则从头训练

### Layer 3: 数据完整性验证

在 `run_shuffle()` 前验证 selfplay 数据：

```python
def validate_selfplay_data(data_dir):
    selfplay_dir = data_dir / "selfplay"
    npz_files = list(selfplay_dir.rglob("*.npz"))
    valid = []
    for f in npz_files:
        if f.stat().st_size == 0:
            print(f"  [Validate] Skipping empty file: {f}")
            continue
        try:
            # Quick check: can numpy open it?
            import numpy as np
            np.load(f, allow_pickle=False)
            valid.append(f)
        except Exception as e:
            print(f"  [Validate] Corrupted file: {f} ({e})")
    return valid
```

### Layer 4: 管线级容错

`run_pipeline()` parallel 模式已有 fallback to serial。增强：

- serial 模式下，如果某个阶段失败但有可恢复状态（如 checkpoint 存在），尝试恢复而非直接失败
- 添加 `--fault-tolerance` 参数控制容错级别（off / basic / aggressive）

### 代码改动点

1. `ml/automl_cli.py` — 新增 `run_subprocess_with_retry()` 函数
2. `ml/automl_cli.py` — `run_selfplay()` 使用重试逻辑
3. `ml/automl_cli.py` — `run_train()` 使用重试逻辑 + 检查点恢复检测
4. `ml/automl_cli.py` — 新增 `validate_selfplay_data()` 函数
5. `ml/automl_cli.py` — `run_shuffle()` 前调用验证
6. `ml/automl_cli.py create_parser()` — 添加 `--fault-tolerance` 参数
