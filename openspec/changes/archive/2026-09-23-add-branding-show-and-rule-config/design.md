# Design

## Context

三个体验需求一次落地。前提决策（用户已确认）：呈现层改名（agent 内部接口保留原始字段）、双层规则配置、修复循环增加详情浏览。

## Decisions

### D1. CS-ID：确定性哈希，无状态
`csId = "CS-" + sha1(tool + "|" + rule)[:5]`；同扫描内碰撞则后缀 `-2`、`-3`。不落盘映射表（无状态、跨仓库稳定）；agent 反查只需 report.json 原始字段，无需解码。生成放在 common.make_issue（单点），report.md/show 渲染时直接读 csId。

### D2. 品牌隔离的边界（写死在 spec）
人读表面（report.md、show 输出、SKILL.md 呈现文案）：无引擎名。agent 内部（report.json、selftest、SKILL.md 的内部决策指引）：保留真实 tool/rule/ruleUrl。registry.json 属于工具内部文件，不算用户表面。

### D3. 类别别名（registry.category）
gitleaks→secrets、ruff→python_lint、bandit→python_security、oxlint→js_lint、pmd→java、sqlfluff→sql、semgrep→semantic；内部组件（eslint-layer/spotbugs）无别名。config.json `"rules"` 以别名为键；engine_errors 在 md 中用别名。

### D4. 双层配置的合并语义
- 读取：`.codespot/config.json` → `{"rules": {"<cat>": {"disabled": bool, "ignore": [rule...]}}}`。
- 调度：`select_engines` 跳过 disabled 类别（category 查 registry）。
- ignore 过滤：merge_issues 时按 issue 的 (tool→category) 找 ignore 列表过滤（单点，不用改适配器）。
- 原生配置优先（检测→行为）：
  - ruff：workdir 存在 `.ruff.toml`/`ruff.toml`，或 pyproject.toml 含 `[tool.ruff` → 适配器省略 `--config`（ruff 自行发现）；否则用 assets 默认。
  - oxlint：workdir 存在 `.oxlintrc.json` → 省略 `-c`。
  - sqlfluff：workdir 存在 `.sqlfluff` → 加 `--config <workdir>/.sqlfluff`（客户端 LT/CP 过滤照旧，ignore 列表照旧叠加）。
  - gitleaks：gitleaks 原生自动读 `.gitleaks.toml`，无需改代码，文档说明。
  - eslint/bandit/semgrep/pmd：本批支持 disabled/ignore（bandit ignore→`-s`、eslint ignore→适配器客户端过滤、semgrep/pmd 走 ignore 通用过滤），原生配置文件不做（eslint 依赖环境复杂、pmd ruleset 支持路径覆盖放 config.json `"rules": {"java": {"ruleset": "<path>"}}`？——不做，记录为限制）。
- "参数调整"：通过原生配置文件实现（ruff line-length 等），文档写明；config.json 不做参数透传（避免造方言）。

### D5. show 子命令
`codespot show [--severity csv] [--file prefix] [--rule CS-id] [--limit N=50] [--all]`：读 report.json → 过滤 → 按 (severity, file, line) 排序输出：`[CS-xxxxx] 🟠 file:line 说明` + 缩进片段行。无 report 时提示先 scan。

### D6. md 渲染改造点
issues 行：`[CS-xxxxx](ruleUrl)` 改为 `[CS-xxxxx]`；删除规则链接；engine_errors 区改"检查模块提示（类别名）"；其余（脱敏、分组、空结论）不变。csId 由 make_issue 统一写入后，渲染/过滤都是纯读。

## Risks / Trade-offs

- [CS-ID 对用户不可望文生义] → show 详情带完整说明；SKILL.md 指引 agent 呈现时用自然语言描述问题而非念编号。
- [哈希碰撞概率] 5 hex=1,048,576 空间，单仓规则种类 <200，生日碰撞 ~1.9%；碰撞仅同扫描内加后缀，可接受。
- [config.json 出现引擎名时] 静默忽略？不——文档说明用类别键；出现未知键给出一次性警告（stderr）。
- [原生 ruff 配置改变了发现集，selftest 夹具所在 repo 无原生配置] 不受影响。

## Open Questions

（无）
