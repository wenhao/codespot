# Proposal

## Why

AI 语义审查按文件逐个读代码，全量仓库（数百文件）审查耗时长、token 成本高，与"日常增量随手扫"的产品节奏不符。全量档位应默认跳过 AI 审查并提醒用户，用户显式要求时仍可开启。

## What Changes

- 有效档位为 `all`（含 auto 降级到 all）时，AI 引擎默认不被调度（不生成 ai-plan.json）。
- 提醒：CLI stdout 输出一行"全量扫描已跳过 AI 审查（--engine ai 可开启）"；SKILL.md 指示 agent 在摘要中向用户转述该提示与开启方式。
- 开启途径：显式 `--engine ai`，或 config `rules.ai_review.enabled: true`（视为永久显式开启，全量也跑）。
- config `disabled: true` 时行为不变（不调度、不提醒——用户已自行关闭）。
- README 英中 + SKILL.md 同步。

## Capabilities

### Modified Capabilities
- `ai-review-engine`: 默认开启语义细化——增量档位默认开、全量档位默认跳过并提示、两种显式开启途径。

## Impact

- 仅主控调度（select_engines 增加有效档位判断）与提示输出；引擎适配器不动。
