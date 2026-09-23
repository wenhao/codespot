# Spec Delta

## ADDED Requirements

### Requirement: show 子命令

`codespot show` SHALL 读取最近一次 report.json 并打印问题详情列表，支持过滤：`--severity <level>`（可逗号组合）、`--file <前缀>`、`--rule <CS 编号>`、`--limit <N>`（默认 50）。每条详情 SHALL 含：CS 编号、严重级、文件:行号、说明、脱敏片段；MUST NOT 输出底层引擎名称。无匹配时输出明确提示。

#### Scenario: 按严重级过滤

- **WHEN** 执行 `codespot show --severity critical,major`
- **THEN** 仅列出 critical 与 major 的详情，均带 CS 编号

#### Scenario: 按 CS 编号定位

- **WHEN** 执行 `codespot show --rule CS-1a2b3`
- **THEN** 列出该规则的全部命中详情
