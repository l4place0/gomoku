## ADDED Requirements

### Requirement: SPRT 统计检验判定
系统 SHALL 实现 Sequential Probability Ratio Test (SPRT) 作为模型晋升的判定机制，替代当前的纯阈值判定。SPRT SHALL 在对弈过程中持续计算似然比，当达到接受或拒绝边界时提前终止。

#### Scenario: SPRT 接受晋升
- **WHEN** 对弈过程中 SPRT 似然比达到上界（接受 H1）
- **THEN** 系统提前终止对弈，标记该模型为晋升候选

#### Scenario: SPRT 拒绝晋升
- **WHEN** 对弈过程中 SPRT 似然比达到下界（接受 H0）
- **THEN** 系统提前终止对弈，标记该模型为拒绝

#### Scenario: SPRT 未达边界
- **WHEN** 对弈完成所有预定局数后 SPRT 似然比仍在上下界之间
- **THEN** 系统按最终胜率和阈值判定（回退到纯阈值判定）

### Requirement: SPRT 参数可配置
系统 SHALL 支持通过 CLI 参数配置 SPRT 的 H0 假设、H1 假设、显著性水平（alpha）和功效（beta）。SHALL 提供合理默认值。

#### Scenario: 使用默认 SPRT 参数
- **WHEN** 用户未指定 SPRT 参数
- **THEN** 系统使用默认值：H0=0 Elo, H1=35 Elo, alpha=0.05, beta=0.05

#### Scenario: 自定义 SPRT 参数
- **WHEN** 用户通过 `--sprt-h1 50 --sprt-alpha 0.01` 指定参数
- **THEN** 系统使用用户指定的参数进行 SPRT 判定

### Requirement: 最小局数下限
系统 SHALL 设置最小对弈局数下限（默认 20 局），在达到下限前不做 SPRT early stop。

#### Scenario: 未达最小局数
- **WHEN** 对弈局数 < 最小局数下限
- **THEN** 系统继续对弈，不触发 SPRT early stop

#### Scenario: 达到最小局数
- **WHEN** 对弈局数 >= 最小局数下限且 SPRT 似然比达到边界
- **THEN** 系统触发 early stop

### Requirement: SPRT 结果包含统计指标
SPRT 结果 SHALL 包含：最终胜率、置信区间（95% CI）、Elo 差异估计、SPRT 似然比、决策结果（accept/reject/undecided）。

#### Scenario: 查看 SPRT 结果
- **WHEN** PK 对弈完成
- **THEN** 输出 JSON 包含 winrate, ci_lower, ci_upper, elo_diff, llr, decision 字段

### Requirement: Elo 差异估计
系统 SHALL 基于最终胜率计算 Elo 差异估计和 95% 置信区间。

#### Scenario: 胜率 60% 的 Elo 估计
- **WHEN** 模型在 PK 中取得 60% 胜率
- **THEN** 系统输出 Elo 差异约 70，95% CI 约 [30, 110]
