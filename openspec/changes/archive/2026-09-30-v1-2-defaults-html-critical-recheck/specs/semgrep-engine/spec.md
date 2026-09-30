# Spec Delta

## ADDED Requirements

### Requirement: 本地规则默认与更新命令

`codespot setup` 安装 semgrep 引擎后 SHALL 确保 `~/.codespot/semgrep-rules/` 就位（缺失则浅克隆 OSS semgrep-rules 仓库；已存在则跳过）；`codespot update-rules` SHALL 刷新该目录（git pull，失败时重新浅克隆）。engine_semgrep 在该目录存在时 SHALL 默认按语言子目录使用本地规则（缺失语言回退 `--config auto` 并提示）。

#### Scenario: setup 后规则就位

- **WHEN** 全新机器执行 `codespot setup`
- **THEN** `~/.codespot/semgrep-rules/` 存在且 semgrep 默认以本地规则运行

#### Scenario: update-rules 刷新

- **WHEN** 执行 `codespot update-rules`
- **THEN** 规则目录刷新到最新（git pull 或重新克隆），退出码反映成败
