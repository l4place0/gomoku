## Why

Gomoku ML 训练控制台的前端 UI 较为简陋，缺乏交互友好性。具体而言：页面布局和配色有待提升；Dashboard 缺少直观的最近 PK 结果展示；Graph 页面节点存在重叠风险；Models 页面缺乏可视化；并且在加载过程中缺少平滑的过渡效果（Loading Skeleton）与响应式适配。

## What Changes

- **UI 整体优化**：改进整体配色方案、字号、间距与排版，提升视觉专业度。
- **Dashboard 增强**：在 Dashboard 页面新增“最近一轮 PK 结果”的卡片展示，包含胜率、推广状态等信息。
- **Graph 布局优化**：改进 DAG 图谱节点的位置算法，防止节点重叠，使结构更加清晰易读。
- **Models 可视化**：在 Models 页面中嵌入 Winrate 的柱状图可视化，直观对比不同模型的胜率。
- **加载状态优化**：为各个页面引入 Loading Skeleton 骨架屏效果，改善等待体验。
- **响应式布局改进**：优化移动端/不同分辨率屏幕下的侧边栏与内容区域的排版适配。

## Capabilities

### New Capabilities
<!-- 无新增 spec，仅修改现有 spec -->

### Modified Capabilities
- `training-webui`: 修改仪表板视图、模型进化图谱视图以及模型列表的展示要求，增加 PK 卡片、节点布局算法、柱状图可视化、骨架屏和响应式要求。

## Impact

影响以下前端组件与页面：
- `webui/frontend/src/index.css` & `App.css` (全局样式、配色、响应式、骨架屏)
- `webui/frontend/src/pages/Dashboard.jsx` (PK 结果卡片、骨架屏)
- `webui/frontend/src/pages/Graph.jsx` (节点布局算法)
- `webui/frontend/src/pages/Models.jsx` (Winrate 柱状图)
- `webui/frontend/src/pages/Logs.jsx` (响应式与骨架屏)
