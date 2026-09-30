# offline-release Specification

## Purpose
TBD - created by archiving change add-offline-release-bundles. Update Purpose after archive.

## Requirements

### Requirement: 离线包内容与结构

离线包 SHALL 不再包含 `offline/osv-db/`（OSV 离线漏洞库随包移除——依赖扫描在线运行）；其余内容（skill/、engines/、wheels/、offline/semgrep-rules/、安装脚本、NOTICES、MANIFEST）不变。

#### Scenario: 四平台打包产物

- **WHEN** 推送 `v*` tag 触发 release 工作流
- **THEN** Release 附带 linux-x64 / macos-arm64 / windows-x64 三个离线包资产，包内无 osv-db 目录

#### Scenario: 许可清单含 AGPL 源码链接

- **WHEN** 检查包内 THIRD-PARTY-NOTICES
- **THEN** 含 TruffleHog（AGPL-3.0，源码链接）与各引擎许可条目

### Requirement: 离线安装脚本

install 脚本 SHALL：复制 `engines/*` 到 `~/.codespot/engines/`；复制 `offline/osv-db/*` 到平台 OSV 缓存目录；复制 `offline/semgrep-rules/` 到 `~/.codespot/semgrep-rules/`；把 `skill/` 安装到 agent skills 目录（复制）；幂等可重复执行。Windows 提供 `.bat` 等价物。

#### Scenario: 安装后零网络扫描

- **WHEN** 断网环境执行 install-offline 后对含 Python/密钥/依赖清单问题的仓库运行 scan
- **THEN** gitleaks/ruff/bandit/OSV（离线库）等引擎正常产出发现，无需任何网络请求

### Requirement: Semgrep 离线规则回退

`engine_semgrep` 默认规则选择 SHALL 升级：`~/.codespot/semgrep-rules/` 存在且非空时以其为默认 `--config`（离线模式），否则维持 `--config auto`；`semgrep_config` 项目覆盖优先级最高。

#### Scenario: 离线规则自动生效

- **WHEN** install-offline 已就位规则目录且项目未配置覆盖
- **THEN** semgrep 以本地规则目录运行
