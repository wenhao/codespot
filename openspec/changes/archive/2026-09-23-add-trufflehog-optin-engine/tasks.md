# Tasks

## 1. 安装与 opt-in 机制

- [x] 1.1 registry 新增 trufflehog 3.97.6（tar.gz 形态，category=secrets_deep，opt_in=true）；setup 安装且幂等；验证：`--version` 正常
- [x] 1.2 主控 scan 新增 `--engine <name>` 可重复参数；select_engines 支持 opt_in（显式命名或 config `rules.secrets_deep.enabled` 激活，disabled 优先）；验证：未指定时不调度，指定后调度

## 2. 适配器

- [x] 2.1 实现 engine_trufflehog.py：NDJSON 逐行解析（跳过日志行）、字段映射（DetectorName/Description/file/line/Redacted/Verified）、severity=critical、本地脱敏兜底；验证：夹具 PEM 检出 PrivateKey、verified 字段存在

## 3. 收尾

- [x] 3.1 夹具 fake_key.pem + expected.json（trufflehog: PrivateKey）+ rules-severity（secrets_deep 默认 critical）；selftest 全绿；验证：`codespot selftest`
- [x] 3.2 SKILL.md 密钥深度检测提示 + README（矩阵行、opt-in 用法、AGPL 边界）；验证：文档一致
- [x] 3.3 端到端验收：kaipanla 默认扫描不含 trufflehog；`--engine trufflehog` 时深度层工作且品牌渲染正常；验证：输出人工复核
