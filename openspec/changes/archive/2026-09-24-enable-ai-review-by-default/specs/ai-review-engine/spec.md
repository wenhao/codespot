# Spec Delta

## REMOVED Requirements

### Requirement: opt-in 触发

**Reason**: AI 语义审查为核心差异化能力，用户决策改为默认开启，不再要求显式点名。

**Migration**: `--engine ai` 参数保留且幂等（语义不变）；原以 config `rules.ai_review.enabled: true` 启用的项目无需改动（enabled 字段被忽略，默认即开启）。

## ADDED Requirements

### Requirement: 默认开启与关闭

AI 审查引擎 SHALL 默认参与每次 `codespot scan`（always_on：随扫描生成 `.codespot/ai-plan.json`，agent 按三步工作流执行：读计划 → 分析写 ai-result.json → `codespot ai-scan absorb`）。项目可通过 `.codespot/config.json` 的 `rules.ai_review.disabled: true` 整体关闭；用户在对话中明确表示"只扫不审"时 agent 亦可跳过 AI 审查步骤。运行模式保持 agent 驱动、无外部 API。

#### Scenario: 默认扫描包含 AI 审查

- **WHEN** 执行 `codespot scan --scope auto`（未显式指定引擎、未配置关闭）
- **THEN** ai 引擎被调度，`.codespot/ai-plan.json` 生成，agent 工作流包含审查三步

#### Scenario: 配置关闭后不参与

- **WHEN** config.json 设置 `{"rules": {"ai_review": {"disabled": true}}}` 并扫描
- **THEN** ai 引擎不被调度，无 ai-plan.json 生成
