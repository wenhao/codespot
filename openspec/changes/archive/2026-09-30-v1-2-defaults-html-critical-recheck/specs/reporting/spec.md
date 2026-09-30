# Spec Delta

## ADDED Requirements

### Requirement: HTML 报告产物

每次 `codespot scan` SHALL 额外产出 `.codespot/report.html`：自包含 CSS（无外部依赖）、codespot 品牌、按严重级分组的发现列表（CS 编号、file:line、说明、脱敏片段）与严重级统计卡片；`codespot report --html` SHALL 输出该文件的路径，`--print` 时打印内容。md/json/html 三产物内容一致（同一 payload 渲染）。

#### Scenario: scan 后存在 HTML 报告

- **WHEN** `codespot scan` 完成
- **THEN** `.codespot/report.html` 存在且含 CS 编号与严重级统计，无底层引擎名
