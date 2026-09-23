# Spec Delta

## ADDED Requirements

### Requirement: JS/TS 与 Java 场景触发

description MUST 额外覆盖 JS/TS 与 Java 项目场景（"检查一下 JS 代码"、"扫扫这个 Java 文件"等）。

#### Scenario: Java 项目触发

- **WHEN** 用户说"帮我扫一下这个 Java 文件"
- **THEN** 技能触发并按 SKILL.md 工作流执行（Java 引擎按需安装）

### Requirement: 编排指令升级为修复循环

SKILL.md 编排 SHALL 升级为完整修复循环（见 fix-loop 能力）：修复范围选项、合理性判断、≤3 轮重扫验证、误报登记、不自动 commit。

#### Scenario: 修复循环演练

- **WHEN** 用户在选项中选择"全部修复"
- **THEN** agent 按修复循环工作流执行并在收敛后给出三类汇总
