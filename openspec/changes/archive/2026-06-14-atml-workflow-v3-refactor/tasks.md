# Tasks: ATML Workflow v3 Refactor

## 1. 重命名
- [x] 1.1 重命名 .claude/skills/mlevo-* → atml-*
- [x] 1.2 更新所有 SKILL.md 的 name: frontmatter
- [x] 1.3 删除 .agent/skills/mlevo-* v1.0 过时文件

## 2. Explore v3
- [x] 2.1 重写 atml-explore SKILL.md：交互式三阶段
- [x] 2.2 定义数据源清单（docs/ml/ + ml/data/）
- [x] 2.3 定义 insights.json 输出格式

## 3. Propose v3
- [x] 3.1 重写 atml-propose SKILL.md：单脚手架 docs/ml/changes/
- [x] 3.2 定义 proposal/design/tasks/training_plan.json 四文件结构

## 4. Apply v3
- [x] 4.1 重写 atml-apply SKILL.md：auto 模式
- [x] 4.2 定义 guardrail warning → 确认逻辑

## 5. Archive v4
- [x] 5.1 重写 atml-archive SKILL.md：自适应路径
- [x] 5.2 定义快速路径（≤2 轮全 VALID）和完整路径（3 Agents）

## 6. CLI 路径迁移
- [x] 6.1 mlevo_cli.py 新增 CHANGES_DIR 常量
- [x] 6.2 更新 get_plan_dir、find_plan、cmd_new、cmd_list、cmd_report
- [x] 6.3 创建 docs/ml/changes/ 和 archive/ 目录
- [x] 6.4 验证 cmd_new、cmd_list、cmd_archive 路径正确

## 7. Spec 迁移
- [x] 7.1 迁移 openspec/specs/atml-skills/ → docs/ml/specs/atml-skills/
- [x] 7.2 重写 spec.md 覆盖 v3/v4 所有新设计

## 8. 测试适配
- [x] 8.1 更新 test_mlevo.py：CHANGES_DIR 替代 PLANS_DIR

## 9. 验证
- [x] 9.1 python3 验证 CHANGES_DIR/ARCHIVE_DIR 路径正确
- [x] 9.2 python3 验证 cmd_new 在 docs/ml/changes/ 下创建
- [x] 9.3 python3 验证 cmd_archive 归档到 docs/ml/changes/archive/
- [x] 9.4 确认 openspec/ 下无 atml 残留（archive 除外）
