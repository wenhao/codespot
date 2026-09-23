# Spec Delta

## MODIFIED Requirements

### Requirement: 引擎并行与失败隔离

多个适配器 SHALL 并行执行；单个引擎以退出码 2 失败（缺运行时、配置错误）MUST NOT 阻止其他引擎的结果合并。失败信息按双层呈现：report.json 的 `engine_errors` 保留真实引擎键（agent 内部接口）；report.md SHALL 以类别别名中性表述（"检查模块提示"），不出现引擎名。

#### Scenario: 一个引擎失败不影响整体报告

- **WHEN** ruff 二进制缺失但 gitleaks 正常，执行 scan
- **THEN** 报告仍包含 gitleaks 的发现，report.json 的 engine_errors 含 ruff 的失败原因，退出码为 0；report.md 中的对应提示只出现类别别名"python_lint"，无引擎名
