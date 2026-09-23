# Spec Delta

## ADDED Requirements

### Requirement: 类别别名与简单开关

registry SHALL 为每个引擎声明对外类别名（category）：secrets、python_lint、python_security、js_lint、java、sql、semantic（内部组件无别名）。`.codespot/config.json` 的 `"rules"` 段 SHALL 以类别为键，支持：`disabled: true`（该类别整体不运行/不计入报告）、`ignore: [规则编号...]`（按各引擎原始规则 ID 删减命中）。用户 MUST NOT 需要在配置中书写底层引擎名。

#### Scenario: 关闭整个类别

- **WHEN** config.json 设置 `{"rules": {"python_security": {"disabled": true}}}` 并扫描
- **THEN** 该类别引擎不被调度，报告中无其发现

#### Scenario: 删减单条规则

- **WHEN** config.json 设置 `{"rules": {"python_lint": {"ignore": ["RUF100"]}}}`
- **THEN** 重扫后 RUF100 类发现消失，其他 python_lint 发现保留

### Requirement: 原生配置文件优先

对支持原生配置的引擎（ruff、oxlint、sqlfluff、gitleaks），若用户项目存在对应原生配置文件（`.ruff.toml`/`ruff.toml`/含 `[tool.ruff]` 的 pyproject、`.oxlintrc.json`、`.sqlfluff`、`.gitleaks.toml`），适配器 SHALL 优先使用之（此时内置默认配置不参与，config.json 的 ignore 仍叠加生效）；不存在时使用 codespot 内置默认。

#### Scenario: 项目自有 ruff 配置生效

- **WHEN** 项目根存在 .ruff.toml 且 codespot 内置默认与它冲突
- **THEN** 扫描行为遵循 .ruff.toml
