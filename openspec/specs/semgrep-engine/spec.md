# semgrep-engine Specification

## Purpose
TBD - created by archiving change add-semgrep-engine. Update Purpose after archive.

## Requirements

### Requirement: 语言到规则集映射

适配器默认 SHALL 使用 `--config auto`（semgrep 自行按项目语言选择规则包，实测为当前 registry 唯一稳定可用的拉取通道——旧的 `p/<lang>` 端点已 404）。项目 `.codespot/config.json` 的 `"semgrep_config"` SHALL 覆盖默认（值即 semgrep `--config` 参数，可为规则集名、本地目录或单个规则文件）；适配器内部保留语言→`p/<lang>` 映射表作为 auto 失败时的重试兜底。

#### Scenario: 默认 auto 规则包

- **WHEN** 范围含 .go 文件且未配置覆盖
- **THEN** 调用带 `--config auto` 且能命中 go 安全规则（含 CWE 元数据）

#### Scenario: 项目覆盖规则集

- **WHEN** .codespot/config.json 指定 `"semgrep_config": "p/gosec"` 且范围含 .go 文件
- **THEN** 调用带 `--config p/gosec` 而非默认 auto

### Requirement: 许可边界（内部使用）

适配器与文档 MUST 注明：semgrep 引擎与 registry 规则仅限公司内部使用，不得随 codespot 或任何发布物对外分发；codespot 不打包、不镜像任何 semgrep 规则，规则由用户机器运行时从官方 registry 拉取。

#### Scenario: 文档含许可说明

- **WHEN** 阅读 README 的 semgrep 段落
- **THEN** 明确写着"仅限内部使用、规则运行时拉取、不随工具分发"

### Requirement: JSON 解析与 severity 映射

适配器 SHALL 解析 `semgrep scan --json` 输出：`check_id`→rule、`path`→file（相对化）、`start.line/col`→位置、`extra.message`→message、`extra.lines`→snippet、`extra.metadata.cwe`→cwe（取首个编号）、`extra.severity`→severity（ERROR→major、WARNING→minor、INFO→info）；ruleUrl 取 `extra.metadata.references` 首个链接，缺失时指向 https://semgrep.dev/rulehub/ 。

#### Scenario: severity 与 cwe 正确映射

- **WHEN** 夹具命中一条 ERROR 级、带 CWE 元数据的安全规则
- **THEN** issue severity=major 且 cwe 字段为对应编号

### Requirement: 网络失败降级

规则拉取/扫描失败（退出码 ≥2 或超时）SHALL 作为引擎失败上报（退出 2 + stderr 原因），由主控记入 engine_errors 并隔离，不影响其他引擎；无网络且无规则缓存时同理。

#### Scenario: 断网时不阻塞整体扫描

- **WHEN** 无网络且规则未缓存，范围含 .go 文件
- **THEN** 其他引擎结果正常产出，report.json 的 engine_errors 含 semgrep 条目

### Requirement: 本地规则默认与更新命令

`codespot setup` 安装 semgrep 引擎后 SHALL 确保 `~/.codespot/semgrep-rules/` 就位（缺失则浅克隆 OSS semgrep-rules 仓库；已存在则跳过）；`codespot update-rules` SHALL 刷新该目录（git pull，失败时重新浅克隆）。engine_semgrep 在该目录存在时 SHALL 默认按语言子目录使用本地规则（缺失语言回退 `--config auto` 并提示）。

#### Scenario: setup 后规则就位

- **WHEN** 全新机器执行 `codespot setup`
- **THEN** `~/.codespot/semgrep-rules/` 存在且 semgrep 默认以本地规则运行

#### Scenario: update-rules 刷新

- **WHEN** 执行 `codespot update-rules`
- **THEN** 规则目录刷新到最新（git pull 或重新克隆），退出码反映成败
