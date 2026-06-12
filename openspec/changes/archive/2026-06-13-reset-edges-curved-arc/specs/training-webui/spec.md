## MODIFIED Requirements

### Requirement: 模型进化图谱视图
WebUI SHALL 提供 DAG 图谱可视化页面。图谱 SHALL 显示模型节点（hash、winrate、promoted 状态）和边（change 名、hypothesis、param_diff）。节点 SHALL 使用颜色区分 promoted（绿色）和 failed（灰色）。边 SHALL 可点击查看 proposal 详情。
当检测到 backward 边（源节点的 round 大于目标节点的 round）时，系统 SHALL 将其绘制为在节点上方或下方弯曲的弧线，并使用虚线等特定的视觉样式（代表“重置/回滚”边），以防止与前向边重叠。

#### Scenario: 渲染完整图谱
- **WHEN** 用户打开图谱页面
- **THEN** 显示所有模型节点和边，mainline 和分支清晰可区分，且 backward 边以虚线和弯曲弧线的形式呈现。

#### Scenario: 点击节点查看详情
- **WHEN** 用户点击一个模型节点
- **THEN** 弹出详情面板，显示 hash、parent、winrate、params、关联 change

#### Scenario: 点击边查看 proposal
- **WHEN** 用户点击一条边
- **THEN** 弹出详情面板，显示 change 名、hypothesis、param_diff、结果
