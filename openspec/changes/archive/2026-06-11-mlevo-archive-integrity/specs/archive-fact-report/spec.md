## ADDED Requirements

### Requirement: 从 PK 日志提取游戏结果
`mlevo report` SHALL 解析 `round_*_pk.log` 文件，提取每局的胜负结果、完成局数、计划局数。SHALL 统计 BLACK/WHITE/DRAW 的分布。SHALL 输出 JSON 格式的结构化事实。

#### Scenario: 正常 PK 日志解析
- **WHEN** PK 日志包含 50 局计划，实际完成 50 局
- **THEN** 输出 `completed_games: 50`, `planned_games: 50`, 以及 BLACK/WHITE/DRAW 各自的胜局数

#### Scenario: PK 日志不完整
- **WHEN** PK 日志包含 50 局计划，但只有 18 局有 Finished 标记
- **THEN** 输出 `completed_games: 18`, `planned_games: 50`, 并标记 `verdict: "INVALID"`

### Requirement: 检测 IPC 通信失败
`mlevo report` SHALL 扫描 PK 日志中的 `IPC failed` 出现次数。SHALL 将 IPC 失败次数作为 PK 有效性的判定依据。

#### Scenario: 日志中有 IPC 失败
- **WHEN** PK 日志中 `IPC failed` 出现次数 > 0
- **THEN** 该轮 PK 的 verdict 标记为 `"INVALID"`，并在 anomalies 中记录 IPC 失败次数

#### Scenario: 日志中无 IPC 失败
- **WHEN** PK 日志中无 `IPC failed`
- **THEN** IPC 失败计数为 0，不影响 verdict 判定

### Requirement: 检测 VCF solver 初始化错误
`mlevo report` SHALL 扫描 PK 日志中的 `zob_board not init` 出现次数。

#### Scenario: VCF solver 未初始化
- **WHEN** PK 日志中 `zob_board not init` 出现次数 > 0
- **THEN** 在 anomalies 中记录 VCF 错误次数

### Requirement: 检测颜色偏差
`mlevo report` SHALL 统计 PK 日志中 BLACK 和 WHITE 各自的胜率。SHALL 当单方胜率超过 70% 时标记颜色偏差。

#### Scenario: 严重的颜色偏差
- **WHEN** WHITE 胜率 > 70% 或 BLACK 胜率 > 70%
- **THEN** 该轮 PK 的 verdict 标记为 `"DEGRADED"`，并在 anomalies 中记录颜色偏差百分比

#### Scenario: 颜色分布正常
- **WHEN** BLACK 和 WHITE 胜率均在 30%-70% 之间
- **THEN** 颜色偏差不影响 verdict 判定

### Requirement: 从训练日志提取指标
`mlevo report` SHALL 解析 `round_*_train.log` 文件，提取 vloss、pacc1、p0loss 指标。SHALL 提取最后一个 epoch 的验证值。

#### Scenario: 训练日志正常
- **WHEN** 训练日志包含 validation 结果
- **THEN** 输出 `vloss`、`pacc1`、`p0loss` 的具体数值

#### Scenario: 训练日志缺失
- **WHEN** 对应轮次的训练日志不存在
- **THEN** training 字段标记为 `"MISSING"`，不使用默认值

### Requirement: Ledger 一致性检查
`mlevo report` SHALL 对比 PK 日志中的实际游戏结果与 `evolution_ledger.json` 中的记录。SHALL 检查 winrate、wins_new、losses_new 是否匹配。

#### Scenario: Ledger 与日志一致
- **WHEN** ledger 中的 wins_new + losses_new + draws 等于日志中的完成局数，且 winrate 计算正确
- **THEN** `ledger_match: true`

#### Scenario: Ledger 与日志不一致
- **WHEN** ledger 记录 0/0 但日志有实际游戏结果
- **THEN** `ledger_match: false`，`mismatch_detail` 描述具体差异

### Requirement: 输出格式
`mlevo report` SHALL 输出 JSON 格式，包含 rounds 数组和 anomalies 数组。SHALL 支持 `--json` 参数。SHALL 支持指定计划名称或目录路径。

#### Scenario: 指定计划名称
- **WHEN** 执行 `mlevo report b10c256nbt-validation --json`
- **THEN** 从 `docs/ml/plans/archive/` 或 `docs/ml/plans/` 中查找对应目录，输出该计划的完整 facts.json

#### Scenario: 计划不存在
- **WHEN** 指定的计划名称不存在
- **THEN** 输出错误信息，退出码非零
