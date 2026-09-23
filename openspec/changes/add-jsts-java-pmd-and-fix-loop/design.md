# Design

## Context

M0 已归档（基座 + gitleaks + ruff）。本批按调研报告 3.5/3.6/3.9 与第 6 章 M1 里程碑实施：JS/TS 双层、Java PMD、修复循环。契约不变（engine-contract），只加适配器与编排。

## Decisions

### D1. oxlint 安装：GitHub Releases 平台二进制
oxc 在 `apps_v1.85.0` 这类 release tag 下提供 `oxlint-<platform>.tar.gz` 平台包，无需 npm。registry 用与 gitleaks 相同的 download 形态。**备选否决**：npm 包 oxlint（要求用户有 node 才能跑"快速层"，违背分层初衷）。

### D2. ESLint 深度层：一次性 npm 项目
setup 在 `~/.codespot/engines/eslint-layer-1/` 里写 package.json（锁 eslint ^9、eslint-plugin-sonarjs 4.2.1、eslint-plugin-oxlint 1.85.0、typescript-eslint、@typescript-eslint/parser）并 `npm install --no-audit --no-fund`。检测 `npm --version` 失败 → 记 degraded。运行时用 `node <layer>/node_modules/eslint/bin/eslint.js --no-config-lookup -c <codespot 配置> --format json <files>`。

### D3. 去重：配置层而非合并层
用 `eslint-plugin-oxlint` 的 flat/recommended 关闭 ESLint 侧重叠规则（官方推荐做法，M0 报告 3.6），合并层不做 (file,line) 去重——两层规则本就不重叠。sonarjs 的 flat config 与 plugin-oxlint 顺序：sonarjs 在前、oxlint 关闭清单在后（数组末尾）。

### D4. ESLint 规则面 v1
只开 sonarjs `recommended`（非类型感知部分）+ eslint core recommend 的质量子集；不开 typed linting（需 tsconfig，Phase 3）。JS 与 TS 文件同跑（sonarjs 支持 JS 语法分析 TS 无类型模式有限——TS 文件若解析失败则记录 degraded 原因，不阻塞）。

### D5. PMD 安装与调用
`pmd-dist-7.27.0-*-zip.zip` 从 GitHub Releases 下载解压；`<pmd>/bin/pmd check --no-progress --no-cache -d <files逗号列表> -R <codespot ruleset> -f sarif -r out.sarif`。ruleset 用官方 quickstart 精简（assets/pmd-ruleset.xml 引用内置规则集优先级≥3 的规则，控制噪音）。退出码 4=有违规（成功）、0=无违规，其余为失败。JRE 探测：`java -version` 失败 → 空结果 + stderr 提示（spec 定义）。

### D6. severity 映射扩展
rules-severity.json 增 `pmd`（priority 属性映射在适配器内做：1/2→critical? 按 spec 1→critical、2→major、3→minor、4/5→info——注意 PMD priority 1 其实少见，可接受）、`oxlint`（correctness 类默认 major，style→minor 按 category 字段）、`eslint-sonarjs`（sonarjs type 字段：bug→major、code-smell→minor；S 族安全规则→critical 由映射表显式列出）。

### D7. 修复循环：纯 SKILL.md 编排，无新代码
重扫验证直接复用 `codespot scan`（scope 足够覆盖改动文件）；`.codespot/ignore` 过滤已在 M0 的 merge_issues 实现。唯一代码改动：SKILL.md 文本升级 + scope unpushed 中 `_unpushed` 重复调用的清理。**不做** `--files` 自定义扫描参数（3 轮重扫用原 scope 即可，避免范围漂移）。

## Risks / Trade-offs

- [ESLint 深度层安装 ~40MB node_modules] → 仅在用户确有 JS/TS 文件且 npm 可用时安装；降级路径完整。
- [oxlint 平台包命名随版本变化] → registry 的 URL 模板集中管理，upgrade 时只改 registry。
- [PMD 首启 JVM 慢（数秒）] → Java 文件本就少，可接受；不做常驻。
- [sonarjs 对零散 TS 文件解析失败] → ESLint `--no-error-on-unmatched-pattern`；解析错误计入 degraded 信息。

## Open Questions

（无——oxlint 平台资源命名在实现时用 GitHub API 现场确认。）
