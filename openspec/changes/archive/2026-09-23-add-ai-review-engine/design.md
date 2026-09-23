# Design

## Context

skill 运行在 AI agent 内——agent 即模型，无需外部 API/Key/联网。AI 审查定位为静态工具盲区的语义级补充，opt-in 复用 TruffleHog 批次机制。

## Decisions

### D1. agent_driven 引擎形态
registry 条目 `agent_driven: true`：适配器不产发现，只产"审查计划"（契约内合法：退出 0 + 空结果 + stderr 指引）。这样 `scan --engine ai` 与其他引擎统一调度、报告不破，agent 后续补上结果。

### D2. 计划内容与成本控制
ai-plan.json：files[{path,lines}]、schema、1 条示例、审查重点（7 项语义维度 + "勿与规则类问题重复"）、>40 文件或总行数 >5000 时附分批指引（agent 分多轮每轮 ≤40 文件）。行数统计用 wc 近似（快）。

### D3. absorb 的替换式合并
读 report.json → 过滤掉旧 tool=="ai" → 追加新校验条目（经 common.make_issue 得 csId/severity 归一，tool="ai"，rule 自动补 `AI-` 前缀）→ 重排序（同 SEV_ORDER）→ 重算 summary → _write_reports 复用。非法条目逐条 stderr 报告；**合法条目照常合并**（部分成功优于全或无），仅在零合法条目且存在非法条目时退出 2。

### D4. confidence 透传
可选字段 high/medium/low，透传进 issue；report.md 渲染 AI 条目时在 message 后附 `(confidence: high)`——为品牌层服务，md 不出现 "ai" 以外的工具名（"ai" 是 codespot 自身能力名，允许）。

### D5. 规则命名
agent 自拟语义化规则名（如 `AI-off-by-one`、`AI-unhandled-race`）；absorb 强制前缀，csId 由 tool="ai"+rule 派生保持稳定。ruleUrl 置空。

## Risks / Trade-offs

- [agent 产出质量参差] → schema 校验 + confidence + SKILL.md 指引"每条发现给依据"；呈现时 AI 类标注建议性。
- [大仓库成本] → 计划层分批指引；absorb 支持多次调用（每次替换全部 AI 条目）。
- [行号漂移（分析期间文件被改）] → absorb 校验 line 在文件行数内，越界拒绝。

## Open Questions

（无）
