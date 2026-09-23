# java-engine Specification

## Purpose
TBD - created by archiving change add-jsts-java-pmd-and-fix-loop. Update Purpose after archive.

## Requirements

### Requirement: PMD 源码级扫描

Java 引擎 SHALL 以 PMD `check` 命令扫描范围内 `.java` 文件（源码级，无需编译），使用内置规则集（基于官方 quickstart 精简），SARIF 输出解析为统一 issue：`rule` 取 PMD 规则 ID，`ruleUrl` 指向 https://docs.pmd-code.org/ 对应规则页，severity 按 priority 映射（1→critical、2→major、3→minor、4/5→info）。

#### Scenario: 检出已知 PMD 规则

- **WHEN** 夹具 Java 文件含空 catch 块等已知问题
- **THEN** 产出对应规则 issue 且 severity 与 priority 映射一致

### Requirement: JRE 探测

Java 引擎运行前 SHALL 探测 `java`（JRE 8+）；不可用时输出空结果并退出 0，同时 MUST 在 stderr 打印一行原因供主控记录为引擎级提示（不作为失败）——若主控配置将该引擎标为必需则按 engine_error 处理（默认非必需）。

#### Scenario: 无 JRE 时不阻塞

- **WHEN** 机器无 java 而范围含 .java 文件
- **THEN** 适配器退出 0、零发现，stderr 含 "java" 提示，报告 md 的附注中出现该提示
