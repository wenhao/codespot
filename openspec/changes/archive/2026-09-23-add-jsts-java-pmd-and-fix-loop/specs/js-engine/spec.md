# Spec Delta

## ADDED Requirements

### Requirement: 双层扫描与去重

JS/TS 引擎 SHALL 先运行 oxlint（快速层），再对同一文件集运行 ESLint + eslint-plugin-sonarjs（深度层）；深度层配置 MUST 启用 `eslint-plugin-oxlint` 的关闭清单以避免与快速层重复报告。两层结果合并为统一 issue 输出：oxlint 规则带 `tool=oxlint`，sonarjs 规则带 `tool=eslint-sonarjs`。

#### Scenario: 同一问题不重复报告

- **WHEN** 夹具 JS 文件含一条 oxlint 与 ESLint 都会命中的规则
- **THEN** 合并结果中该问题只出现一次（来自其归属层）

#### Scenario: sonarjs 规则可检出

- **WHEN** 夹具含一条 sonarjs 独有规则命中（如 S1481 未使用变量）
- **THEN** 深度层产出 tool=eslint-sonarjs 的 issue，severity 按映射（bug 类 major+）

### Requirement: 深度层优雅降级

node/npm 或深度层依赖不可用时，引擎 SHALL 仅运行 oxlint 层并在 stderr 标注 `degraded` 及原因，整体退出码仍为 0（成功）；完全无法运行任何层时才退出 2。

#### Scenario: 无 npm 环境降级

- **WHEN** 机器无 npm 而目标文件为 .js
- **THEN** 仅产出 oxlint 发现，stderr 含 degraded 原因，适配器退出 0
