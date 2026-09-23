# trufflehog-engine Specification

## Purpose
TBD - created by archiving change add-trufflehog-optin-engine. Update Purpose after archive.

## Requirements

### Requirement: opt-in 触发

TruffleHog 引擎默认 SHALL 不被调度；仅当 ① `codespot scan --engine trufflehog` 显式命名（`--engine` 可重复），或 ② 项目 `.codespot/config.json` 存在 `rules.secrets_deep.enabled: true` 时运行。运行模式默认 `--no-verification`（纯本地检测，无网络外呼）。

#### Scenario: 默认不运行

- **WHEN** 夹具含密钥且未显式指定 trufflehog
- **THEN** 调度不包含 trufflehog，报告无其发现

#### Scenario: 显式命名后运行

- **WHEN** 执行 `codespot scan --engine trufflehog`
- **THEN** trufflehog 被调度并检出夹具中的私钥（rule=PrivateKey，severity=critical）

### Requirement: NDJSON 解析与脱敏

适配器 SHALL 逐行解析 TruffleHog 的 NDJSON 输出：`rule`=DetectorName、`message`=DetectorDescription、`line` 取 SourceMetadata.Data.Filesystem.line、`snippet` 使用 Redacted 字段（缺失时本地脱敏）、`tool=trufflehog`；每条发现 MUST 附 `verified` 字段（布尔，透传 Verified）。

#### Scenario: 私钥检出带 verified 标记

- **WHEN** 夹具含 PEM 私钥
- **THEN** 产出 rule=PrivateKey、verified=false 的 critical issue，snippet 为脱敏形式

### Requirement: 许可边界

TruffleHog（AGPL-3.0）SHALL 仅在内部使用、运行时下载的前提下集成；不随 codespot 打包分发；文档须注明。

#### Scenario: 文档含边界说明

- **WHEN** 阅读 README 的 trufflehog 段落
- **THEN** 明确写着 AGPL、仅内部使用、运行时下载、不随工具分发
