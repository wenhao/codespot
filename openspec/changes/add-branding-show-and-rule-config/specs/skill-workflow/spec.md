# Spec Delta

## MODIFIED Requirements

### Requirement: 编排指令升级为修复循环

SKILL.md 修复选项 SHALL 增加"先查看问题详情"：agent 以 `codespot show` 分批呈现详情（按严重级/文件分组，含 CS 编号）后，重新呈现修复选项；呈现给用户的文案 MUST NOT 出现底层引擎名，涉及规则时只用 CS 编号；引擎名仅允许出现在 agent 内部决策（读 report.json）中。

#### Scenario: 先看详情再决策

- **WHEN** 用户选择"先查看问题详情"
- **THEN** agent 用 show 呈现详情后重新给出修复选项

#### Scenario: 修复循环演练

- **WHEN** 用户在选项中选择"全部修复"
- **THEN** agent 按修复循环工作流执行并在收敛后给出三类汇总
