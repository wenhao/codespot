# Spec Delta

## ADDED Requirements

### Requirement: 依赖漏洞场景触发

description SHALL 覆盖依赖/供应链场景（"查一下依赖有没有漏洞"、"依赖安全检查"等）。

#### Scenario: 依赖检查触发

- **WHEN** 用户说"帮我看看 requirements 里的依赖有没有漏洞"
- **THEN** 技能触发并按 SKILL.md 工作流执行（依赖引擎按需安装）
