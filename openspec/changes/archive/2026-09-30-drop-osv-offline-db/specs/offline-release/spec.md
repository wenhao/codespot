# Spec Delta

## MODIFIED Requirements

### Requirement: 离线包内容与结构

离线包 SHALL 不再包含 `offline/osv-db/`（OSV 离线漏洞库随包移除——依赖扫描在线运行）；其余内容（skill/、engines/、wheels/、offline/semgrep-rules/、安装脚本、NOTICES、MANIFEST）不变。

#### Scenario: 四平台打包产物

- **WHEN** 推送 `v*` tag 触发 release 工作流
- **THEN** Release 附带 linux-x64 / macos-arm64 / windows-x64 三个离线包资产，包内无 osv-db 目录

#### Scenario: 许可清单含 AGPL 源码链接

- **WHEN** 检查包内 THIRD-PARTY-NOTICES
- **THEN** 含 TruffleHog（AGPL-3.0，源码链接）与各引擎许可条目
