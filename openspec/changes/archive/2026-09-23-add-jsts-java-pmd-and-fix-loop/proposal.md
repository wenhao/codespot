# Proposal

## Why

M0 已建立基座与两个 P0 引擎（gitleaks + ruff）。本批（调研报告里程碑 M1）补齐核心三语言中的另外两个：JS/TS（oxlint 快速层 + ESLint/sonarjs 深度层）与 Java（PMD 源码级），并实现产品核心体验——**AI 修复循环**（SKILL.md 编排：修复选项 → agent 修复 → 重扫验证 ≤3 轮）。

## What Changes

- 新增 `engine_js.py`：双引擎编排——先跑 oxlint（快），再跑 ESLint+eslint-plugin-sonarjs（深），用 `eslint-plugin-oxlint` 的关闭清单避免重复报告；oxlint 经 GitHub Releases 单二进制安装（无 npm 依赖），ESLint 深度层经 npm 安装到 `~/.codespot/engines/eslint-layer/`（需要 node/npm，缺失时优雅降级为仅 oxlint 层）。
- 新增 `engine_java.py`：PMD 7 源码级扫描（zip 包下载到引擎缓存，`check` + 内置 quickstart 规则集，SARIF 输出解析，rank→severity 映射）；JRE 缺失时报告 engine_error 而非静默跳过。
- SKILL.md 升级为**修复循环**工作流：用户选择修复范围 → agent 逐条判断合理性并修复 → 重扫验证 → ≤3 轮收敛 → 汇总；新增 `.codespot/ignore` 误报登记指引。
- registry.json 新增 oxlint / eslint-layer / pmd 三个条目；setup 支持平台二进制与 npm 两种安装形态。
- 夹具扩充：JS（含 sonarjs 已知规则命中）与 Java（含 PMD 已知规则命中）夹具及预期清单。
- 本批**不包含**：SpotBugs/FindSecBugs、bandit、SQLFluff（M2）；sonarlint-ls（M3）。

## Capabilities

### New Capabilities
- `js-engine`: JS/TS 双层扫描——oxlint 快速层 + ESLint/sonarjs 深度层 + 去重与降级策略。
- `java-engine`: PMD 适配——源码级扫描、SARIF 解析、rank→severity 映射、JRE 探测。
- `fix-loop`: AI 修复循环编排——修复范围选项、合理性判断、重扫验证、轮次上限、误报登记。

### Modified Capabilities
- `scan-orchestration`: setup 需支持两种安装形态（平台二进制 / npm 项目）并逐引擎降级；扫描调度需将"可选运行时缺失"记为 engine_error。
- `skill-workflow`: 触发描述扩展（Java/JS 项目）；编排指令从"呈现选项"升级为完整修复循环。

## Impact

- 新增 scripts/engines/engine_js.py、engine_java.py、eslint-layer 安装逻辑；assets 增加 eslint flat config 与 oxlint 配置、PMD 规则集。
- 运行时依赖新增：node/npm（仅 ESLint 深度层，可选）、JRE 8+（仅 Java 引擎）。
- registry/安装器/夹具/selftest 同步扩展；不改 M0 契约（engine-contract 不变）。
