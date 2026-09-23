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

`.codespot/report.md` SHALL 按严重级分组（critical→info）列出发现，每条含 `file:line`（Markdown 链接形式）、规则 ID（链接到 ruleUrl）与 message；密钥类 snippet 只出现脱敏形式；无发现时 SHALL 输出明确的"通过"结论与扫描范围摘要。

#### Scenario: 干净扫描的通过报告

- **WHEN** 目标文件无任何发现
- **THEN** report.md 首行为通过结论，并注明扫描档位与文件数

### Requirement: 退出码语义（主控）

`codespot scan` 退出码 SHALL 满足：0 = 扫描流程完成（无论发现问题多少）；2 = 编排层失败（范围计算失败、所有引擎失败、报告无法写出）。发现数量 MUST NOT 使主控退出码非零（由 agent 读报告决定后续动作）。

#### Scenario: 有发现仍返回 0

- **WHEN** 夹具产生 5 条发现
- **THEN** `codespot scan` 退出码为 0，报告完整
