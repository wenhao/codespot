# python-security-engine Specification

## Purpose
TBD - created by archiving change add-deep-layers-bandit-sqlfluff-spotbugs. Update Purpose after archive.

## Requirements

### Requirement: bandit 安全扫描

Python 安全引擎 SHALL 以 `bandit -f json` 扫描范围内 .py 文件并解析其 JSON：每条发现转为统一 issue（`tool=bandit`，`rule` 取 B 编码，`ruleUrl` 指向 https://bandit.readthedocs.io/ 对应页面），severity 按 issue_severity 映射（HIGH→critical、MEDIUM→major、LOW→minor），`fixHint` 不适用时省略。

#### Scenario: 检出硬编码密码

- **WHEN** 夹具含 `password = "..."`（B105）
- **THEN** 产出 rule=B105、severity=critical 的 issue

#### Scenario: 与 ruff 引擎共存

- **WHEN** 范围含 .py 文件
- **THEN** 调度同时运行 ruff 与 bandit 两个适配器，报告同时含两者的发现
