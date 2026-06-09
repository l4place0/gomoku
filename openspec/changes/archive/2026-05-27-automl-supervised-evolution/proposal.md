## Why

为了解决当前机器学习（ML）自对弈和模型训练管线完全依赖手动操作、参数难复现、训练日志冗长杂乱以及缺乏自动化模型PK晋升机制的问题，系统需要一套高度自动化、参数透明且具备完整证据链记录的机器学习进化管线。

## What Changes

- **自动化演化编排命令行 (automl_cli.py)**：实现一套全新的命令行工具，包裹底层的自对弈、混洗、训练、导出和PK阶段。
- **精炼日志与完整证据链归档**：CLI 只输出格式整齐的高精炼阶段总结日志，底层子进程的海量详细日志重定向至按轮数和阶段分类归档的文件（如 `logs/round_N_{stage}.log`）。
- **同步的参数化控制接口**：CLI 暴露与底层训练管线严格同步的命令行参数，由 Agent 或用户动态拼接调用，在每一轮启动时首先打印无争议的参数配置清单以实现 100% 实验复现。
- **自动化模型 PK 机制**：集成并调用 `headless_runner.py`，实现平衡的黑白双方双模型对抗，依据设定的胜率阈值（默认 55%）自动决定是否晋升、替换主模型并触发开局库自进化对接。
- **配套的 AutoML 监督进化 Skill**：在当前工作空间 `.agent/skills/` 下制作专属的智能调参 Skill 配置文件，指导 Agent 进行自主参数拼接、异常熔断和自愈动作。

## Capabilities

### New Capabilities
- `automl-supervised-evolution`: 提供无人值守、具备完整实验证据链归档与自动模型 PK 晋升机制的自动化五子棋模型迭代进化管道，及配套的 Agent 监督调参 Skill。

### Modified Capabilities
- `ml-training`: 支持与 AutoML 进化管线同步的命令行动态参数化传参与配置。

## Impact

- **新增文件**：`automl_cli.py` (CLI 编排工具), `.agent/skills/automl-supervised-evolution/SKILL.md` (配套 Agent 监督 Skill)。
- **运行依赖**：依靠已有的 `headless_runner.py` 进行 PK；使用 `uv` 依赖管理和 PyTorch 进行后端有监督训练。
- **日志存储**：所有运行详情以 `logs/round_{round}_{stage}.log` 格式归档；高层指标数据账本保存至 `logs/evolution_ledger.json`。
