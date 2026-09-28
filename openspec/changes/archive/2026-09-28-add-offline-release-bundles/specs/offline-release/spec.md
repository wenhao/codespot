# Spec Delta

## ADDED Requirements

### Requirement: 离线包内容与结构

`make_bundle.py` SHALL 在单平台产出 `codespot-offline-<version>-<os>-<arch>` 包，内容：① `skill/`（完整载荷）；② `engines/`（该平台全部已装引擎，保持 `<name>-<version>/` 布局与 `.ok` 标记；不支持平台的引擎缺席）；③ `wheels/`（venv 引擎的完整传递依赖 wheel，按 python 大版本分子目录）；④ `offline/osv-db/`（构建时 OSV 本地库缓存）；⑤ `offline/semgrep-rules/`（Semgrep 规则快照，若可提取）；⑥ `install-offline.sh` / `install-offline.bat`；⑦ `THIRD-PARTY-NOTICES`（引擎名-许可-上游源码链接，含 TruffleHog AGPL 源码可得声明）；⑧ `MANIFEST.json`（版本、平台、引擎清单、构建时间）。

#### Scenario: 四平台打包产物

- **WHEN** 推送 `v*` tag 触发 release 工作流
- **THEN** Release 附带 linux-x64 / macos-arm64 / macos-x64 / windows-x64 四个离线包资产

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
