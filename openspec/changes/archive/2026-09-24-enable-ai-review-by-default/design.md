# Design

## Context

单字段行为翻转 + 文档同步。always_on 与 category disabled 机制均已存在（M0/品牌批次），无新代码路径。

## Decisions

### D1. registry 一处变更
`ai` 引擎：删除 `opt_in: true`，置 `always_on: true`。`agent_driven` 保留（调度与执行两处已放行）。`--engine ai` 保留：requested 集合包含恒真，幂等无害，兼容既有肌肉记忆。

### D2. config 语义
关闭唯一途径 `rules.ai_review.disabled: true`；`enabled` 字段自此冗余（默认即开），文档不再宣传，出现时不报错（向后兼容）。

### D3. SKILL.md 流程位次
标准流程：扫描 → 读报告 → **AI 审查三步（plan 默认已生成）→ absorb 合并** → 摘要与修复选项（基于合并后报告）。用户说"只扫不审"或 config 关闭 → 跳过审查直接呈现。密钥深度检测提示（TruffleHog）保持 opt-in 话术。

## Risks / Trade-offs

- [每次扫描都做语义审查增加 token 成本] → plan 有 40 文件/5000 行分批上限；用户可"只扫不审"或 config 关闭；报告如实呈现审查是否执行。
- [absorb 前用户就看报告的时序] → SKILL.md 规定 absorb 后才呈现修复选项，避免基于未合并报告决策。

## Open Questions

（无）
