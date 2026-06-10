# machine-benchmark Proposal

## Context

今天 (2026-06-10) 连续遇到两个资源问题：

1. **WSL 崩溃**：sf_threads=32 导致 RAM 耗尽 (>7.7GB)，整个 VM 崩溃
2. **VRAM 估算偏差**：预估 b10c256nbt 训练需 5-7GB VRAM，实测仅 1.3GB

根因：没有系统化的机器资源基准数据。参数选择靠猜，踩了坑才知道上限。

## Goal

建立一套自动化的机器基准测试 + 运行时监控体系：

1. **Phase 1: 短基准测试** — 一次性扫描各阶段资源消耗，产出 machine_profile.json
2. **Phase 2: 被动监控** — 嵌入日常训练管线，持续采集退化数据

## Scope

### In Scope

- 自博弈 (selfplay) 资源扫描：sf_threads × sf_visits
- 训练 (train) 资源扫描：tr_batch × sh_samples
- PK 评估资源扫描：pk_visits
- 运行时监控层：step_time、GPU、RAM 采集
- machine_profile.json 产出

### Out of Scope

- 自动拒绝超出参数（改为建议，不阻断）
- 多模型跨架构测试（仅测当前目标 b10c256nbt）
- 硬件升级建议

## Success Criteria

| 指标 | 目标 |
|------|------|
| Phase 1 完成时间 | < 2 小时 |
| 产出 machine_profile.json | 包含 train/selfplay/pk 三阶段推荐参数 |
| 覆盖 sf_threads 安全边界 | 明确 RAM 不会 OOM 的最大线程数 |
| 被动监控零侵入 | 不改变现有管线行为，仅追加日志 |
| 后续训练自动读取 profile | DecisionEngine 输出建议参数 |

## Risk

- Phase 1 短测试可能遗漏长时间退化问题（靠 Phase 2 补）
- machine_profile 是当前硬件状态的快照，环境变化后需重测
