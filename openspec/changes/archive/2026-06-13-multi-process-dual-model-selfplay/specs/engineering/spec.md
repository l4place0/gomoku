## ADDED Requirements

### Requirement: 对决控制台多模型路径文件选择 UI
在双 AI 对决控制台中，系统 SHALL 为黑白两方 AI 分别渲染“模型权重文件选择卡片”。卡片包含当前已载入的模型路径显示文本，以及一个 `[ 浏览模型 ]` 按钮。点击按钮后，系统 SHALL 弹出系统文件选择窗允许用户选择 `.bin.gz` 模型路径，并更新至对应 AI 状态属性中。

#### Scenario: 浏览并选择新模型路径
- **WHEN** 玩家点击白方 AI 卡片中的“浏览模型”按钮并成功选择 `models/custom.bin.gz`
- **THEN** 卡片上的显示路径文本实时渲染更新，并同步至 `gs.ai_white_cfg["model_path"]` 中。
