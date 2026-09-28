# Spec Delta

## MODIFIED Requirements

### Requirement: 默认开启与关闭

AI 审查引擎 SHALL 默认参与**增量档位**（uncommitted / unpushed / ref）的每次 `codespot scan`（随扫描生成 `.codespot/ai-plan.json`，agent 按三步工作流执行）。**全量档位（有效 scope 为 `all`，含 auto 降级）默认不调度 AI 引擎**，且 MUST 在 CLI stdout 输出一行提示（说明已跳过及 `--engine ai` 开启方式），SKILL.md SHALL 指示 agent 转述该提示。全量下开启的途径：显式 `--engine ai`，或 config `rules.ai_review.enabled: true`（视为永久显式开启）。项目可通过 `.codespot/config.json` 的 `rules.ai_review.disabled: true` 整体关闭（此时不产生提示）；用户在对话中明确表示"只扫不审"时 agent 亦可跳过。运行模式保持 agent 驱动、无外部 API。

#### Scenario: 默认扫描包含 AI 审查

- **WHEN** 执行 `codespot scan --scope uncommitted`（未配置关闭）
- **THEN** ai 引擎被调度，`.codespot/ai-plan.json` 生成

#### Scenario: 全量默认跳过并提示

- **WHEN** 执行 `codespot scan --scope all`（未显式指定引擎、未配置开启/关闭）
- **THEN** ai 引擎不被调度、无 ai-plan.json，stdout 含"跳过 AI 审查"与开启方式的提示

#### Scenario: 显式开启后全量也运行

- **WHEN** 执行 `codespot scan --scope all --engine ai`
- **THEN** ai 引擎被调度且 ai-plan.json 生成

#### Scenario: config 永久开启

- **WHEN** config.json 设 `{"rules": {"ai_review": {"enabled": true}}}` 且执行 `--scope all`
- **THEN** ai 引擎被调度（等同显式开启）

#### Scenario: 配置关闭后不参与

- **WHEN** config.json 设置 `{"rules": {"ai_review": {"disabled": true}}}` 并扫描（任意档位）
- **THEN** ai 引擎不被调度，亦不产生跳过提示
