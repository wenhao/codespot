# reporting Specification

## Purpose
定义双报告产物的格式与内容要求：report.json 供 AI agent 消费，report.md 供人阅读。

## Requirements

### Requirement: report.json 结构

`.codespot/report.json` SHALL 包含：`generatedAt`（ISO 时间）、`scope`（实际生效档位与文件数）、`issues`（统一 issue 数组，按 severity 降序、文件分组排序）、`engine_errors`（失败引擎数组，可为空）、`summary`（各 severity 计数与总数）。

#### Scenario: summary 与 issues 一致

- **WHEN** 报告含 2 critical、3 major
- **THEN** summary 中 critical=2、major=3、total=5，与 issues 数组一致

### Requirement: report.md 可读摘要

`.codespot/report.md` SHALL 按 codespot 品牌渲染：CS 编号 + 严重级分组 + `file:line` + 说明（脱敏片段）；MUST NOT 出现底层引擎名称与引擎官方链接；引擎失败在 md 中以"检查模块提示"呈现（用类别名或"某检查模块"，不暴露引擎名）；引擎级不可用提示（如 JRE 缺失）同样以中性的 codespot 措辞表述。report.json 增加 `csId` 字段，其余内部字段不变。

#### Scenario: md 无引擎名且含 csId

- **WHEN** 渲染一份含失败模块的报告
- **THEN** md 无任何底层引擎名；report.json 每条 issue 含 csId

#### Scenario: 干净扫描的通过报告

- **WHEN** 目标文件无任何发现
- **THEN** report.md 首行为通过结论，并注明扫描档位与文件数

### Requirement: 退出码语义（主控）

`codespot scan` 退出码 SHALL 满足：0 = 扫描流程完成（无论发现问题多少）；2 = 编排层失败（范围计算失败、所有引擎失败、报告无法写出）。发现数量 MUST NOT 使主控退出码非零（由 agent 读报告决定后续动作）。

#### Scenario: 有发现仍返回 0

- **WHEN** 夹具产生 5 条发现
- **THEN** `codespot scan` 退出码为 0，报告完整
