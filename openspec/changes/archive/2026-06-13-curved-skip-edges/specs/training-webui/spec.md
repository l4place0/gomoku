## MODIFIED Requirements

### Requirement: 模型进化图谱视图
WebUI SHALL 提供 DAG 图谱可视化页面。图谱 SHALL 显示模型节点（hash、winrate、promoted 状态）和边（change 名、hypothesis、param_diff）。节点 SHALL 使用颜色区分 promoted（绿色）和 failed（灰色）。边 SHALL 可点击查看 proposal 详情。为了避免视觉重叠，跳过一轮及以上的前向边（即 |to.round - from.round| > 1） SHALL 被绘制为在节点上方拱起且高度与跳过轮数成正比的二次贝塞尔曲线，而相邻轮次的边（round diff = 1） SHALL 保持直线。所有边的点击交互和标签定位 SHALL 在曲线或直线上正常工作。

#### Scenario: 渲染完整图谱
- **WHEN** 用户打开图谱页面
- **THEN** 显示所有模型节点和边，相邻边为直线，跳过轮数的边为向上的曲线，且高度与跳过轮数成正比，mainline 和分支清晰可区分

#### Scenario: 点击节点查看详情
- **WHEN** 用户点击一个模型节点
- **THEN** 弹出详情面板，显示 hash、parent、winrate、params、关联 change

#### Scenario: 点击边查看 proposal
- **WHEN** 用户点击一条边（无论是直线还是曲线）
- **THEN** 弹出详情面板，显示 change 名、hypothesis、param_diff、结果
