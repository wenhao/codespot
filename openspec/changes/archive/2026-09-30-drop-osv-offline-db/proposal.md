# Proposal

## Why

用户决策：OSV 依赖扫描**不再使用离线漏洞库**，始终在线查询 osv.dev（数据最新；全新环境首跑仅 PyPI 可下载、其余生态逐次落盘且伴随 exit 127 噪音的 osv-scanner 2.6 怪癖彻底规避）。离线数据库、update-db 命令、osv_offline 配置全部移除；断网时依赖引擎按既有失败隔离语义处理。

## What Changes

- 移除 `codespot update-db` 子命令。
- `engine_deps.py`：移除 `--offline-vulnerabilities` 分支与 `offline_db_available` 引用（始终在线）。
- `make_bundle.py`：离线包不再收集 OSV 库（`offline/osv-db` 目录移除；其余内容不变——离线包内依赖扫描将因无库而失败并提示，属已知边界）。
- README 英中：移除 update-db/osv_offline 相关说明，离线指南更新（依赖扫描需网络）。

## Capabilities

### Modified Capabilities
- `dependency-engine`: 网络语义改为仅在线。
- `offline-release`: 离线包不再包含 OSV 漏洞库。
- `scan-orchestration`: 移除 update-db 命令。
