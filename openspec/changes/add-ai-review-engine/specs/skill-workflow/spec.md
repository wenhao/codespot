# Spec Delta

## ADDED Requirements

### Requirement: AI 审查工作流

SKILL.md SHALL 定义 AI 审查三步工作流：① `codespot scan --engine ai` 生成审查计划；② agent 读取 `.codespot/ai-plan.json`，逐文件分析（聚焦计划中的审查重点、跳过静态工具已覆盖的规则类问题、每条发现给出精确 file:line 与依据），按 schema 写 `.codespot/ai-result.json`（含 confidence）；③ `codespot ai-scan absorb` 合并后呈现报告。触发场景包括"用 AI 再查一遍"、"深度审查这段代码"。

#### Scenario: 三步闭环

- **WHEN** 用户要求 AI 深度审查
- **THEN** agent 按三步工作流执行并在 absorb 后呈现合并报告（AI 发现附 confidence）
