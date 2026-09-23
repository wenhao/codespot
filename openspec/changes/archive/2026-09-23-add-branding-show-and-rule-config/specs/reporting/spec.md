# Spec Delta

## MODIFIED Requirements

### Requirement: report.md 可读摘要

`.codespot/report.md` SHALL 按 codespot 品牌渲染：CS 编号 + 严重级分组 + `file:line` + 说明（脱敏片段）；MUST NOT 出现底层引擎名称与引擎官方链接；引擎失败在 md 中以"检查模块提示"呈现（用类别名或"某检查模块"，不暴露引擎名）；引擎级不可用提示（如 JRE 缺失）同样以中性的 codespot 措辞表述。report.json 增加 `csId` 字段，其余内部字段不变。

#### Scenario: md 无引擎名且含 csId

- **WHEN** 渲染一份含失败模块的报告
- **THEN** md 无任何底层引擎名；report.json 每条 issue 含 csId

#### Scenario: 干净扫描的通过报告

- **WHEN** 目标文件无任何发现
- **THEN** report.md 首行为通过结论，并注明扫描档位与文件数
