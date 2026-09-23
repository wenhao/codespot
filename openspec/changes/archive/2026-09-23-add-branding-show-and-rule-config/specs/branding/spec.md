# Spec Delta

## ADDED Requirements

### Requirement: CS 编号稳定派生

每条 issue SHALL 获得对外编号 `csId = "CS-" + tool|rule 联合哈希的前 5 位十六进制`：同一 tool+rule 在任意仓库、任意次扫描中 MUST 得到相同 csId；不同 tool+rule 碰撞时 MUST 附加区分后缀。csId SHALL 写入 report.json 的 `csId` 字段。

#### Scenario: 跨次扫描稳定

- **WHEN** 对同一仓库连续两次扫描
- **THEN** 同一发现的 csId 两次一致

### Requirement: 人读报告品牌隔离

report.md SHALL 只包含 codespot 品牌信息：CS 编号、严重级、文件:行号、说明与脱敏片段；MUST NOT 出现底层引擎名称、引擎官方文档链接或"由 XX 工具检出"类表述。report.json 作为 agent 内部接口 SHALL 保留 tool/rule/ruleUrl 原始字段。

#### Scenario: md 无引擎名

- **WHEN** 渲染一版含各引擎发现的报告
- **THEN** 全文检索不存在 ruff/bandit/oxlint/sonarjs/PMD/SpotBugs/gitleaks/sqlfluff/semgrep 任何引擎名

#### Scenario: json 保留内部字段

- **WHEN** agent 读取 report.json
- **THEN** 每条 issue 同时具有 tool、rule、ruleUrl 与 csId
