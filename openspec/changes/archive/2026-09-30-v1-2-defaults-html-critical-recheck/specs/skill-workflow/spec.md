# Spec Delta

## ADDED Requirements

### Requirement: critical 级发现 AI 复审

当报告含 critical 级发现时，agent SHALL 在呈现修复选项前对每条 critical 逐条复审：读取问题行及上下文，给出结论（确认 / 疑似误报 / 需人工判断）与一句话依据；摘要中按结论标注；疑似误报默认不进入修复范围（用户可推翻）。major 及以下不强制复审。

#### Scenario: critical 复审后呈现

- **WHEN** 报告含 2 条 critical
- **THEN** agent 呈现的摘要中每条 critical 带复审结论，且在修复选项中如实反映
