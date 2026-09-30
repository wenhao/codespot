# Spec Delta

## REMOVED Requirements

### Requirement: update-db 命令

**Reason**: OSV 弃用离线漏洞库（始终在线），update-db 无存在意义。

**Migration**: 离线依赖扫描不再支持；断网环境依赖引擎将不可用（其余引擎正常）。
