# ai-review-engine Specification

## Purpose
TBD - created by archiving change add-ai-review-engine. Update Purpose after archive.

## Requirements

### Requirement: 审查计划生成

AI 引擎适配器被调度时（增量档位默认、`--engine ai` 或 config `rules.ai_review.enabled`）SHALL 写出 `.codespot/ai-plan.json`：目标文件清单（含行数）、统一 issue 输出 schema 与一条示例、审查重点清单（逻辑正确性/边界条件/并发与竞态/错误处理缺口/资源泄漏/跨文件一致性/安全隐患，明确**不与静态工具已覆盖的规则类问题重复**）、以及 **bundles 字段**——目标文件按"同目录优先 + import/调用共现"聚类后的分组（同目录文件必同组；检测到 import 关系的跨目录文件并组；无法关联的文件各自成组）。超过 40 文件或 5000 行时的分轮指引 SHALL 以 bundle 为最小单位切分（不再按文件数量机械切批）。随后返回空结果退出 0，并在 stderr 提示后续步骤。

#### Scenario: 计划文件生成

- **WHEN** 执行 `codespot scan --engine ai` 且范围含 .py 文件
- **THEN** `.codespot/ai-plan.json` 存在且含文件清单、schema、示例与审查重点；scan 正常完成（该引擎 0 发现）

#### Scenario: bundle 聚类

- **WHEN** 范围含 `src/a/m1.py`、`src/a/m2.py`（同目录）与 `src/a/m1.py` import 的 `src/b/helper.py`
- **THEN** plan 的 bundles 中 m1/m2/helper 归入同一 bundle

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

### Requirement: 精度优先的证据门槛

AI 审查工作流（SKILL.md）SHALL 写死证据门槛：每条发现必须有**可指认的代码证据**（问题行本身或紧邻上下文）；无法指出具体证据的推测性意见不得写入结果；confidence=low 且无直接证据的发现应直接丢弃（而非降级保留）。整体取向为精度优先——宁漏报不误报。

#### Scenario: 无证据的推测不产出

- **WHEN** agent 认为某处"可能存在并发问题"但无法指出具体的交错路径或共享状态
- **THEN** 该意见不写入 ai-result.json

### Requirement: 定位纪律

AI 发现的行号锚定 SHALL 遵守：提交（写 ai-result.json）前重读锚定行，行内容与发现描述不符时必须重新定位到问题可见行，禁止以方法签名行或代码块首行顶替（否则不得提交该条）。

#### Scenario: 锚定不符必须重定位

- **WHEN** agent 完成一条发现后发现所记行号的内容与描述不一致
- **THEN** 重新定位后再写入；无法定位则放弃该条
