# ai-review-engine Specification

## Purpose
TBD - created by archiving change add-ai-review-engine. Update Purpose after archive.

## Requirements

### Requirement: 审查计划生成

AI 引擎适配器被调度时（`scan --engine ai` 或 config `rules.ai_review.enabled`）SHALL 写出 `.codespot/ai-plan.json`：目标文件清单（含行数）、统一 issue 输出 schema 与一条示例、审查重点清单（逻辑正确性/边界条件/并发与竞态/错误处理缺口/资源泄漏/跨文件一致性/安全隐患，明确**不与静态工具已覆盖的规则类问题重复**）、超过 40 文件或 5000 行时的分批指引；随后返回空结果退出 0，并在 stderr 提示后续步骤（agent 分析 → 写 ai-result.json → absorb）。

#### Scenario: 计划文件生成

- **WHEN** 执行 `codespot scan --engine ai` 且范围含 .py 文件
- **THEN** `.codespot/ai-plan.json` 存在且含文件清单、schema、示例与审查重点；scan 正常完成（该引擎 0 发现）

### Requirement: absorb 校验与合并

`codespot ai-scan absorb` SHALL 读取 `.codespot/ai-result.json` 并逐条校验：必填字段（rule/severity/file/line/message）、severity 归一到四级（非法值拒绝）、file 必须存在于 workdir、line 在文件行数范围内（越界条目拒绝并报告）、`rule` 未带 `AI-` 前缀时自动补全；`confidence` 字段（high/medium/low）透传。校验通过的条目经统一 issue 构造（赋 csId、severity 归一）后**替换式合并**：移除最近报告中全部 `tool=ai` 条目再追加新条目，重算 summary，重写 report.json 与 report.md；全部条目非法时退出 2 且不改动报告。

#### Scenario: 合并进报告

- **WHEN** ai-result.json 含 2 条合法发现（1 critical 1 major）且原报告已有 1 条旧 AI 发现
- **THEN** absorb 后报告恰好含 2 条 `tool=ai` 发现（旧条目被替换），summary 相应更新，两份报告均重写

#### Scenario: 非法条目拒绝

- **WHEN** 某条目的 line 超出文件行数
- **THEN** 该条目被拒绝并逐条报告原因；其余合法条目照常合并

### Requirement: 与工具发现的互补边界

AI 审查的审查重点 SHALL 指向静态规则无法覆盖的语义级问题；AI 发现以 `tool=ai`、规则前缀 `AI-` 标识，进入与工具发现相同的品牌层（CS 编号）、排序与双层配置（`rules.ai_review.disabled/ignore`）；文档须注明 AI 发现为**建议性**（advisory），呈现时附 confidence。

#### Scenario: AI 发现走品牌层

- **WHEN** absorb 后查看 report.md
- **THEN** AI 发现以 CS 编号呈现（无引擎名暴露），report.json 中带 tool=ai 与 confidence

### Requirement: 默认开启与关闭

AI 审查引擎 SHALL 默认参与每次 `codespot scan`（always_on：随扫描生成 `.codespot/ai-plan.json`，agent 按三步工作流执行：读计划 → 分析写 ai-result.json → `codespot ai-scan absorb`）。项目可通过 `.codespot/config.json` 的 `rules.ai_review.disabled: true` 整体关闭；用户在对话中明确表示"只扫不审"时 agent 亦可跳过 AI 审查步骤。运行模式保持 agent 驱动、无外部 API。

#### Scenario: 默认扫描包含 AI 审查

- **WHEN** 执行 `codespot scan --scope auto`（未显式指定引擎、未配置关闭）
- **THEN** ai 引擎被调度，`.codespot/ai-plan.json` 生成，agent 工作流包含审查三步

#### Scenario: 配置关闭后不参与

- **WHEN** config.json 设置 `{"rules": {"ai_review": {"disabled": true}}}` 并扫描
- **THEN** ai 引擎不被调度，无 ai-plan.json 生成
