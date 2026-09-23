# Design

## Context

TruffleHog 以 opt-in 密钥深度层定位集成（用户确认）。AGPL-3.0 内部使用无碍；默认 `--no-verification` 消除联网验证副作用。

## Decisions

### D1. opt_in 为通用 registry 机制（非 trufflehog 专属）
registry 引擎加 `"opt_in": true`；`select_engines(entries, requested_engines)` 签名扩展：opt_in 且 (名字在 requested 或其 category enabled) → 调度。scan 新增 `--engine <name>` 可重复参数。该机制今后任何"点名才跑"的引擎（如重量级分析）直接复用。

### D2. 类别 secrets_deep
与 `secrets`（gitleaks，常开）区分：config 里可分别控制。`rules.secrets_deep.enabled: true` 激活；`disabled` 语义对 opt-in 引擎同样生效（enabled 优先级低于 disabled）。

### D3. 调用与解析
`trufflehog filesystem <workdir> --no-verification --json` ——直接扫 workdir（TruffleHog 自己处理全部文件；扫描范围与 git 无关，密钥扫描宁可略宽）。输出为 NDJSON：结果行含 `SourceMetadata`，日志行含 `"logger":"trufflehog"`——按行 json.loads，缺 SourceMetadata 的行跳过。字段映射：DetectorName→rule、DetectorDescription→message、SourceMetadata.Data.Filesystem.{file,line}、Redacted→snippet（trufflehog 自带脱敏，缺失时用 common.redact 兜底）、Verified→verified。severity 一律 critical；退出码 0 正常（trufflehog 不以发现数改变退出码）。

### D4. 安装 raw_binary 的变体
release 是 tar.gz（内含 trufflehog 二进制 + LICENSE/docs），不是裸文件——不用 raw_binary，沿用 tar.gz 形态（archive 内 binary 名即 `trufflehog`，既有逻辑直接命中）。URL：`.../download/v{version}/trufflehog_{version}_{os}_{arch}.tar.gz`。

### D5. selftest
夹具新增 `fake_key.pem`（已知 PrivateKey 检出）。selftest 照常运行（`--no-verification` 无网络需求）。

## Risks / Trade-offs

- [AGPL] 内部使用 + 不分发 = 无义务；与 semgrep 同一文档边界。
- [TruffleHog 对部分伪造样例不报（检测器带格式/熵校验）] → 夹具用真实格式的 PEM；预期清单以实测为准。
- [全 workdir 扫描略超"范围文件"边界] → 密钥场景宁可宽；文档注明。

## Open Questions

（无）
