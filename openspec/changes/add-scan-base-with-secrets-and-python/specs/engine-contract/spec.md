# Spec Delta

## Purpose

定义所有引擎适配器必须遵守的统一调用契约与统一 issue 数据结构，是各批次并行开发引擎的依据。

## ADDED Requirements

### Requirement: 统一调用接口

每个适配器脚本 SHALL 以如下方式被调用：`engine_<name>.py --workdir <仓库根> --files <清单文件> --out <结果json路径>`；结果 JSON MUST 为对象数组，每个元素即一条 issue。

#### Scenario: 契约可用性由 selftest 验证

- **WHEN** 执行 `codespot selftest`
- **THEN** 每个已注册且已安装的引擎在夹具上按契约产出结果 JSON，字段完整性通过校验

### Requirement: 统一 issue schema

每条 issue MUST 包含字段：`tool`（引擎名）、`language`、`rule`（规则 ID）、`ruleUrl`（官方文档链接）、`severity`（critical/major/minor/info 之一）、`file`、`line`、`column`、`message`、`snippet`；可选字段：`cwe`、`fixHint`。severity SHALL 由 `scripts/rules-severity.json` 的映射表归一化，用户可在项目 `.codespot/severity-overrides.json` 中按 `tool+rule` 覆盖。

#### Scenario: severity 映射与用户覆盖

- **WHEN** ruff 报出 S 规则族的某条高危规则，且 overrides 中将该 rule 覆盖为 minor
- **THEN** report.json 中该条 issue 的 severity 为 minor，其余未覆盖规则按默认映射

### Requirement: 退出码语义

适配器退出码 SHALL 满足：0 = 引擎运行成功（无论发现多少问题）；2 = 引擎自身失败（缺运行时/配置错/内部错误），且失败原因写入 stderr。"发现问题数量" MUST NOT 影响适配器退出码。

#### Scenario: 有发现仍返回 0

- **WHEN** 夹具 Python 文件含 10 条 ruff 违规
- **THEN** engine_py.py 退出码为 0，结果 JSON 恰好包含这 10 条
