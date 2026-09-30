# dependency-engine Specification

## Purpose
TBD - created by archiving change add-dependency-scanning-osv-scanner. Update Purpose after archive.

## Requirements

### Requirement: 依赖清单发现与扫描

依赖引擎 SHALL 在目标文件清单中识别**可确定版本**的依赖清单/锁文件（requirements*.txt、package-lock.json、npm-shrinkwrap.json、yarn.lock、pom.xml、go.mod、go.sum、Cargo.lock、composer.lock、Gemfile.lock、*.csproj）；pyproject.toml、package.json 等无版本 pin 的宽松清单 MUST 被排除（osv-scanner 无法解析会报错），对每个命中文件以 `osv-scanner scan source -L <file> -f json` 查询 OSV 漏洞库；清单不存在时 SHALL 输出空结果并退出 0。

#### Scenario: 旧版本依赖被检出

- **WHEN** 夹具 requirements.txt pin 一个有已知 CVE 的旧版本（如 requests==2.19.0）
- **THEN** 产出 issue：rule 为 GHSA/OSV 编号，file 指向该清单，message 含包名

#### Scenario: 无清单时空结果

- **WHEN** 范围内无任何清单文件
- **THEN** 适配器退出 0、零发现

### Requirement: severity 与修复建议

issue severity SHALL 取漏洞数据源的严重级（OSV 数据库 CVSS 汇总或等价字段），无法取得时缺省 major；`fixHint` SHALL 在存在已知修复版本时给出 `{"description": "upgrade to <fixed>"}`；`ruleUrl` 指向对应 GHSA/OSV advisory 页面。

#### Scenario: 修复版本透传

- **WHEN** 某漏洞数据含 fixed 版本
- **THEN** 对应 issue 的 fixHint 描述含该版本号

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
