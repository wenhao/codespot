# Spec Delta

## MODIFIED Requirements

### Requirement: 统一 issue schema

每条 issue MUST 包含字段：`tool`、`language`、`rule`、`ruleUrl`、`severity`（critical/major/minor/info 之一）、`file`、`line`、`column`、`message`、`snippet`；可选字段：`cwe`、`fixHint`、`unparsable`。severity SHALL 由 `scripts/rules-severity.json` 归一化，用户覆盖文件 `.codespot/severity-overrides.json` MUST 支持 `rules`（逐 `tool+rule`）与 `default`（逐 tool 默认值）两级，覆盖优先于默认映射。

#### Scenario: severity 映射与用户覆盖

- **WHEN** ruff 报出 S 规则族的某条高危规则，且 overrides 中将该 rule 覆盖为 minor
- **THEN** report.json 中该条 issue 的 severity 为 minor，其余未覆盖规则按默认映射

#### Scenario: 工具级默认覆盖

- **WHEN** overrides 中设置 `"pmd": {"default": "minor"}` 且某条 PMD 规则无逐规则映射
- **THEN** 该条 severity 为 minor

## ADDED Requirements

### Requirement: venv 安装形态

setup SHALL 支持第三种安装形态 `venv`：在 `~/.codespot/engines/<name>-<version>/` 内 `python3 -m venv .` + `bin/pip install <锁定版本包>`；`python3` 不可用时按逐引擎失败处理，不阻塞其余引擎。

#### Scenario: SQLFluff 装入独立 venv

- **WHEN** 执行 `codespot setup`
- **THEN** sqlfluff 安装于独立 venv，宿主 Python 环境无新包
