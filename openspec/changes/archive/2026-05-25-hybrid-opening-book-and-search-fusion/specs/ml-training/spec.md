## ADDED Requirements

### Requirement: 动态 Visits 与残局自适应降级
系统 SHALL 支持根据落子手数量（步数）动态调节神经网络 MCTS 的 Visits 参数。在对局早期，系统 SHALL 提供高 Visits（例如 `128`）以进行宏大和深远的局势思考；随着棋盘局势深入或战术冲突上升，系统 SHALL 自动将 Visits 降低（例如 `64` 或 `32`），并在进入绝对算杀期（例如检测到活三/冲四，或步数大于 18 步）时将 Visits 彻底降为 `0`（完全关停神经网络推理，100% 将算力倾注于 MiniMax 精确算杀）。

#### Scenario: 战术冲突时神经网络自动降级
- **WHEN** 局面上检测到对手有活三或冲四威胁，且 Visits 当前为 64
- **THEN** 系统 SHALL 自动调用 `dll.SetKataSearchParams` 将 visits 设置为 `0`，停用网络推理，完全交由 MiniMax 算杀

---

### Requirement: 基于步数的动态融合公式
在进行神经网络估分与 Alpha-Beta 搜索得分融合时，系统 SHALL 舍弃以往固定的融合参数，改为根据落子步数 $t$ 动态调整混合权重 $W_{\text{Kata}}(t)$ 和 $W_{\text{AB}}(t)$：
- **前 6 手**：$W_{\text{Kata}} = 1.0, W_{\text{AB}} = 0.0$（完全信任神经网络/开局库，0 运行 AB 搜索）。
- **第 7 - 16 手**：$W_{\text{Kata}} = 0.6, W_{\text{AB}} = 0.4$（战略布局主导，AB搜索战术校验）。
- **第 16 手之后**：$W_{\text{Kata}} = 0.2, W_{\text{AB}} = 0.8$（AB搜索绝对主导，神经网络辅助大局）。

#### Scenario: 中盘布局期平滑过渡
- **WHEN** 当前局势处于第 10 手落子
- **THEN** 系统 SHALL 采用 $W_{\text{Kata}} = 0.6$ 和 $W_{\text{AB}} = 0.4$ 对二者进行加权融合

---

### Requirement: 自对弈训练管线与开局库自进化对接
在 `training_ui.py` 或后台自对弈训练阶段，系统 SHALL 开启“高分定式挖掘器”。当某一盘自对弈变例在深度 MCTS 搜索下，特定开局（落子数 $\le 8$）的 visits 达到阈值（$\ge 800$）且胜率极为优异（黑棋 $>65\%$ 或白棋 $>53\%$）时，系统 SHALL 自动捕获该走法，归一化后写入开局数据库，完成库的自成长。

#### Scenario: 训练管线发现高分定式并入库
- **WHEN** 训练自对弈产生一局棋，第 4 手白棋的 visits 为 1000 且白棋最终评估胜率为 55%
- **THEN** 系统 SHALL 将此局面坐标经过 8 路归一化后，以 `AI_NOVELTY` 标签自动追加入库
