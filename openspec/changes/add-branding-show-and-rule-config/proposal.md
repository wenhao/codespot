# Proposal

## Why

三个用户体验需求：① 对人类用户只呈现 codespot 品牌，不暴露底层开源引擎名称（agent 内部接口不受限）；② 用户需要"先浏览问题详情再决定修复范围"的入口；③ 需要按项目删减规则或调整参数。已确认方案：呈现层改名（CS-ID）、`codespot show` 详情子命令、双层规则配置（config.json 简单开关 + 项目原生配置文件优先）。

## What Changes

- **品牌层**：每条 issue 生成稳定的对外规则编号 `CS-xxxxx`（由 tool+rule 哈希派生，跨次扫描稳定）；`report.md` 全面 codespot 化——只显示 CS 编号/分级/文件行号/说明，不再出现 ruff、bandit、oxlint、sonarjs、PMD、gitleaks 等名称，也不再放引擎官方文档链接；`report.json` 作为 agent 内部接口**保留**原始 `tool`/`rule`/`ruleUrl` 字段（另新增 `csId`）。
- **详情子命令**：`codespot show` 支持按 `--severity`、`--file`（前缀）、`--rule`（CS 编号）、`--limit` 过滤浏览详情；SKILL.md 修复选项增加"先查看问题详情"，agent 用 show 分批呈现后回到修复选项循环。
- **双层规则配置**：`.codespot/config.json` 新增 `"rules"` 段，以**检查类别**为键（python_lint/python_security/js_lint/java/sql/secrets/semantic——不暴露引擎名），支持 `disabled`（整体关）、`ignore`（规则删减）；ruff/oxlint/sqlfluff 等若在用户项目发现原生配置文件（`.ruff.toml`、`.oxlintrc.json`、`.sqlfluff` 等）则**优先采用**（不与内置默认合并）；参数级调整走原生配置。registry 为每个引擎声明 `category` 别名。
- 本批不包含：CS 编号到官方文档的反查文档页；PMD ruleset 的项目级删减（仅支持整体 disabled 与原生 ruleset 路径覆盖）。

## Capabilities

### New Capabilities
- `branding`: CS-ID 稳定派生、呈现层品牌隔离的边界（人读报告无引擎名，agent 接口保留内部字段）。
- `issue-details`: `codespot show` 详情浏览——过滤参数与输出格式。
- `rule-config`: 双层规则配置——类别别名、disabled/ignore 语义、原生配置文件优先级。

### Modified Capabilities
- `reporting`: report.md 渲染改为 CS-ID 且无引擎名；report.json 增加 csId。
- `skill-workflow`: 修复选项增加"先查看问题详情"及详情浏览→修复选项的循环。

## Impact

- scripts/codespot（show 子命令、渲染）、scripts/engines/common.py（CS-ID、config rules 读取）、各适配器（读取 config 的 disabled/ignore、原生配置检测：ruff/oxlint/sqlfluff/bandit）、registry.json（category 字段）。
- 对 agent 的工作方式无破坏：report.json 原有字段不变，仅新增 csId。
- selftest 夹具照常基于真实规则校验（内部字段），另补 CS-ID 与 brand 隔离断言。
