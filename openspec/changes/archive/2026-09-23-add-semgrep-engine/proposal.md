# Proposal

## Why

codespot 现有 6 引擎覆盖 Python/JS-TS/Java/SQL，缺少跨语言语义/taint 分析，且不支持 Go、C#、Kotlin、Ruby、PHP、Rust、Terraform 等语言。codespot 定位为**公司内部使用、不售卖**——Semgrep Rules License v1.0 明确允许 "internal business purposes"，因此官方 registry 规则（2800+ 条）可以合法使用，Semgrep CE 是补齐上述缺口的最优引擎。

## What Changes

- registry 新增 `semgrep` 条目：venv 安装形态，锁定 1.177.0（py≥3.10），本机 3.9 环境自动回退 1.136.0。
- 新增 `engine_semgrep.py`：跨语言语义扫描——按目标文件语言选择 registry 规则集（py→p/python、go→p/go、ts/js→p/typescript+p/javascript 等，映射表在适配器内维护）；项目可用 `.codespot/config.json` 的 `"semgrep_config"` 覆盖默认规则集（如 `auto` 或自定义规则目录）；JSON 输出解析为统一 issue（severity ERROR→major、WARNING→minor、INFO→info，CWE/参考文献透传）。
- 首次运行需联网拉取规则（semgrep 自动缓存，之后可离线）；拉取失败得体降级为引擎失败（engine_error），不阻塞其他引擎。
- `scripts/scope.py` 语言检测扩展：go/rb/php/kt/rs/cs/c/cpp/h/tf/yaml/dockerfile 等后缀（供 semgrep 匹配）。
- SKILL.md/README 更新语言矩阵与"内部使用"许可边界说明。
- 不包含：自写规则包、semgrep 规则的分发。

## Capabilities

### New Capabilities
- `semgrep-engine`: Semgrep CE 适配——语言→规则集映射、内部使用许可边界、JSON 解析、severity 映射、网络降级。

### Modified Capabilities
- `scan-scope`: 语言检测后缀扩展（go/rb/php/kt/rs/cs/c/cpp/tf/yaml 等）。

## Impact

- 新增 scripts/engines/engine_semgrep.py；registry/setup 复用 venv 形态无代码改动（除非验证发现缺口）；scope.py 语言表扩展。
- 运行时依赖：python3（semgrep 装独立 venv）；首次扫描需联网拉规则。
- 许可边界：semgrep 引擎与规则仅限公司内部使用，不得随 codespot 对外分发。
