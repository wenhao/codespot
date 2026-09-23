# Proposal

## Why

用户确认：TruffleHog 以**可选引擎（opt-in）**定位集成——默认不运行，仅当用户显式指定（CLI `--engine` 或项目 config 的 `enabled`）时使用。这化解了此前不集成的全部顾虑（AGPL 仅内部使用无碍；联网验证默认关闭）。价值：800+ 检测器（约为 gitleaks 3.6 倍）作为密钥深度层，与常开的 gitleaks 构成"快速层 + 点名深度层"组合，复用 JS/TS 双层的既有架构模式。

## What Changes

- 主控新增通用 **opt-in 引擎机制**：registry 引擎可声明 `"opt_in": true`（默认不被调度）；激活途径二选一：`codespot scan --engine <name>`（`--engine` 可重复）或 `.codespot/config.json` 的 `rules.<category>.enabled: true`。
- registry 新增 `trufflehog`：类别 `secrets_deep`，raw_binary 安装形态，版本锁定 3.97.6。
- 新增 `engine_trufflehog.py`：`trufflehog filesystem <路径> --no-verification --json`（NDJSON 输出逐行解析），issue 含 DetectorName/Verified/Redacted 脱敏片段；默认关闭验证，无外呼。
- SKILL.md/README 更新：密钥发现的呈现中可提示用户可选启用深度密钥检测。
- 不包含：联网验证（`--no-verification` 写死为默认；验证需求由用户手动执行 TruffleHog 原生命令）。

## Capabilities

### New Capabilities
- `trufflehog-engine`: TruffleHog 适配——opt-in 定位、NDJSON 解析、脱敏、Verified 字段透传。

### Modified Capabilities
- `scan-orchestration`: 调度支持 opt-in 引擎（默认跳过，`--engine`/config `enabled` 激活）。
- `skill-workflow`: 密钥发现时提示可选深度检测。

## Impact

- 新增 scripts/engines/engine_trufflehog.py；主控 select_engines 与 scan 参数扩展；registry +1 条目。
- TruffleHog AGPL-3.0：仅内部使用、运行时下载、不随 codespot 分发（与 semgrep 同一边界写法）。
