# Spec Delta

## ADDED Requirements

### Requirement: dialect 探测链

SQL 引擎 SHALL 按以下顺序确定 dialect：① 目标文件内的 `sqlfluff:dialect:<x>` 注释（首个命中文件的配置应用于本次调用）；② 项目 `.codespot/config.json` 的 `"dialect"` 字段；③ 内容启发式（AUTO_INCREMENT/BACKTICK→mysql，`::`类型转换→postgres 等，命中≥1 条才采用）；④ 均未命中时用 `ansi` 兜底并在 stderr 提示"建议在 .codespot/config.json 指定 dialect"。

#### Scenario: 未指定 dialect 时兜底不报错

- **WHEN** 目标 SQL 无任何 dialect 线索
- **THEN** 以 ansi 扫描成功（退出 0），stderr 含提示

#### Scenario: 项目配置优先

- **WHEN** .codespot/config.json 指定 dialect=postgres 且文件无注释
- **THEN** 以 postgres 运行

### Requirement: 规则取舍与解析失败处理

默认规则集 MUST 关闭纯排版组（Layout/LT、Capitalisation/CP），启用语义组（Ambiguous、Structure、References、Convention 语义类）；解析失败产生的 PRS 类发现 SHALL 在 issue 上标注 `unparsable: true` 且主控报告 md 中单列为"无法解析"，修复循环不得将其作为改写目标。

#### Scenario: LT/CP 默认不出现

- **WHEN** 夹具 SQL 有关键字小写、缩进不齐
- **THEN** 报告不含 LT/CP 规则

#### Scenario: 解析失败单列

- **WHEN** 夹具含无法解析的 SQL 片段
- **THEN** 对应 PRS issue 带 unparsable 标记
