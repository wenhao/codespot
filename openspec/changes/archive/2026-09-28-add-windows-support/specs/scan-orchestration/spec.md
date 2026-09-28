# Spec Delta

## MODIFIED Requirements

### Requirement: 引擎注册表驱动调度

调度 SHALL 由 `scripts/engines/registry.json` 驱动，并支持 **opt-in 引擎**：声明 `"opt_in": true` 的引擎默认不被调度，仅当 `scan --engine <name>` 显式命名、或 `.codespot/config.json` 的 `rules.<category>.enabled: true` 时被纳入。引擎可声明 `"platforms"` 白名单（如 semgrep 仅 darwin/linux）：当前平台不在白名单的引擎 MUST NOT 被调度、不计入 engine_errors，且 scan 的 stdout SHALL 输出一行平台提示（说明该引擎在本平台不可用）；其余调度语义不变。

#### Scenario: 默认不运行 opt-in 引擎

- **WHEN** 未显式指定且范围含 .py 文件
- **THEN** opt-in 引擎不被调度

#### Scenario: 显式命名后运行

- **WHEN** 执行 `codespot scan --engine trufflehog`
- **THEN** trufflehog 被调度并产出发现

#### Scenario: 无匹配引擎时不误调用

- **WHEN** 目标文件清单只含 `.py` 文件且本批仅注册了 secrets（常开）与 python 引擎
- **THEN** 调度恰好调用这两个适配器各一次，不调用未注册的 JS/Java/SQL 适配器

#### Scenario: 平台白名单排除并提示

- **WHEN** 在 Windows 上执行 scan 且 semgrep 声明 `platforms: [darwin, linux]`
- **THEN** semgrep 不被调度、engine_errors 为空（无其条目），stdout 含一行平台不可用提示

### Requirement: setup 幂等安装

setup SHALL 支持第四种安装形态 `raw_binary`：直接下载单文件二进制（URL 直链 release 资产，按 os/arch 映射；Windows 下目标文件带 `.exe` 后缀）到 `~/.codespot/engines/<name>-<version>/` 并加执行位（Windows 为空操作）；幂等与失败清理语义不变。

Windows 安装语义：① venv 形态在 Windows 用 `python`（无则失败得体）且 venv 工具位于 `Scripts\` 而非 `bin/`；② wrapper 形态（PMD/SpotBugs）在 Windows 直接采用发行包自带 `bin\<name>.bat`，不生成 shell 包装；③ 各安装形态的二进制解析 SHALL 统一支持 `name`/`name.exe` 后缀差异。

#### Scenario: 直链二进制安装

- **WHEN** 执行 `codespot setup osv-scanner`
- **THEN** 二进制从 release 直链下载、`--version` 校验通过；重复执行跳过

#### Scenario: 一个引擎失败不影响其余安装

- **WHEN** osv-scanner 安装失败但平台二进制引擎正常
- **THEN** setup 对其余引擎安装成功，对失败引擎打印原因并继续，整体退出码非零

#### Scenario: 重复 setup

- **WHEN** 连续执行两次 `codespot setup`
- **THEN** 第二次的下载步骤全部跳过，退出码 0

#### Scenario: 重复 setup 幂等

- **WHEN** 连续执行两次 `codespot setup`
- **THEN** 第二次全部跳过，退出码 0

#### Scenario: 网络失败不落半成品

- **WHEN** 任一形态的安装中途失败
- **THEN** `~/.codespot/engines/` 下不残留该引擎的不完整目录，stderr 给出重试提示

#### Scenario: Windows venv 工具路径

- **WHEN** 在 Windows 上 setup venv 形态引擎（bandit/sqlfluff）
- **THEN** 安装成功且工具可从 `Scripts\` 目录解析调用
