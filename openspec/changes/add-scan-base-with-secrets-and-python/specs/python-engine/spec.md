# Spec Delta

## Purpose

定义 ruff Python 质量扫描适配行为：JSON 输出解析、fix 建议透传、规则链接。

## ADDED Requirements

### Requirement: JSON 输出与 fix 透传

适配器 SHALL 以 `ruff check --output-format json` 运行并解析其 JSON；每条违规转为统一 issue；ruff 的 `fix` 字段（若存在）MUST 透传到 issue 的 `fixHint`。

#### Scenario: fix 建议可用

- **WHEN** 夹具包含一条 ruff 可自动修复的违规（如未使用的 import）
- **THEN** 对应 issue 的 fixHint 非空，且包含可应用的编辑信息

### Requirement: 默认规则面

适配器 SHALL 使用内置默认配置（assets 中预置）：启用 correctness/suspicious 等质量类规则族（含 flake8-bandit 的 S 规则族高危项），不启用格式风格类规则（formatter 职责）；目标文件列表通过 `--file-list` 或临时清单传入，只扫范围内文件。

#### Scenario: 只扫目标文件

- **WHEN** 仓库有 100 个 py 文件而范围清单只有 2 个
- **THEN** ruff 进程的输入清单仅含这 2 个文件，报告只含这 2 个文件的发现

### Requirement: 规则链接与映射

每条 issue 的 ruleUrl SHALL 指向 `https://docs.astral.sh/ruff/rules/<rule 小写>/`；severity 按映射表：S 规则族高危（如 S101/S102/S105-S108）→ critical，其余 S 族 → major，F/E 族 → major，W/PL 等 → minor。

#### Scenario: ruleUrl 可解析

- **WHEN** issue 的 rule 为 S101
- **THEN** ruleUrl 为 https://docs.astral.sh/ruff/rules/assert/
