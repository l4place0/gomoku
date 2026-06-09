## ADDED Requirements

### Requirement: CLI 单入口与子命令
系统 SHALL 提供 `mlevo` 作为唯一 CLI 入口。所有功能 SHALL 通过子命令暴露（`status`, `run`, `branch`, `merge`, `pk`, `graph`, `models`, `model`, `migrate`, `recover`, `test`, `schema`）。每个子命令 SHALL 支持 `--help` 输出用法说明。

#### Scenario: 查看可用命令
- **WHEN** 用户执行 `mlevo schema --json`
- **THEN** 返回所有子命令列表，每个包含名称、参数、描述

#### Scenario: 子命令帮助
- **WHEN** 用户执行 `mlevo run --help`
- **THEN** 输出 run 子命令的所有参数和用法说明

### Requirement: 结构化 JSON 输出
所有子命令 SHALL 支持 `--json` 参数。使用 `--json` 时，输出 SHALL 是合法 JSON，exit code 0 表示成功，非 0 表示失败。

#### Scenario: 正常 JSON 输出
- **WHEN** 用户执行 `mlevo status --json`
- **THEN** 输出合法 JSON，包含 pipeline_state、current_round、current_model 等字段

#### Scenario: 错误 JSON 输出
- **WHEN** 执行失败（如从 running 状态再次 run）
- **THEN** 输出 `{"error": "...", "code": "STATE_CONFLICT"}`，exit code 非 0

### Requirement: 状态机管控
CLI SHALL 维护 `pipeline_state` 状态机，状态 SHALL 为 `idle`、`running`、`paused`、`crashed` 之一。状态转换 SHALL 通过 CLI 子命令触发，非法转换 SHALL 被拒绝。

#### Scenario: 正常状态转换
- **WHEN** 状态为 idle 时执行 `mlevo run --round 1`
- **THEN** 状态变为 running，训练开始

#### Scenario: 非法转换拒绝
- **WHEN** 状态为 running 时执行 `mlevo run --round 2`
- **THEN** 返回错误 `{"error": "already running", "code": "STATE_CONFLICT"}`，exit code 非 0

#### Scenario: 崩溃恢复
- **WHEN** 状态为 crashed 时执行 `mlevo recover --json`
- **THEN** 状态变为 idle，返回恢复策略（如 "rerun round N"）

### Requirement: Preset 参数梯度
系统 SHALL 支持 `--preset tiny|small|full` 参数。tiny 模式 SHALL 使用最小参数（sf_games=5, sf_visits=8, sh_samples=100, pk_games=4）执行完整训练流程，耗时 SHALL 不超过 60 秒。small 模式 SHALL 使用中等参数（sf_games=50, sf_visits=32, sh_samples=1000, pk_games=10）。full 模式 SHALL 使用训练计划中的完整参数。

#### Scenario: tiny preset 执行完整流程
- **WHEN** 用户执行 `mlevo run --round 1 --preset tiny --json`
- **THEN** 系统走完 selfplay→shuffle→train→export→pk 全流程，30 秒内返回结果，输出包含 winrate 和 promoted 字段

#### Scenario: preset 覆盖训练计划参数
- **WHEN** 同时指定 `--preset tiny` 和训练计划中的参数
- **THEN** preset 参数优先，训练计划参数被覆盖

### Requirement: 训练进度查询
系统 SHALL 支持 `mlevo progress --json` 查询当前训练进度。输出 SHALL 包含 stage（当前阶段）、pct（完成百分比）、eta（预计剩余时间）。

#### Scenario: 训练中查询进度
- **WHEN** 状态为 running 时执行 `mlevo progress --json`
- **THEN** 返回 `{"stage": "selfplay", "pct": 45, "eta": "12m"}`

#### Scenario: 非训练状态查询进度
- **WHEN** 状态为 idle 时执行 `mlevo progress --json`
- **THEN** 返回 `{"stage": null, "pct": 0, "eta": null}`

### Requirement: 崩溃恢复策略
系统 SHALL 支持保守恢复策略：训练崩溃时标记 round 为 failed，`mlevo recover` SHALL 提供重跑整个 round 的选项。系统 SHALL 记录崩溃原因（OOM、NaN、进程异常退出）。

#### Scenario: 训练 OOM 崩溃恢复
- **WHEN** 训练因 OOM 崩溃
- **THEN** 状态变为 crashed，`mlevo recover --json` 返回 `{"action": "rerun", "round": N, "reason": "OOM"}`

#### Scenario: 从崩溃恢复并继续
- **WHEN** 用户执行 `mlevo recover --json`
- **THEN** 状态变为 idle，可重新执行 `mlevo run`
