# Design

## Context

内部使用前提解除 Semgrep 规则许可红线（用户 2026-09-23 确认）。复用 M2 的 venv 安装形态，引擎/规则运行时拉取，codespot 不分发规则。

## Decisions

### D1. 安装：venv + min_python 回退
registry 锁 `semgrep 1.177.0`（requires py≥3.10），`pip_deps_fallback` 用 `1.136.0`（支持 py3.9 的最新版，本机实测需求）。回退机制 M2 已有，零代码改动。

### D2. 规则集选择：适配器内置语言映射 + 项目覆盖
默认按 5.3 提案的语言表逐语言选 `p/<lang>`（多语言多 config）；`.codespot/config.json` 的 `"semgrep_config"` 整体覆盖（高级用户可指向自有规则目录）。不用 `--config auto` 做默认：auto 会按项目语言全量拉取，扫描面不可预测且每次判断语言有网络往返。

### D3. 调用与解析
`semgrep scan --json --quiet --config <c1> --config <c2> <files...>`；文件多时无需分批（semgrep 自己处理目标列表；>100 文件改用目录+--include 后缀过滤）。退出码 0=无发现、1=有发现、2=错误。`--quiet` 防止进度条污染 stdout。severity 映射 ERROR→major / WARNING→minor / INFO→info（semgrep 的 ERROR 多为安全类，但不确定到 critical 的程度，映射保守；可经 severity-overrides 提级）。

### D4. scope 语言表扩展
只改 SUPPORTED_LANGS 增后缀；不动排除规则。yaml 双后缀、dockerfile 无后缀文件（Dockerfile 名）不特殊处理——`.yaml` 归 yaml，Dockerfile 无后缀检测不到（记录为限制，语义上 semgrep tf/dockerfile 规则可后续用 config 覆盖启用）。

### D5. 网络
首次拉取规则需联网（semgrep 缓存于 ~/.semgrep）；`--timeout-threshold` 不需要，适配器 subprocess 超时 600s。断网+无缓存 → 引擎失败路径（既有 engine_errors 机制）。

## Risks / Trade-offs

- [registry 规则拉取慢（首次 p/python 数千条）] → 仅首次；后续命中本地缓存。
- [semgrep 1.x 内部版本差异（3.9 回退版 1.136 与 4.x 规则兼容性）] → 规则 schema 向后兼容度高，遇到个别不兼容规则 semgrep 会告警跳过。
- [Dockerfile 无后缀检测不到] → 记录为已知限制。

## Open Questions

（无）
