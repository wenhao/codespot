# Spec Delta

## MODIFIED Requirements

### Requirement: 网络语义

依赖扫描 SHALL 始终在线查询 osv.dev（不做离线库判定）；断网或下载失败（退出码 ≥2）SHALL 作为引擎失败上报（退出 2 + stderr 原因）并隔离，不影响其他引擎。

#### Scenario: 默认在线

- **WHEN** 未配置任何离线选项且范围含清单文件
- **THEN** osv-scanner 以在线模式运行并产出依赖发现

#### Scenario: 显式离线

- **WHEN** config 残留旧版 `"osv_offline": true` 配置（本版已弃用该选项）
- **THEN** 该配置被忽略，仍以在线模式运行

#### Scenario: 断网降级

- **WHEN** 无网络且范围含清单文件
- **THEN** 该引擎按失败上报并隔离（engine_errors 含条目），其他引擎正常

## REMOVED Requirements

### Requirement: 离线漏洞库（update-db / --offline-vulnerabilities / osv_offline 配置）

**Reason**: osv-scanner 2.6 全新缓存首跑仅 PyPI 可下载、其余生态逐次落盘且伴随 exit 127 噪音；在线模式数据最新且行为确定。用户决策弃用离线库。

**Migration**: 需要离线依赖扫描的场景使用在线模式先行完成一次扫描即可；断网环境依赖引擎将报告不可用（其余引擎不受影响）。
