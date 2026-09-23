# Spec Delta

## Purpose

定义 codespot 主控 CLI 与扫描编排的对外行为：子命令、引擎注册、并行调度、失败隔离。用户与 AI agent 通过该 CLI 完成一次完整扫描。

## ADDED Requirements

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

多个适配器 SHALL 并行执行；单个引擎以退出码 2 失败（缺运行时、配置错误）MUST NOT 阻止其他引擎的结果合并，且该失败 MUST 以 `engine_errors` 字段出现在 report.json 中（含引擎名与原因摘要）。

#### Scenario: 一个引擎失败不影响整体报告

- **WHEN** ruff 二进制缺失但 gitleaks 正常，执行 scan
- **THEN** 报告仍包含 gitleaks 的发现，report.json 的 engine_errors 含 ruff 的失败原因，退出码为 0（扫描流程本身成功）

### Requirement: setup 幂等安装

`codespot setup` SHALL 按注册表下载引擎到 `~/.codespot/engines/<name>-<version>/`，版本锁定；重复执行 MUST 幂等（已存在且校验通过则跳过下载）；网络失败或运行时缺失 MUST 给出明确的缺失项与修复提示，且不写入半成品目录。

#### Scenario: 重复 setup

- **WHEN** 连续执行两次 `codespot setup`
- **THEN** 第二次的下载步骤全部跳过，退出码 0

#### Scenario: 网络失败不落半成品

- **WHEN** 下载 gitleaks 二进制中途失败
- **THEN** `~/.codespot/engines/` 下不残留该引擎的不完整目录，stderr 给出重试提示
