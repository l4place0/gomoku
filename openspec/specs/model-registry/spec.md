## ADDED Requirements

### Requirement: 模型注册表持久化
系统 SHALL 维护 `model_registry.jsonl` 文件作为模型版本注册表。每行 SHALL 是一个合法 JSON 对象，记录单个模型的完整元数据。系统 SHALL 以 append-only 方式写入，不修改已有行。

#### Scenario: 注册新模型
- **WHEN** 一轮训练完成且模型导出成功
- **THEN** 系统在 `model_registry.jsonl` 末尾追加一行 JSON，包含 hash、parent、round、winrate、promoted、params、change、timestamp、file 字段

#### Scenario: 重启后注册表完整
- **WHEN** 系统重启并读取 `model_registry.jsonl`
- **THEN** 所有历史记录完整无损，可正确构建模型图谱

### Requirement: 模型 hash 寻址
每个模型 SHALL 有唯一 hash 标识符。hash SHALL 由模型文件内容计算得出（SHA256 前 12 位 hex）。模型文件 SHALL 按 hash 归档存储于 `models/{hash}.bin.gz`。

#### Scenario: 相同内容产生相同 hash
- **WHEN** 两次导出产生相同的模型文件
- **THEN** 两次注册的 hash 值相同

#### Scenario: 按 hash 检索模型
- **WHEN** 用户执行 `mlevo model --hash a1b2c3 --json`
- **THEN** 系统返回该模型的完整元数据记录

### Requirement: parent 关系维护
每个模型（除初始模型外）SHALL 有且仅有一个 parent 字段，指向其训练所基于的父模型 hash。parent 关系 SHALL 构成有向无环图。

#### Scenario: 正常训练的 parent 设置
- **WHEN** 从 model_A 开始训练一轮并晋升
- **THEN** 新模型的 parent 字段值为 model_A 的 hash

#### Scenario: 失败轮次的 parent 设置
- **WHEN** 从 model_A 训练但未晋升（winrate < 阈值）
- **THEN** 新模型的 parent 字段值仍为 model_A 的 hash（失败模型也记录，不丢弃）

#### Scenario: 环检测
- **WHEN** 设置 parent 时形成环（A→B→C→A）
- **THEN** 系统拒绝写入并返回错误

### Requirement: 模型检索与过滤
系统 SHALL 支持按 hash、branch、promoted 状态、winrate 范围检索模型。

#### Scenario: 按 branch 过滤
- **WHEN** 用户执行 `mlevo models --branch mainline --json`
- **THEN** 系统返回 mainline 分支的所有模型列表

#### Scenario: 按 winrate 过滤
- **WHEN** 用户执行 `mlevo models --min-winrate 0.7 --json`
- **THEN** 系统返回 winrate ≥ 0.7 的所有模型

### Requirement: 历史数据迁移
系统 SHALL 支持从现有 `evolution_ledger.json` 迁移历史数据到 `model_registry.jsonl`。迁移 SHALL 自动推导 parent 关系：promoted 模型成为 mainline 下一轮的 parent，failed 模型继承上一个 promoted 的 parent。

#### Scenario: 迁移 10 轮历史数据
- **WHEN** 用户执行 `mlevo migrate --from-ledger --json`
- **THEN** 系统生成 10 条 registry 记录，parent 链正确反映晋升/失败关系，输出迁移报告

---

## MODIFIED Requirements

### Requirement: 模型注册表持久化
系统 SHALL 维护 `model_registry.jsonl` 文件作为模型版本注册表。每行 SHALL 是一个合法 JSON 对象，记录单个模型的完整元数据。系统 SHALL 以 append-only 方式写入，不修改已有行。

#### Scenario: 注册新模型
- **WHEN** 一轮训练完成且模型导出成功
- **THEN** 系统在 `model_registry.jsonl` 末尾追加一行 JSON，包含 hash、parent、round、winrate、promoted、params、change、timestamp、file 字段

#### Scenario: 重启后注册表完整
- **WHEN** 系统重启并读取 `model_registry.jsonl`
- **THEN** 所有历史记录完整无损，可正确构建模型图谱

#### Scenario: 注册包含 SPRT 结果的模型
- **WHEN** 一轮训练完成且 PK 使用 SPRT 评估
- **THEN** 注册记录的 params 字段 SHALL 包含 tr_lr 字段，新增 sprt_result 字段包含 decision、llr、elo_diff、ci_lower、ci_upper
