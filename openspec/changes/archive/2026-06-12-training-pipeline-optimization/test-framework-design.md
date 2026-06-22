# 训练流水线测试框架设计

## 1. 问题

automl_cli.py 的 main() 函数是 300+ 行的单体函数，所有阶段（selfplay/shuffle/train/export/pk）的逻辑混在一起。无法单独测试某个阶段，也无法在没有 GPU 的环境下测试。

## 2. 目标

- 将每个阶段提取为独立的可测试函数
- 用 mock 替代 subprocess 调用（不需要真实 GPU）
- 测试串行和并行两种模式
- 测试错误恢复和边界情况

## 3. 架构

```
当前:
  main() ─── selfplay ─── shuffle ─── train ─── export ─── pk
  (300+ 行单体函数)

重构后:
  run_pipeline(args, serial=True)
    ├── run_selfplay(args) → Result
    ├── run_shuffle(args) → Result
    ├── run_train(args) → Result
    ├── run_export(args) → Result
    └── run_pk(args) → Result

  run_pipeline(args, serial=False)
    ├── start_shuffle_service(args) → BackgroundService
    ├── start_export_service(args) → BackgroundService
    ├── run_selfplay(args) → Result          # 并行
    ├── run_train(args) → Result             # 并行
    ├── stop_services()
    └── run_pk(args) → Result
```

## 4. 提取的函数签名

```python
@dataclass
class StageResult:
    success: bool
    duration: float
    log_file: Path
    error: str = ""

def run_selfplay(args, data_dir, logs_dir, round_no) -> StageResult:
    """执行自博弈阶段。"""

def run_shuffle(args, data_dir, logs_dir, round_no) -> StageResult:
    """执行数据混洗阶段。"""

def run_train(args, data_dir, logs_dir, round_no) -> StageResult:
    """执行训练阶段。"""

def run_export(args, data_dir, logs_dir, round_no) -> StageResult:
    """执行模型导出阶段。"""

def run_pk(args, data_dir, logs_dir, round_no) -> StageResult:
    """执行 PK 评测阶段。"""

def run_pipeline(args, serial=True) -> Dict[str, StageResult]:
    """执行完整流水线。serial=True 串行，serial=False 并行。"""
```

## 5. 测试分类

### 5.1 单元测试（不需要 GPU）

```python
# test_pipeline_stages.py

class TestStageResult:
    """测试 StageResult 数据类。"""

class TestRunSelfplay:
    """测试 selfplay 阶段逻辑。"""
    def test_selfplay_calls_engine_with_correct_args(self, mock_subprocess):
        """验证 selfplay 命令行参数正确。"""

    def test_selfplay_handles_engine_not_found(self, mock_subprocess):
        """引擎不存在时使用 mock 模式。"""

    def test_selfplay_records_metrics(self, mock_subprocess):
        """验证 StageMetrics 被正确调用。"""

class TestRunShuffle:
    """测试 shuffle 阶段逻辑。"""
    def test_shuffle_clears_old_dirs(self, mock_subprocess):
        """验证旧目录被清理。"""

    def test_shuffle_creates_tmp_dirs(self, mock_subprocess):
        """验证临时目录被创建。"""

    def test_shuffle_self_healing_val(self, mock_subprocess):
        """验证 val 数据为空时自动复制 train 数据。"""

class TestRunTrain:
    """测试 train 阶段逻辑。"""
    def test_train_passes_fp16_flag(self, mock_subprocess):
        """验证 --tr-fp16 参数正确传递。"""

    def test_train_handles_nan_loss(self, mock_subprocess):
        """验证 NaN loss 时的错误处理。"""

class TestRunExport:
    """测试 export 阶段逻辑。"""
    def test_export_finds_latest_checkpoint(self, tmp_path):
        """验证 checkpoint 查找逻辑。"""

    def test_export_gzip_compression(self, tmp_path):
        """验证 gzip 压缩。"""

class TestRunPk:
    """测试 PK 阶段逻辑。"""
    def test_pk_records_results(self, mock_subprocess):
        """验证 PK 结果被正确记录。"""

    def test_pk_handles_worker_crash(self, mock_subprocess):
        """验证 worker 崩溃时的错误处理。"""
```

### 5.2 集成测试（需要 mock pipeline）

```python
# test_pipeline_integration.py

class TestSerialPipeline:
    """测试串行流水线。"""
    def test_pipeline_runs_all_stages(self, mock_pipeline):
        """验证所有阶段按顺序执行。"""

    def test_pipeline_stops_on_selfplay_failure(self, mock_pipeline):
        """验证 selfplay 失败时后续阶段不执行。"""

    def test_pipeline_records_progress(self, mock_pipeline):
        """验证 progress.json 被正确更新。"""

class TestParallelPipeline:
    """测试并行流水线。"""
    def test_parallel_selfplay_and_train(self, mock_pipeline):
        """验证 selfplay 和 train 并行执行。"""

    def test_parallel_shuffle_runs_in_background(self, mock_pipeline):
        """验证 shuffle 在后台运行。"""

    def test_parallel_stops_on_crash(self, mock_pipeline):
        """验证进程崩溃时正确清理。"""

class TestBackgroundService:
    """测试后台服务。"""
    def test_service_starts_and_stops(self):
        """验证服务启动和停止。"""

    def test_service_auto_restarts_on_crash(self):
        """验证服务崩溃后自动重启。"""

    def test_service_respects_stop_signal(self):
        """验证停止信号被正确处理。"""
```

### 5.3 回归测试

```python
# test_pipeline_regression.py

class TestRegression:
    """回归测试：确保重构不改变行为。"""
    def test_serial_output_matches_before_refactor(self):
        """验证串行模式输出与重构前一致。"""

    def test_ledger_format_unchanged(self):
        """验证 ledger 格式不变。"""

    def test_log_file_format_unchanged(self):
        """验证日志文件格式不变。"""
```

## 6. Mock 策略

### 6.1 Mock subprocess

```python
@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run 和 subprocess.Popen。"""
    calls = []

    def mock_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    def mock_popen(cmd, **kwargs):
        proc = MagicMock()
        proc.wait.return_value = 0
        proc.returncode = 0
        proc.stdout = []
        calls.append(cmd)
        return proc

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.setattr(subprocess, "Popen", mock_popen)
    return calls
```

### 6.2 Mock 数据目录

```python
@pytest.fixture
def data_dir(tmp_path):
    """创建测试用数据目录结构。"""
    d = tmp_path / "data"
    for subdir in ["selfplay", "models", "shuffleddata/current/train",
                   "shuffleddata/current/val", "torchmodels_toexport",
                   "models_exported", "shuffle_tmp/train", "shuffle_tmp/val",
                   "train/b10c256nbt"]:
        (d / subdir).mkdir(parents=True, exist_ok=True)
    return d
```

### 6.3 Mock args

```python
@pytest.fixture
def args(data_dir):
    """创建测试用 args 对象。"""
    class Args:
        round = 1
        model_name = "b10c256nbt"
        gpu = 0
        data_dir = str(data_dir)
        sf_games = 10
        sf_visits = 8
        sf_threads = 2
        sh_threads = 2
        sh_samples = 100
        tr_kind = "b10c256nbt"
        tr_batch = 16
        tr_lr = 0.002
        tr_epochs = 1
        tr_fp16 = False
        # ... 其他参数
    return Args()
```

## 7. 实施顺序

1. **Phase 1**: 提取函数（不改变行为）
   - 从 main() 提取 run_selfplay()
   - 从 main() 提取 run_shuffle()
   - 从 main() 提取 run_train()
   - 从 main() 提取 run_export()
   - 从 main() 提取 run_pk()
   - 保持 main() 调用这些函数（串行模式不变）

2. **Phase 2**: 添加测试
   - 为每个提取的函数添加单元测试
   - 为 pipeline 集成添加测试
   - 为 BackgroundService 添加测试

3. **Phase 3**: 实现并行模式
   - 添加 run_pipeline(serial=False) 逻辑
   - 实现 shuffle/export 后台服务
   - 添加 --serial 参数

4. **Phase 4**: 验证
   - 运行所有测试
   - 对比重构前后的输出
   - 合并到 dev 分支

## 8. 测试文件结构

```
tests/ml/
├── test_automl.py              # 现有测试（保留）
├── test_pipeline_stages.py     # 新增：阶段单元测试
├── test_pipeline_integration.py # 新增：流水线集成测试
├── test_background_service.py  # 新增：后台服务测试
└── test_pipeline_regression.py # 新增：回归测试
```
