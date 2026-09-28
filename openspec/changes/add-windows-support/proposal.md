# Proposal

## Why

用户需要在 Windows 上运行 codespot。主控为纯 Python 标准库天然兼容，但安装器与部分引擎调用存在平台假设（os 映射缺失、shell wrapper、venv bin 目录、exe 后缀、`file:///C:/` URI）。Semgrep CE 官方不支持 Windows 原生，需平台白名单排除并提示。

## What Changes

- registry：各平台二进制引擎补 `windows` 的 os/arch/ext 映射（gitleaks/ruff/oxlint/trufflehog=zip、osv-scanner=raw `.exe`、PMD/SpotBugs 复用 zip）；semgrep 声明 `platforms: [darwin, linux]`。
- 安装器：统一 `resolve_engine_cmd`（name/name.exe/bin//Scripts/ 多路径解析）；Windows 分支——venv 用 `python` 且工具在 `Scripts\`、wrapper 形态直接指向发行包自带 `.bat`（不再生成 sh）、raw_binary 带 `.exe` 后缀。
- 调度：按 registry `platforms` 过滤，被平台排除的引擎不调度也不计 engine_errors，stdout 一行提示；selftest 同样跳过并注明。
- engine_java：Windows 下以 `cmd /c` 调 `.bat`；`file:///C:/...` URI 剥前导斜杠。
- 文档：README 英中 Windows 安装（复制/mklink、python 调用）与平台说明更新。
- 新增 GitHub Actions `windows-latest` CI：setup 全引擎 + selftest + 演示仓库 scan，作为真实 Windows 验证。

## Capabilities

### Modified Capabilities
- `scan-orchestration`: setup 安装形态的 Windows 语义；调度增加平台白名单过滤。

## Impact

- registry.json/setup_engine.py/codespot/engine_java.py/各适配器 find_*（统一解析）；无契约变化；本地（macOS）回归 selftest，Windows 由 CI 验证。
