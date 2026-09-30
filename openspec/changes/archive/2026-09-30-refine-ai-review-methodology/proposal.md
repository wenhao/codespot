# Proposal

## Why

用户决策不集成 open-code-review 引擎（避免 LLM 后端配置），改为**吸收其工程方法论**强化内置 agent 审查：语义分 bundle（相关文件成组、bundle 级隔离评审）、精度优先证据门槛（宁漏报不误报）、定位纪律强化（锚定行不符必须重新定位）。零新依赖、零配置面、许可零变化。

## What Changes

- `engine_ai.py` 计划生成升级：目标文件按"同目录 + import 共现"聚类为 bundles（同模块必同组、有调用关系的跨目录文件并组）；超限时按 bundle 边界分轮（替换纯数量切批）；plan 结构新增 `bundles` 字段（每 bundle 文件清单），保留总清单向后兼容。
- SKILL.md AI 审查工作流：
  - P1 逐 bundle 评审（bundle 内文件互为上下文，跨文件契约核对以 bundle 为单位），完成一个再下一个；
  - P2 证据门槛写死：每条发现必须有可指认的代码证据（问题行或紧邻上下文）；推测性意见不写；confidence=low 且无直接证据的发现直接丢弃（不降级保留）；
  - P3 定位纪律升级：提交前重读锚定行，行内容与描述不符必须重新定位，禁止硬写（从"应当"升为"否则不提交"）。
- 不包含：bundle 级子代理并行（列为后续观察项）；OCR 引擎集成（已决策不做）。

## Capabilities

### Modified Capabilities
- `ai-review-engine`: 审查计划生成要求升级（bundle 聚类）；新增证据门槛与定位纪律的 agent 行为要求（SKILL.md 承载）。

## Impact

- engine_ai.py 约 +40 行（聚类）；SKILL.md 措辞；无其他代码路径；selftest/e2e 回归。
