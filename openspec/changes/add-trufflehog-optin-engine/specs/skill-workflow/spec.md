# Spec Delta

## ADDED Requirements

### Requirement: 密钥深度检测提示

SKILL.md SHALL 指引 agent：在呈现密钥类（gitleaks/secrets 类别）发现时，可提示用户"可选择启用深度密钥检测（TruffleHog，含 800+ 检测器；默认不联网验证）"，经用户同意后以 `--engine trufflehog` 重扫。

#### Scenario: 提示深度检测

- **WHEN** 报告含密钥发现且用户询问能否查得更深
- **THEN** agent 说明可选启用 TruffleHog 深度层及其默认不联网验证的边界
