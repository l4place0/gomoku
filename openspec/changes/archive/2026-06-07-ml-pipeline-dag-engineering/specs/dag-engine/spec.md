## ADDED Requirements

### Requirement: DAG 节点定义
DAG 中的每个节点 SHALL 对应 `model_registry.jsonl` 中的一个模型记录。节点 SHALL 包含 hash（唯一标识）、parent（父节点指针）、branch（所属分支）。

#### Scenario: 创建新节点
- **WHEN** 一轮训练完成并注册模型
- **THEN** DAG 中新增一个节点，parent 指向训练所基于的模型

#### Scenario: 节点唯一性
- **WHEN** 两次注册相同 hash 的模型
- **THEN** 系统拒绝重复注册，DAG 中不产生重复节点

### Requirement: DAG 边与 OpenSpec 关联
DAG 中的每条边 SHALL 对应一次训练决策，关联一个 OpenSpec change。边 SHALL 记录 from（父模型 hash）、to（子模型 hash）、change（OpenSpec change 名）、hypothesis（实验假设）、param_diff（参数变化）。

#### Scenario: 训练时创建边
- **WHEN** 执行 `mlevo run --round N --change "my-change" --json`
- **THEN** 训练完成后自动创建一条边，记录 change 名和参数 diff

#### Scenario: 查询边信息
- **WHEN** 用户执行 `mlevo graph --with-edges --json`
- **THEN** 返回包含 nodes 和 edges 的完整图结构

### Requirement: 无环校验
系统 SHALL 在每次写入 parent 关系时校验 DAG 无环性。如果设置 parent 会导致环，系统 SHALL 拒绝操作。

#### Scenario: 检测并拒绝环
- **WHEN** 尝试将 model_A 的 parent 设置为 model_B，而 model_B 的后代链中已包含 model_A
- **THEN** 操作失败，返回错误信息 "cycle detected: A→...→B→A"

### Requirement: 分支创建
系统 SHALL 支持从任意历史模型创建分支。分支 SHALL 自动命名（格式：`branch-{YYYYMMDD}-{param_slug}`）。新分支的第一个模型的 parent SHALL 指向分叉点模型。

#### Scenario: 从历史模型分叉
- **WHEN** 用户执行 `mlevo branch --from a1b2c3 --json`
- **THEN** 系统创建新分支，返回分支名和分叉点模型 hash

#### Scenario: 在分支上训练
- **WHEN** 用户执行 `mlevo run --round 1 --branch exp-lr --json`
- **THEN** 训练基于该分支的最新模型进行，新模型 branch 字段为 "exp-lr"

### Requirement: 锦标赛合并
系统 SHALL 支持两个分支的 PK 对决。PK 赢家 SHALL 成为或继续作为 mainline，输家 SHALL 被标记为 archived。

#### Scenario: 分支与 mainline 对决
- **WHEN** 用户执行 `mlevo pk --branch-a mainline --branch-b exp-lr --games 50 --json`
- **THEN** 返回 PK 结果（winner、winrate、games_played）

#### Scenario: 合并到 mainline
- **WHEN** 用户执行 `mlevo merge --winner exp-lr --json`
- **THEN** exp-lr 的最新模型成为新 mainline，原 mainline 的后续模型保留为历史

### Requirement: 拓扑排序
系统 SHALL 支持对 DAG 进行拓扑排序，返回按依赖顺序排列的模型列表。

#### Scenario: 获取训练顺序
- **WHEN** 用户执行 `mlevo graph --topo --json`
- **THEN** 返回按拓扑排序的模型列表，每个模型出现在其 parent 之后
