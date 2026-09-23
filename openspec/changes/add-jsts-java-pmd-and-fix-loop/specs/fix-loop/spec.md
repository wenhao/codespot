# Spec Delta

## ADDED Requirements

### Requirement: 修复循环编排

SKILL.md SHALL 定义修复循环：① agent 按用户选择的范围（仅 critical / major 及以上 / 全部 / 自定义）逐条处理 issue；② 修复前 MUST 判断合理性，疑似误报（测试代码、示例占位符）跳过并说明；③ 每轮修复后对受影响文件重扫验证；④ 轮次上限 3 轮；⑤ 结束时汇总已修复 / 跳过 / 剩余三类计数；⑥ 全程不自动 commit。

#### Scenario: 三轮内收敛

- **WHEN** 用户选择修复全部且夹具有 5 条可修复 issue
- **THEN** agent 在 ≤3 轮重扫内使对应 issue 清零并给出汇总

### Requirement: 误报登记指引

对确认的误报，SKILL.md SHALL 指引 agent 将其写入 `.codespot/ignore`（`{"tool","file","rule"}`）或 gitleaks 的 `.gitleaksignore`，并在下一轮扫描中生效（不再出现）。

#### Scenario: 登记后不再报告

- **WHEN** agent 将某条 ruff 误报写入 .codespot/ignore 并重扫
- **THEN** 该条从报告中消失
