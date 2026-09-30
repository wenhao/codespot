# Spec Delta

## MODIFIED Requirements

### Requirement: 网络语义

依赖扫描 SHALL 默认**在线**查询 osv.dev（数据最新）；仅当 `.codespot/config.json` 设 `"osv_offline": true` 或环境变量 `CODESPOT_OSV_OFFLINE=1` 时，扫描加 `--offline-vulnerabilities` 走本地库（须已由 `codespot update-db` 就位，缺失生态将被跳过并在 stderr 说明）。失败（网络错误/退出码 ≥2）仍作为引擎失败上报并隔离。

#### Scenario: 默认在线

- **WHEN** 未配置任何离线选项且范围含清单文件
- **THEN** osv-scanner 以在线模式运行并产出依赖发现

#### Scenario: 显式离线

- **WHEN** config 设 `"osv_offline": true` 且已 `update-db`
- **THEN** osv-scanner 带 `--offline-vulnerabilities` 运行，无网络请求

#### Scenario: 断网降级

- **WHEN** 无网络且未启用离线库
- **THEN** 该引擎按失败上报并隔离（engine_errors 含条目），其他引擎正常
