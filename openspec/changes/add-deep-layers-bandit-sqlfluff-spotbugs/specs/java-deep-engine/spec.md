# Spec Delta

## ADDED Requirements

### Requirement: 构建探测与编译

Java 深度层 SHALL 在 PMD 扫描完成后运行：探测 `pom.xml` → `mvn -q compile -DskipTests`；探测 `build.gradle(.kts)` → `gradle compileJava -q`（超时 300s）；两者皆无或编译失败 → 跳过深度层（stderr 说明原因，非失败）。

#### Scenario: 无构建文件跳过

- **WHEN** 范围含 .java 但仓库无 pom.xml/build.gradle
- **THEN** 深度层不运行，PMD 结果正常输出，退出 0

#### Scenario: 编译失败不阻塞

- **WHEN** mvn compile 因依赖下载失败
- **THEN** 深度层跳过并在 stderr 说明，PMD 结果保留，适配器退出 0

### Requirement: SpotBugs 扫描与安全提级

编译产物（target/classes 或 build/classes/java/main，存在 class 文件时）SHALL 以 SpotBugs + findsecbugs-plugin 扫描（SARIF 输出）：`rule` 取 bug pattern 语义名，`cwe` 透传 FindSecBugs 的 cweid，severity 按 rank 映射（1-4→critical、5-9→major、10-14→minor、15-20→info），FindSecBugs 安全类（SEC 缩写）整体提一档。

#### Scenario: 检出 SQL 注入模式

- **WHEN** 夹具编译产物含可注入的 JDBC 拼接
- **THEN** 产出 rule=SQL_INJECTION 相关 pattern 的 issue，含 cwe 字段，severity ≥ major
