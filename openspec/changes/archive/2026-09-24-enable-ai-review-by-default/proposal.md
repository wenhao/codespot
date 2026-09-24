# Proposal

## Why

用户决策：AI 语义审查是 codespot 的核心差异化能力（补齐静态工具盲区），应默认开启，让每次标准扫描都包含 AI 审查，而不是要求用户记住 `--engine ai`。TruffleHog 深度密钥检测维持 opt-in 不变（外呼/耗时考量）。

## What Changes

- registry 的 `ai` 引擎：移除 `opt_in`，改为 `always_on: true`——每次 `codespot scan` 默认生成审查计划（ai-plan.json）。
- 关闭方式：`.codespot/config.json` 的 `rules.ai_review.disabled: true`（既有类别禁用机制，零新代码）；`--engine ai` 参数保留（幂等无害）。
- SKILL.md 工作流更新：标准流程在"读报告"后加入 AI 审查三步（读 plan → 分析 → absorb），再呈现修复选项；用户明确说"只扫不审"或 config 关闭时跳过。
- README（英/中）与两版汇报文档同步：ai_review 标注从 opt-in 改为"默认开启（可关闭）"，opt-in 段落仅剩 TruffleHug。

## Capabilities

### Modified Capabilities
- `ai-review-engine`: 触发语义从 opt-in 改为默认开启 + 可配置关闭。

## Impact

- registry.json 一处字段变更；SKILL.md/README/汇报文档文案；无代码逻辑改动（always_on 与 disabled 机制均已存在）。
