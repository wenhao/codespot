# Proposal

## Why

codespot 已集成 9 个静态扫描引擎，但静态规则抓不住逻辑 bug、并发问题、错误处理缺口、跨文件不一致这类**语义级缺陷**。skill 本身运行在 AI agent 环境中——agent 就是现成的"AI 模型"，无需外部 API key、无额外成本。将 AI 代码审查作为 **opt-in 的 agent 驱动引擎**（类别 `ai_review`），复用 TruffleHog 批次建立的 opt-in 机制。

## What Changes

- registry 新增 `ai` 引擎：`opt_in: true`、`agent_driven: true`（适配器不调用外部模型，而是产出审查计划）、类别 `ai_review`、无安装物。
- 新增 `engine_ai.py`：按契约被调度时写 `.codespot/ai-plan.json`（目标文件清单含行数、统一 issue 输出 schema 与示例、审查重点清单、>40 文件分批指引），返回空结果并在 stderr 提示后续步骤。
- 主控新增 `codespot ai-scan absorb` 子命令：校验 `.codespot/ai-result.json`（必填字段、severity 归一、file 存在与行号范围检查、`AI-` 规则前缀自动补全、confidence 透传），经 `make_issue` 赋 csId，替换式合并进最近一次报告（移除旧 `tool=ai` 条目再追加），重算 summary 并重写双报告。
- SKILL.md 增加 AI 审查工作流：`scan --engine ai` → 读 plan → agent 自行分析（聚焦静态工具盲区，不与工具发现重复）→ 写 ai-result.json → `ai-scan absorb` → 呈现合并报告。
- README（英/中）同步：opt-in 用法、AI 发现的定位与边界（建议性、带 confidence）。

## Capabilities

### New Capabilities
- `ai-review-engine`: agent 驱动的 AI 代码审查——计划生成、结果 schema、absorb 校验合并、与工具发现的互补边界。

### Modified Capabilities
- `skill-workflow`: AI 审查触发与三步工作流指引。

## Impact

- 新增 engine_ai.py 与 ai-scan 子命令；registry +1（无下载）。不改既有引擎与契约。
- AI 发现以 `tool=ai`、规则前缀 `AI-` 标识，进品牌层（CS 编号）与双层配置（`rules.ai_review.disabled/ignore`）。
