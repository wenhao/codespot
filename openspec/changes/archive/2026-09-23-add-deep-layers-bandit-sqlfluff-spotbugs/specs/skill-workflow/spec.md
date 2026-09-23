# Spec Delta

## ADDED Requirements

### Requirement: SQL 场景触发

description SHALL 额外覆盖 SQL 场景（"扫一下这几个 SQL 文件"、"检查 SQL 规范"等）。

#### Scenario: SQL 项目触发

- **WHEN** 用户说"帮我检查一下迁移目录里的 SQL"
- **THEN** 技能触发，SQL 引擎按需安装并扫描
