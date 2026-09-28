# Design

## Context

macOS 开发、Windows 由 CI（GitHub Actions windows-latest）验证。原则：平台差异集中在 setup_engine.py 与统一解析函数，适配器只调统一入口。

## Decisions

### D1. resolve_engine_cmd（setup_engine 新增，全部适配器复用）
`resolve_engine_cmd(name, inner_paths=("bin/{n}","Scripts/{n}"))`：在已安装引擎目录内依次尝试 name、name.exe、各 inner 路径及其 .exe 变体；返回可执行文件路径。八个 find_* 全部换用它——消除各适配器自写 glob 的平台假设。venv 引擎（bandit/sqlfluff/semgrep）在 Windows 的 `Scripts\` 由 inner_paths 覆盖。

### D2. 安装器 Windows 分支
- `IS_WINDOWS = platform.system()=="Windows"`；
- venv：解释器 `python`→`python3` 回退；min_python 检查用 venv 内 python（bin/ 或 Scripts/）；
- wrapper：layout 增加 `windows_binary`（bin/<name>.bat）；安装时不写 sh、不 chmod，`.ok` 校验经 `cmd /c <bat> --version`；
- raw_binary：目标为 name + ".exe"（Windows）；
- zip 内 exe：Windows 下解压即用（zip 不含执行位问题仅影响 macOS，已有 chmod）。

### D3. 平台白名单
registry `"platforms": ["darwin","linux"]`（缺省=全平台）；select_engines 与 selftest 循环都过滤；stdout 提示 "engine X unavailable on <os> (registry platforms: …)"。setup 对不支持平台直接报错跳过（继续其余）。

### D4. engine_java
PMD/SpotBugs 路径以 .bat 结尾时 `cmd = ["cmd","/c",path]+args`；`_uri_to_path` 对 `^/[A-Za-z]:` 剥前导斜杠。

### D5. CI
`.github/workflows/windows.yml`：windows-latest + Python 3.11 + Node 20；步骤 setup→selftest→临时 git 仓库 scan 冒烟。macOS 本地不执行 Windows 分支，依赖该工作流作为验收。

## Risks / Trade-offs
- [bat 引号/换行差异] → 参数均无空格路径外的复杂引用，CI 冒烟兜底。
- [TruffleHog filesystem 扫盘符路径] → 传绝对路径，Go 程序自身处理 Windows 路径。

## Open Questions
（无）
