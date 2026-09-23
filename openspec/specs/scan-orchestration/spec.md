# scan-orchestration Specification

## Purpose
定义 codespot 主控 CLI 与扫描编排的对外行为：子命令、引擎注册、并行调度、失败隔离。用户与 AI agent 通过该 CLI 完成一次完整扫描。

## Requirements

### Requirement: 主控 CLI 入口

`codespot` CLI（scripts/codespot，Python 3，仅标准库）SHALL 提供子命令 `setup`、`scope`、`scan`、`report`、`selftest`，其中 `scan` MUST 串联"范围计算 → 引擎调度 → 合并归一 → 双报告"完整流程。

#### Scenario: 一次完整扫描

- **WHEN** 在一个含未提交 Python 文件（内含已知 ruff 违规）的 git 仓库执行 `codespot scan --scope uncommitted`
- **THEN** 命令成功退出，且 `.codespot/report.json` 与 `.codespot/report.md` 均被生成

### Requirement: 引擎注册表驱动调度

调度 SHALL 由 `scripts/engines/registry.json` 驱动：注册表 MUST 为每个引擎声明语言匹配（glob 或语言标识）、是否常开（always_on）、setup 命令与版本锁定；主控 SHALL 只对"语言层引擎匹配到目标文件，或常开引擎且目标文件非空"的组合调用适配器。

#### Scenario: 无匹配引擎时不误调用

- **WHEN** 目标文件清单只含 `.py` 文件且本批仅注册了 secrets（常开）与 python 引擎
- **THEN** 调度恰好调用这两个适配器各一次，不调用未注册的 JS/Java/SQL 适配器

### Requirement: 引擎并行与失败隔离

多个适配器 SHALL 并行执行；单个引擎以退出码 2 失败（缺运行时、配置错误）MUST NOT 阻止其他引擎的结果合并。失败信息按双层呈现：report.json 的 `engine_errors` 保留真实引擎键（agent 内部接口）；report.md SHALL 以类别别名中性表述（"检查模块提示"），不出现引擎名。

#### Scenario: 一个引擎失败不影响整体报告

- **WHEN** ruff 二进制缺失但 gitleaks 正常，执行 scan
- **THEN** 报告仍包含 gitleaks 的发现，report.json 的 engine_errors 含 ruff 的失败原因，退出码为 0；report.md 中的对应提示只出现类别别名"python_lint"，无引擎名

### Requirement: setup 幂等安装

setup SHALL 支持两种安装形态：平台二进制（tar.gz，M0 已有）与 npm 项目（在 `~/.codespot/engines/<name>-<version>/` 内 `npm install` 锁定版本）；单引擎安装失败 MUST 中止该引擎并继续其余引擎（逐引擎降级），最终以非零码提示存在失败项；scan 时将"未安装且被需要"的引擎记为 engine_error。

#### Scenario: 一个引擎失败不影响其余安装

- **WHEN** npm 引擎安装失败（npm 缺失）但平台二进制引擎正常
- **THEN** setup 对二进制引擎安装成功，对失败引擎打印原因并继续，整体退出码非零

#### Scenario: 重复 setup

- **WHEN** 连续执行两次 `codespot setup`（混合形态引擎）
- **THEN** 第二次的下载与 npm install 全部跳过，退出码 0

#### Scenario: 网络失败不落半成品

- **WHEN** 任一形态的安装中途失败
- **THEN** `~/.codespot/engines/` 下不残留该引擎的不完整目录，stderr 给出重试提示
