# Spec Delta

## MODIFIED Requirements

### Requirement: 引擎注册表驱动调度

调度 SHALL 由 `scripts/engines/registry.json` 驱动，并支持 **opt-in 引擎**：声明 `"opt_in": true` 的引擎默认不被调度，仅当 `scan --engine <name>` 显式命名、或 `.codespot/config.json` 的 `rules.<category>.enabled: true` 时被纳入；其余调度语义不变。

#### Scenario: 默认不运行 opt-in 引擎

- **WHEN** 未显式指定且范围含 .py 文件
- **THEN** opt-in 引擎不被调度

#### Scenario: 显式命名后运行

- **WHEN** 执行 `codespot scan --engine trufflehog`
- **THEN** trufflehog 被调度并产出发现

#### Scenario: 无匹配引擎时不误调用

- **WHEN** 目标文件清单只含 `.py` 文件且本批仅注册了 secrets（常开）与 python 引擎
- **THEN** 调度恰好调用这两个适配器各一次，不调用未注册的 JS/Java/SQL 适配器
