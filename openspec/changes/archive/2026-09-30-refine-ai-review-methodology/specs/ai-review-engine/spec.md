# Spec Delta

## MODIFIED Requirements

### Requirement: 审查计划生成

AI 引擎适配器被调度时（增量档位默认、`--engine ai` 或 config `rules.ai_review.enabled`）SHALL 写出 `.codespot/ai-plan.json`：目标文件清单（含行数）、统一 issue 输出 schema 与一条示例、审查重点清单（逻辑正确性/边界条件/并发与竞态/错误处理缺口/资源泄漏/跨文件一致性/安全隐患，明确**不与静态工具已覆盖的规则类问题重复**）、以及 **bundles 字段**——目标文件按"同目录优先 + import/调用共现"聚类后的分组（同目录文件必同组；检测到 import 关系的跨目录文件并组；无法关联的文件各自成组）。超过 40 文件或 5000 行时的分轮指引 SHALL 以 bundle 为最小单位切分（不再按文件数量机械切批）。随后返回空结果退出 0，并在 stderr 提示后续步骤。

#### Scenario: 计划文件生成

- **WHEN** 执行 `codespot scan --engine ai` 且范围含 .py 文件
- **THEN** `.codespot/ai-plan.json` 存在且含文件清单、schema、示例与审查重点；scan 正常完成（该引擎 0 发现）

#### Scenario: bundle 聚类

- **WHEN** 范围含 `src/a/m1.py`、`src/a/m2.py`（同目录）与 `src/a/m1.py` import 的 `src/b/helper.py`
- **THEN** plan 的 bundles 中 m1/m2/helper 归入同一 bundle

## ADDED Requirements

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
