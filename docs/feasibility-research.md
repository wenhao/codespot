# codespot 可行性调研报告

> 调研日期：2026-09-23（两轮调研：第一轮覆盖 Sonar 系路线与备选引擎，第二轮补充 oxlint、gitleaks、SQLFluff、SpotBugs+FindSecBugs 编排、Opengrep 现状）
> 调研方式：网络调研。所有版本号、许可证、能力结论均通过官方文档、npm / PyPI / Maven / GitHub Releases API 当日实时核验，非缓存或二手转载。
> 结论速览：**方案整体可行**。原定"直接封装 sonar-java / sonar-python / SonarJS"存在**许可证合规灰区**与**无官方 standalone 模式**两道障碍，推荐改为"**多引擎适配器 + 统一报告 + AI 修复闭环**"架构：v1 使用干净许可的引擎组合（JS/TS 用 oxlint+ESLint(sonarjs) 双层、Python 用 ruff+bandit、Java 用 PMD、密钥检测 gitleaks 常开、SQL 用 SQLFluff），Sonar 原生引擎作为 Phase 3 实验性选项。引擎轨道互相独立，**基座完成后可并行实施**（见第 6 章）。

---

## 目录

1. [项目背景与目标](#1-项目背景与目标)
2. [核心结论](#2-核心结论)
3. [关键调研发现](#3-关键调研发现)
4. [三条技术路线对比](#4-三条技术路线对比)
5. [推荐方案与实现设计](#5-推荐方案与实现设计)
6. [并行实施路径与迭代计划](#6-并行实施路径与迭代计划)
7. [风险与限制](#7-风险与限制)
8. [附录：版本快照](#8-附录版本快照2026-09-23-核验)
9. [参考链接汇总](#9-参考链接汇总)

---

## 1. 项目背景与目标

**codespot** 是一个面向 AI agent 的静态代码扫描 skill。目标用户旅程：

1. 用户在本地用 AI 生成代码；
2. 调用 codespot 做静态扫描（支持增量：未提交 / 已提交未推送 / 全量 / 自定义范围）；
3. skill 自动下载所需的开源扫描引擎（幂等，按语言懒加载）；
4. 扫描产出**机器可读报告**（JSON，供 AI agent 读取）+ 人类可读摘要（Markdown）；
5. agent 呈现修复选项：仅严重（critical）/ 重要及以上（major+）/ 全部 / 自定义，随后执行修复并重扫验证。

设计原则：**纯本地运行、不部署服务器、报告机器可读、修复闭环**。

覆盖范围（第二轮调研后确定）：**代码质量 + 安全漏洞 + 硬编码密钥 + SQL 规范**，四个维度。

---

## 2. 核心结论

| # | 结论 | 影响 |
|---|------|------|
| 1 | sonar-java / sonar-python / SonarJS 自 2024-11 起从 LGPL-3.0 改为 **SSALv1（Sonar Source-Available License v1.0，非 OSI 开源）**，其中包含"禁止用非捆绑 AI 摄取/分析本程序输出数据"的条款 | ⚠️ 与"AI agent 读扫描结果并修复"的核心场景存在许可灰区：个人自用风险低，作为开源工具分发则需法务确认 |
| 2 | 官方新 CLI（SonarQube CLI `sonar`，2026-06 GA）**必须连接 SonarQube Cloud/Server** 才能做质量分析；仅 secrets 检测可本地；且 macOS 只支持 ARM64 | ❌ 不符合"纯本地"要求，排除（本机为 darwin x64 也直接不可用） |
| 3 | `sonar-scanner-cli` 官方确认**无法脱离服务器运行** | ❌ 排除 |
| 4 | `sonarlint-language-server`（LGPL-3.0，Maven Central 公开）**内嵌全套 Sonar 分析器 JAR，可完全离线运行**；社区已有 CLI 驱动先例 | ✅ 技术可行（路线 A），但协议无官方承诺 + SSALv1 灰区 + 约 170MB 下载 → 定位为 Phase 3 实验选项 |
| 5 | **JS/TS 推荐"oxlint + ESLint(sonarjs)"双层引擎**：oxlint 1.85（870 条规则、SARIF 原生、官方宣称比 ESLint 快 50–100 倍、还有面向 AI 的 `agent` formatter）做快速层；ESLint + eslint-plugin-sonarjs（Sonar 官方维护、200+ 条 Sonar 规则）做深度层；用官方 `eslint-plugin-oxlint` 关闭重叠规则避免重复报告 | ✅ 速度与 Sonar 风味兼得，且是 oxlint 官方推荐的混合模式 |
| 6 | Python：**ruff**（900+ 规则、JSON 带 fix 建议、秒级）+ **bandit**（安全、JSON 带 severity+confidence） | ✅ 干净许可、当天可用 |
| 7 | Java：**PMD 7**（源码级、无需编译、JRE 8 即可、内置 SARIF/JSON）为 v1 主引擎；**SpotBugs 4.10 + FindSecBugs 1.14**（144 个安全检测器、CWE 内建）作为"项目可编译时"的深度增强（编排：探测 pom.xml/build.gradle → compile → CLI 扫 classes 目录，SARIF 输出） | ✅ 双层覆盖；注意 SpotBugs CLI 无原生 JSON，以 SARIF 为准 |
| 8 | **密钥检测：gitleaks 8.30**（MIT、Go 单二进制、222 条内置规则、json/sarif 输出、`dir` 模式直扫工作区不碰 git 历史）跨语言**常开** | ✅ 对"AI 生成代码常带硬编码密钥"的场景价值极高、成本极低 |
| 9 | SQL：**SQLFluff 4.3**（MIT、约 30 种方言、约 80 条规则、4.0.1 起原生 SARIF）覆盖 SQL 规范；注意必须显式指定 dialect、无自动检测 | ✅ 可选语言轨道 |
| 10 | Semgrep/Opengrep：Opengrep 引擎（1.30.0）生产可用且更快，但**没有官方规则库**（opengrep-rules 已归档；semgrep 官方 registry 规则许可仅限内部使用） | ⚠️ 引擎可用、规则必须自备 → 降级为 Phase 3 可选项 |
| 11 | LGPL 组件采用"**运行时由用户从官方源下载、不随工具分发**"模式，对 codespot **零额外义务**（GNU FAQ 确认） | ✅ 分发合规 |
| 12 | 兜底路线：本地 Docker SonarQube Community Build + REST API（分钟级启动 + 约 4GB 内存） | ⚠️ 备选，体验重，不做 |
| 13 | 先例充分：官方 sonarqube-mcp-server、semgrep/mcp 均验证了"分析器 → 结构化 findings → agent 修复"闭环 | ✅ 方向成立；codespot 差异化 = 本地 CLI + 多引擎统一报告 + 修复选项闭环 |

**推荐路线：v1 用路线 B（干净引擎组合）落地完整闭环，架构预留引擎适配器接口；路线 A（sonarlint-ls）作为 Phase 3 实验性 `--engine sonar` 选项（默认关闭并明示许可灰区）；路线 C 不做。**

**命名：保留 codespot**——短、直觉（spot = 揪出问题，与 SpotBugs 呼应），仓库已建，不换。备选：patrol、codeprobe，均不如现名。

---

## 3. 关键调研发现

### 3.1 Sonar 分析器许可证变更（SSALv1）——影响最大的发现

- 2024-11-19 官方公告：分析器许可证从 LGPL-3.0 改为 **Sonar Source-Available License v1.0（SSALv1）**，2024-11-29 之后发布的版本全部适用（sonar-java 仓库 LICENSE.txt 变更于 2024-11-21，SonarJS 于 2024-11-26）。
- SSALv1 限制：① 仅授权"非竞争用途"；② **禁止"用非捆绑的 AI 摄取/分析本程序提供的数据"**——codespot 的核心场景（AI agent 读 Sonar 分析结果并修复）恰好落在该条款的解释范围内，开源分发前需法务确认；个人本地自用风险较低。
- 附带疑点：`eslint-plugin-sonarjs@4.2.1` 的 tarball 内 `LICENSE` 文件为 SSALv1，而 `package.json` 的 license 字段仍写 LGPL-3.0-only，两者矛盾，应按更保守的 SSALv1 对待（运行时下载模式下对自用无实质影响）。

来源：
- <https://community.sonarsource.com/t/a-new-sonar-license-for-sonarqube-analyzers/120106>
- <https://github.com/SonarSource/sonar-java/blob/master/LICENSE.txt>

### 3.2 官方 CLI 路线盘点（全部不符合"纯本地"）

| 产品 | 状态 | 关键事实 |
|------|------|----------|
| `sonarlint-cli`（旧） | 2017 年归档 | <https://github.com/SonarSource/sonarlint-cli> |
| **SonarQube CLI**（`sonar`，新） | Open Beta 2026-04-13 → GA 1.0 2026-06-17 → 当前 1.8.0.5274（2026-09-15） | 安装：brew cask / mise / curl 脚本，**无 npm 包**；平台：Linux x64/arm64、**macOS 仅 ARM64**、Windows x64。质量分析走服务端 "Agentic Analysis"（本地变更分析仅限 SonarQube Cloud）；仅 secrets 检测本地运行（仍尝试联网认证）。输出 json/table/csv/toon，**无 SARIF**；退出码 51 = 发现问题。CLI 代码本身 LGPL-3.0，但有效功能依赖 Cloud 订阅或 Server 2025.1+ |
| `sonar-scanner-cli` | 现役 | 官方确认无服务器直接失败（"you can't use the scanner without an instance of the server"）；第三方 `sonarless` 的绕法也是起临时 Docker SonarQube |

来源：
- <https://github.com/SonarSource/sonarqube-cli> · <https://docs.sonarsource.com/sonarqube-cli/> · <https://docs.sonarsource.com/sonarqube-cli/using-sonarqube-cli/exit-codes/>
- Beta 帖 <https://community.sonarsource.com/t/sonarqube-cli-is-now-in-open-beta-and-its-available-to-everyone/181112> · GA 帖 <https://community.sonarsource.com/t/sonarqube-cli-is-generally-available/183664>
- <https://github.com/gitricko/sonarless>

### 3.3 sonarlint-language-server：事实上的离线 Sonar 路线（路线 A，Phase 3 实验选项）

- **分发**：npm 上**不存在** `sonarlint-language-server` 包（registry 404，已实测）。公开渠道：Maven Central `org.sonarsource.sonarlint.ls:sonarlint-language-server`，最新 5.9.0.79716（2026-09-14），LGPL-3.0；以及 SonarLint VS Code 扩展 VSIX（5.10.0+80769）——**下载解包即得 LS 与全部分析器**：`extension/server/sonarlint-ls.jar`（53MB）+ `extension/analyzers/` 下 14 个分析器 JAR（sonarjava 20MB、sonarpython 19MB、sonarjs 18MB、javasymbolicexecution、go、php、html、xml、iac、text/secrets 等），VSIX 整体约 170MB。
- **启动**：`java -jar sonarlint-ls.jar -stdio -analyzers path/to/xxx.jar ...`，Java 11+。
- **离线能力**：SonarQube for IDE 官方明确支持 standalone 模式（本地反馈、不连 Server/Cloud），standalone 下本地支持 20+ 语言（含 Java、JS/TS、Python）。
- **批量扫描可行性**：LSP 以 `didOpen → publishDiagnostics` 逐文件触发，无官方"整仓批扫" API；`sonarlint/` 命名空间的自定义扩展协议**未对外文档化承诺**，跨版本可能变化。Java 全量类型感知规则需项目 classpath/JDK 配合，否则降级。
- **社区实证**（CLI/编辑器驱动 LS 的先例）：
  - [vincentfenet/sonarlint-ls-cli](https://github.com/vincentfenet/sonarlint-ls-cli) —— Python CLI，加载 VSIX 提取的 `sonarpython.jar`，支持 `analyze --files *.py`、`list-rules`、规则过滤，可完全离线。**这就是路线 A 的原型验证**。
  - [sonarlint.nvim](https://gitlab.com/schrieveslaach/sonarlint.nvim) · [burrima/sonarlint-ls-wrapper](https://github.com/burrima/sonarlint-ls-wrapper) · [tskorupka/sonarqube-zed-extension](https://github.com/tskorupka/sonarqube-zed-extension)
- **嵌入式备选**：`sonarlint-backend-cli`（sonarlint-core 引擎 Maven 构件，11.10.0.86299）。
- **结论**：技术上可行且已被社区验证；代价 = 协议无承诺（升级可能 break）、约 170MB 首次下载、需 JDK 11+、SSALv1 灰区（LS 是 LGPL，但其中运行的分析器 JAR 源码许可是 SSALv1）。

### 3.4 SonarJS 与 eslint-plugin-sonarjs（深度层引擎）

- `eslint-plugin-sonarjs@4.2.1`（2026-09-15 发布，SonarSource 员工维护，源码在 SonarJS monorepo），peer 依赖 `eslint ^8 || ^9 || ^10`，支持 flat config（`sonarjs.configs.recommended`）。
- **规则覆盖**：README 规则表约 **215 条**（另一统计口径 295，含已废弃与装饰规则），其中约 **48–71 条需 TypeScript 类型信息**（💭，需 `@typescript-eslint/parser` + typed linting）。约占 SonarJS 全量（533 JS + 552 TS + 43 CSS）的一半。
- **官方明确缺失三类**：① SonarQube 直接复用外部 ESLint/@stylistic/typescript-eslint 的规则（S103/S106/S108/S113/S121 等）；② SonarJS "decorated 改进版"（S107、S109、S131、S905、S1068 等）；③ 43 条 CSS 规则。
- **输出**：ESLint 原生 `--format json`；SARIF 用 [`@microsoft/eslint-formatter-sarif@3.1.0`](https://www.npmjs.com/package/@microsoft/eslint-formatter-sarif)（MIT，2024-04 后未再发布；ESLint 9 下存在过时的 `@types/eslint` 依赖冲突，可能需 `--legacy-peer-deps`）。
- **类型感知规则适配成本**：需 `parserOptions.project` / `projectService`，且被扫文件必须包含在某个 tsconfig 内——对"AI 生成的零散 TS 文件"需要合成 tsconfig（Phase 3 处理），v1 先开非类型感知规则。
- 规则表：<https://github.com/SonarSource/SonarJS/blob/master/packages/analysis/src/jsts/rules/README.md>

### 3.5 干净许可的引擎矩阵总表（路线 B，2026-09-23 核验）

| 领域 | 引擎 | 版本 | 许可 | 输出 | 运行时 | 定位 |
|------|------|------|------|------|--------|------|
| JS/TS 快速层 | **oxlint** | 1.85.0 | MIT | `--format json / sarif / checkstyle / github / agent / junit…`（10 种） | npm 单包（Rust） | 870 条内置规则（eslint core/typescript/react/unicorn/jest/import/promise/jsx-a11y/nextjs/node/vue/oxc 等 15 家族，默认开 correctness 类 111 条，325 条可 autofix）；官方宣称比 ESLint 快 50–100 倍；**v1.63.0（2026-05）起 SARIF 正式支持**；`agent` formatter 专为 AI agent 场景设计 |
| JS/TS 深度层 | **ESLint + eslint-plugin-sonarjs** | eslint 9.x / sonarjs 4.2.1 | MIT / ⚠️ SSALv1-LGPL 矛盾 | 原生 json；SARIF 经 @microsoft formatter | Node | Sonar 规则风味（200+ 条）；与 oxlint 经 `eslint-plugin-oxlint` 去重（见 3.6） |
| Python 质量 | **ruff** | 0.16.8 | MIT | `--output-format json / sarif` 等 12 种 | 单二进制 | 900+ 规则（pycodestyle/pyflakes/flake8 全家桶/pylint/isort/pyupgrade 等）；**JSON 输出带 `fix` 字段，SARIF 不带**——AI 修复场景用 JSON |
| Python 安全 | **bandit** | 1.9.4 | Apache-2.0 | `-f json / sarif` | Python | B1xx–B7xx 纯安全检测，带 severity(H/M/L) + confidence |
| Java 源码级 | **PMD 7** | 7.27.0 | Apache-2.0 | 内置 **sarif / json** 等 15 种渲染器 | **JRE 8+** | 源码 AST 分析、无需编译——唯一适合扫"可能编译不过的零散代码"的 Java 引擎；退出码 4=发现违规；`--file-list` 支持文件清单 |
| Java 字节码级 | **SpotBugs 4.10.4 + FindSecBugs 1.14.0** | — | LGPL-2.1 | `-sarif=` / `-xml=`（**CLI 无原生 JSON**） | JDK 11+ 运行；可分析 Java 21 字节码（≥4.8.0） | 类型/数据流分析更准 + 144 个安全检测器（CWE 内建）；**需先编译成功**，作"可编译项目"深度增强（编排见 3.9） |
| Java 风格（可选） | Checkstyle | 14.1.0 | LGPL-2.1 | `-f xml / sarif / plain` | JDK 21+，配置 XML 强制 | 风格规范为主，优先级最低 |
| **密钥检测（跨语言常开）** | **gitleaks** | 8.30.1 | MIT | `--report-format json / sarif / csv / junit / template` | Go 单二进制 | 222 条内置规则（各厂商 API key/token + private-key + 熵值启发式）；`git / dir / stdin` 三种模式（详见 3.7） |
| SQL | **SQLFluff** | 4.3.0 | MIT | `--format human / json / yaml / sarif(4.0.1+) / github…` | Python ≥ 3.10 | 约 30 种方言、约 80 条规则；规范/结构检测，无安全规则（详见 3.8） |
| 跨语言语义（Phase 3 可选） | **Opengrep** | 1.30.0 | LGPL-2.1（引擎） | `--json` / `--sarif-output`（semgrep 兼容） | OCaml 二进制 | 引擎生产可用、比 semgrep CE 快 25–74%（厂商口径）；**规则必须自备**（详见 3.10） |
| Python 补充（可选） | pylint | 4.0.8 | GPL-2.0 | `json / json2`（无 SARIF） | Python | 分类最接近 Sonar "Code Smell"，优先级低 |

与 SonarPython 规则风格的可比性（定性）：ruff 的 E/W（pycodestyle）、F（pyflakes）、PL（pylint）、S（flake8-bandit）家族合计覆盖 SonarPython 常见规则的**大部分同类问题**，但规则 ID 体系完全不同，需在 codespot 层建"规则名 → Sonar RSPEC"的启发式映射表。

### 3.6 JS/TS 双层引擎策略：oxlint + ESLint（官方推荐混合模式）

**为什么双层**：oxlint 快（50–100 倍，万文件约 100ms）但**没有 sonarjs 规则家族**；ESLint+sonarjs 有 Sonar 规则风味但慢。oxlint 官方文档给出两条采用路径：直接替换，或**渐进混合——"Run Oxlint first, then run ESLint with overlapping rules disabled"**。codespot 采用混合模式。

**不重复报告的配置**（三步，全部官方支持）：

```bash
npm i -D oxlint eslint eslint-plugin-sonarjs eslint-plugin-oxlint
```

```js
// eslint.config.js —— oxlint 的关闭清单插件必须放在配置数组最后
import oxlint from 'eslint-plugin-oxlint';
export default [
  sonarjs.configs.recommended,
  ...oxlint.configs['flat/recommended'],   // 关闭 ESLint 中已被 oxlint 覆盖的规则
];
```

```json
// package.json
"scripts": { "lint": "oxlint && eslint ." }
```

进阶：`buildFromOxlintConfigFile('./.oxlintrc.json')` 可按实际 oxlint 配置精确生成关闭清单。**注意包名是 `eslint-plugin-oxlint`（`eslint-config-oxlint` 在 npm 不存在，404 已核验）**，它与 oxlint 版本严格同步（同为 1.85.0）。

**类型感知（Phase 3）**：oxlint 自身 type-aware 已于 2026-07 转为 **stable**（`oxlint --type-aware`，需 `oxlint-tsgolint`，基于 TypeScript 7 原生编译器 typescript-go，覆盖 59/61 条 typescript-eslint 类型感知规则，官方基准比 ESLint+typescript-eslint 快 12–18 倍）。注意 tsgolint 属 oxc-project（源自 typescript-eslint 组织的 PoC），不是 Microsoft 项目；Microsoft 提供的是底层 typescript-go。ESLint 侧的类型感知规则仍走合成 tsconfig 方案（3.4）。

**观望项（Phase 3+）**：oxlint 的 **jsPlugins（alpha，2025-10 发布）** 兼容 ESLint v9+ 插件 API，官方一致性测试名单**已包含 sonarjs**——若转正，可用 oxlint 单引擎直接加载 `eslint-plugin-sonarjs`，但目前 alpha 且不支持依赖类型信息的规则，生产采用有风险。

**oxlint 配置**：`.oxlintrc.json` 完整支持（categories: correctness 默认/suspicious/pedantic/perf/style/restriction/nursery；`--init` 生成、`--print-config` 校验）。

来源：
- 规则页（870 条计数）：<https://oxc.rs/docs/guide/usage/linter/rules> · linter 主页（50–100x）：<https://oxc.rs/docs/guide/usage/linter>
- 配置：<https://oxc.rs/docs/guide/usage/linter/config> · CLI（格式列表）：<https://oxc.rs/docs/guide/usage/linter/cli>
- 混合用法与去重插件：<https://github.com/oxc-project/eslint-plugin-oxlint>
- type-aware：<https://oxc.rs/docs/guide/usage/linter/type-aware> · tsgolint：<https://github.com/oxc-project/tsgolint>
- jsPlugins（alpha）：<https://oxc.rs/docs/guide/usage/linter/js-plugins>
- SARIF 落地版本：<https://github.com/oxc-project/oxc/releases/tag/apps_v1.63.0>（PR #22067）
- 1.0 公告：<https://voidzero.dev/posts/announcing-oxlint-1-stable>

### 3.7 密钥检测：gitleaks（跨语言常开层）

**版本/许可**：v8.30.1（2026-03-21），MIT，29.4k★；brew / 预编译二进制 / Docker 安装；发布节奏放缓但维护中（最后 push 2026-09-09）。

**命令体系（重要，v8.19.0 起 `detect`/`protect` 已废弃）**：

| 场景 | 命令 | 语义 |
|------|------|------|
| 扫 git 全历史 | `gitleaks git <repo>` | 等价 `git log -p` 全量 |
| **扫工作区文件（AI 刚生成的未提交代码）** | **`gitleaks dir <目录或文件>`** | 当普通文件扫，不碰 git 历史，秒级 |
| 扫暂存区（pre-commit） | `gitleaks git --pre-commit --staged` | diff 模式，毫秒级 |
| 扫标准输入 | `gitleaks stdin` | 管道流 |

- **不能一次传文件清单**：`dir` 只接受单个路径。多文件变通：聚合到临时目录再 `dir`，或对未提交代码直接 `dir <repo根>`（它只读文件内容，不读历史，无性能问题）。
- **输出**：`--report-format json / sarif / csv / junit / template` + `--report-path`。**退出码：0=无泄漏；1=发现泄漏或出错；126=未知 flag**（1 的双重含义需结合 stderr 区分；可用 `--exit-code N` 覆盖）。
- **规则**：内置 **222 条**（对官方默认 gitleaks.toml 实测统计），覆盖两百余种厂商 key/token、私钥块、熵值+关键词启发式；自定义规则走 TOML（`--config` > 环境变量 > `.gitleaks.toml` > 内置）。
- **误报通道**：每条 finding 带 Fingerprint，加入仓库根 `.gitleaksignore` 即精确忽略（experimental）；`--baseline-path <旧报告>` 只报新增——与 codespot 的增量理念天然契合。
- **性能**：`dir` 模式秒级；`git` 全历史大仓库分钟级（社区经验，无官方基准）。

**替代品对比与结论**：
- **trufflehog**（28k★，**AGPL-3.0**）：800+ 检测器且能联网验证密钥是否有效——验证会外呼、不适合本地离线扫 AI 代码；AGPL 对集成有传染风险。仅"确认活密钥"深度场景作可选补充。
- **detect-secrets**（Yelp，Apache-2.0）：活跃度下滑、检测器少于 gitleaks，不建议新集成。
- **推荐 gitleaks**：MIT、单二进制零依赖、不联网、json/sarif 齐全——嵌入 codespot 常开层。

来源：<https://github.com/gitleaks/gitleaks> · 命令源码 <https://github.com/gitleaks/gitleaks/blob/master/cmd/detect.go>（新旧命令映射注释）· <https://github.com/gitleaks/gitleaks/blob/v8.30.1/config/gitleaks.toml>（222 条实测）

### 3.8 SQL：SQLFluff

- **版本/许可/安装**：4.3.0（2026-08-07），MIT，Python ≥ 3.10（4.2.0 起放弃 3.9），`pipx install sqlfluff`；另有 Rust 解析器扩展 `sqlfluffrs` 与 Rust 原生规则（4.3.0 起 CP01/CP03/CP04 已 Rust 化）。
- **方言**：约 30 个（ansi/postgres/mysql/tsql/bigquery/snowflake/duckdb/sparksql/clickhouse/oracle/db2/…，含派生树）。**无自动检测**：不指定 dialect 直接报错（退出码 2），ansi 只是手动退路。可用 `--dialect`、配置文件或文件内注释 `-- sqlfluff:dialect:mysql` 指定。
- **规则**：约 80 条，新旧双编号（组名 + L0xx 别名）。分组：Aliasing(AL)、**Ambiguous(AM，真 bug 味：DISTINCT+GROUP BY、裸 UNION、隐式交叉连接、LIMIT 无 ORDER BY)**、Capitalisation(CP)、Convention(CV)、Layout(LT，纯排版)、Postgres/TSQL/Oracle 方言组、References(RF)、**Structure(ST，未用 CTE/JOIN、嵌套 CASE)**。**无安全类规则**（确认）。官方提供 `core` 规则子集（稳定、跨方言、非主观）作为团队起点。
- **输出**：`--format human / json / yaml / sarif / github-annotation(-native) / gitlab / none`——**SARIF v2.1.0 原生支持自 4.0.1（2026-02，PR #7413），不再是 feature request**。退出码：**0=通过；1=存在违规/解析失败类违规；2=配置错误（如未知 dialect）**——三态可直接被编排器消费。已知坑：`--bench` 与 json/sarif 同用输出到 stdout 会产生非法 JSON（issue #8490），落盘用 `--write-output` 或不用 --bench。
- **修复**：`sqlfluff fix` 默认只修可解析文件；`--FIX-EVEN-UNPARSABLE` 为强制开关（风险自担）。修复主要覆盖 Layout/Convention 类，会改写文本结构——**AI 修复链路建议 fix 后 diff 复核**。
- **性能**：大 SQL 文件偏慢是长期反馈（issue #1208）；官方持续优化（4.1.0 并行/流式管线、4.2.0 max_parse_nodes 防资源耗尽、4.3.0 Rust 原生规则）。并行选项是 `-p/--processes`（不是 --threads）。对"AI 生成的零散 SQL 片段"（无 dbt/jinja 模板）开箱即用，纯 SQL 原样通过默认 jinja templater。
- **给 AI 修复的规则取舍（工程建议）**：默认开 AM/ST/RF + CV 语义类 + 方言组（真问题）；**默认关 LT/CP 全组**（纯排版噪音，可分流到单独的"格式化"通道跑 `sqlfluff fix`）；或直接用官方 `core` 子集起步。
- **codespot 适配要点**：dialect 无法自动检测——编排器按"项目配置 > 文件内注释 > 按文件名/内容启发式（如 `CREATE TABLE ... AUTO_INCREMENT` → mysql）> 询问用户"的顺序确定；**解析失败（PRS 类违规）不得当作可修复清单**，要在报告中单列为"无法解析"。

来源：<https://docs.sqlfluff.com/en/stable/reference/cli.html> · 规则参考 <https://docs.sqlfluff.com/en/stable/reference/rules.html> · 方言 <https://docs.sqlfluff.com/en/stable/reference/dialects.html> · PyPI <https://pypi.org/project/sqlfluff/> · SARIF PR <https://github.com/sqlfluff/sqlfluff/pull/7413> · 性能 issue <https://github.com/sqlfluff/sqlfluff/issues/1208>

### 3.9 SpotBugs + FindSecBugs 的工程化编排（Java 深度层）

**触发方式（三种）**：
1. **CLI 直跑产物（codespot 采用，侵入性最低）**：推荐 FindSecBugs 官方 `findsecbugs-cli.zip`（含 `findsecbugs.sh` 与依赖目录）：`findsecbugs.sh -effort:max -sarif=out.sarif <jar或classes目录>`。裸 `spotbugs -textui -pluginList findsecbugs-plugin.jar ...` 也可，但单 jar 不含依赖易 NoClassDefFound，且 pluginList 多 jar 分隔符随 OS（Unix `:` / Windows `;`）。
2. Maven 项目：`spotbugs-maven-plugin` 4.10.4.1（前三段对齐 SpotBugs 4.10.4），`mvn compile spotbugs:spotbugs`，SARIF 开 `<sarifOutput>true</sarifOutput>`；`spotbugs:check` 默认绑 verify。需 Maven 3.8.9 + JDK 11。
3. Gradle 项目：`spotbugs-gradle-plugin` 6.5.6（配 SpotBugs 4.10.2），`spotbugsMain` 挂在 check 下，reports DSL 支持 sarif。

**codespot 编排器策略**：探测 `pom.xml` → `mvn -q compile` → CLI 扫 `target/classes`；探测 `build.gradle(.kts)` → `gradle compileJava`（只编译，不跑 build/test）→ CLI 扫 `build/classes/java/main`；**都没有构建文件 → 跳过 SpotBugs 层并提示**（AI 半成品常无完整构建）。

**已知坑**：① 首次 `mvn compile` 可能大量下载依赖（设超时 + `-o` 离线降级提示）；② 插件版本与 SpotBugs 内核必须对齐（4.10.4.1 ↔ 4.10.4）；③ XML 与 SARIF 参数体系不同（Maven 属性式 vs CLI 选项式）；④ **CLI 无原生 JSON**，统一管线以 SARIF 为准。

**confidence vs priority**：同一维度的两个名字——FindBugs 时代叫 priority，SpotBugs 改叫 **confidence**（High/Medium/Low，XML 里 `priority` 属性 1/2/3）；另有独立 **rank（1–20，"scariest→of concern"）**。codespot 的 severity 映射采用 SpotBugs 官方档次：rank 1–4（Scariest）→ critical、5–9（Scary）→ major、10–14（Troubling）→ minor、15–20（Of concern）→ info，安全类（FindSecBugs，category=SECURITY）整体提一档。

**FindSecBugs**：144 个 BugPattern（官方描述符实测；官网口径 "144 bug patterns, 826 unique API signatures"），覆盖 OWASP Top 10；**每个 BugPattern 内建 `cweid` 属性**（SARIF 可透出 CWE 编号）；命名体系是语义 type（SQL_INJECTION_JDBC、XXE_DOCUMENT…）+ 缩写（SECSQLIJDBC…），无 SECRITICAL/SECMAJOR 官方命名（那是第三方聚合层的展示名）。

**JDK 兼容**：SpotBugs 4.10.x 运行需 JDK 11+（4.10.2 特意保持 Java 11 兼容）；分析 Java 21 字节码（major 65）自 4.8.0 起支持；建议编排器用 JDK 17/21 跑扫描进程。

来源：<https://spotbugs.readthedocs.io/en/latest/running.html> · findsecbugs-cli 教程 <https://github.com/find-sec-bugs/find-sec-bugs/wiki/CLI-Tutorial> · maven 插件 <https://spotbugs.github.io/spotbugs-maven-plugin/plugin-info.html> · gradle 插件 <https://github.com/spotbugs/spotbugs-gradle-plugin> · FindSecBugs 描述符 <https://github.com/find-sec-bugs/find-sec-bugs/blob/master/findsecbugs-plugin/src/main/resources/metadata/findbugs.xml> · Java 21 支持 <https://github.com/spotbugs/spotbugs/issues/2567>

### 3.10 Semgrep / Opengrep 现状（降级为 Phase 3 可选）

- **Opengrep 1.30.0**（2026-09-07，另有 1.30.1-RC 与 2.0.0 alpha）：semgrep v1.100.0 的 fork，CLI 兼容（`scan` 子命令、`--config`、`--json`、`--sarif-output`，环境变量同认 `OPENGREP_*`/`SEMGREP_*`），本地规则文件可无缝使用。联盟维护（Aikido、Endor Labs、Orca、Kodem、Amplify），双周级发版，2026 活跃度良好；厂商口径比 semgrep CE 快 25–74%（非中立基准）。
- **规则生态是硬伤**：Opengrep **无官方托管 registry**——原 `opengrep/opengrep-rules`（fork 自 semgrep-rules）已于 **2025-11-28 归档只读**；semgrep 官方 registry（含 `p/` 规则集）受 **Semgrep Rules License v1.0** 约束（"only for internal business purposes"，禁止用于竞争产品/SaaS）→ **对 codespot 不可作为规则来源**。
- **结论**：引擎生产可用，但 codespot 若采用必须**自写规则集**（LGPL/自有许可）或引用第三方社区规则库（覆盖参差）。价值/工作量比不高 → 放 Phase 3 按需评估。

来源：<https://github.com/opengrep/opengrep> · 归档仓库 <https://github.com/opengrep/opengrep-rules> · semgrep FAQ（规则许可）<https://docs.semgrep.dev/faq> · OSS 变更公告 <https://semgrep.dev/blog/2024/important-updates-to-semgrep-oss/>

### 3.11 本地 Docker SonarQube 兜底路线（路线 C，不做）

- Community Build 免费、分析器内置；Java、Python、JavaScript、TypeScript、C#、Go、Kotlin、Rust 等全部在免费版（不含 C/C++/Swift/ObjC/Dart 等）。
- 资源：≤1M LOC 需 **4GB RAM、2 核、30GB 磁盘**；Linux 需 `vm.max_map_count=524288`；启动含 ES 建索引经验上 1–5 分钟。
- 导出：Web API `/api/issues/search` 返回 JSON；先例 [sonarless](https://github.com/gitricko/sonarless)（MIT）证明可工程化。
- 定位：规则保真度最高的兜底，但对"AI 写完随手扫"体验太重，**不做**。
- 语言矩阵：<https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/languages/overview/>

### 3.12 许可证合规：LGPL/SSAL 的"运行时下载"模式

依据 [GNU GPL/LGPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)：

- LGPL 义务以**分发（convey）**为触发点。codespot 只在脚本里写下载指令、组件由用户直接从 npm/PyPI/GitHub 官方源获取 → 分发主体是上游，**codespot 无任何义务，自身也无需开源**。
- CLI 通过命令行参数/管道调用分析器进程 = GNU FAQ 认定的"两个独立程序"通信方式（mere aggregation），LGPL 不传染。
- 若将来打包分发 LGPL JAR/包：需保留许可与版权声明、保证源码可得、保证可替换。codespot 自身代码仍可保持自己的许可。
- **真正的红线是两类**：① semgrep 官方规则许可（3.10，禁止竞争产品使用）；② SonarSource 系的 SSALv1（3.1，AI 摄取条款）。LGPL 组件（oxlint/PMD/SpotBugs/gitleaks 均为 MIT/Apache/LGPL 且运行时下载）按上述模式用即可，无风险。

### 3.13 SARIF 2.1.0 生态与 severity 映射

- **合并工具**：微软 SARIF MultiTool（`sarif merge`；dotnet tool 或 npm `@microsoft/sarif-multitool@5.7.0`）；微软 Python 包 `sarif-tools@3.0.5`（3.x 用 `sarif copy` 合并）。
- SARIF 2.1.0 单文件天然支持多 `runs[]`（每工具一个 run），合并本质是 runs 拼接——**codespot 自写 20 行代码即可合并，可不引依赖**。
- **severity 映射惯例**（采用 SonarQube 官方 SARIF 导入映射）：`error→CRITICAL`、`warning→MAJOR`、`note→MINOR`、`none→LOW`，未指定默认 MAJOR。codespot 内部保留工具原始 severity（Sonar 五级 / bandit H-M-L / SpotBugs rank / gitleaks 一律按泄漏处理），SARIF 层按惯例写 level，原始值放 `properties`。

### 3.14 现有先例

| 项目 | 一句话点评 |
|------|-----------|
| [SonarSource/sonarqube-mcp-server](https://github.com/SonarSource/sonarqube-mcp-server)（655★，官方，活跃） | 最接近 codespot 定位的官方实现，但它是"SonarQube 平台的门面"而非独立本地扫描器；SSAL 源码可得——**架构可参考，代码不能抄** |
| [semgrep/mcp](https://github.com/semgrep/mcp)（688★，官方） | 单引擎安全向，证明了"分析器→MCP→agent 修复"闭环可行 |
| SonarSource AI Code Assurance / AI Code Fix（商业） | 证明需求真实性，闭源不可复用 |
| [MegaLinter](https://megalinter.io) + megalinter-mcp | "多分析器聚合 + SARIF"的最佳架构参照（非 AI） |
| `@paretools/lint`（npm） | 轻量单点 lint MCP，说明生态位存在 |

---

## 4. 三条技术路线对比

| 维度 | 路线 A：封装 sonarlint-ls | 路线 B：干净引擎组合（推荐 v1） | 路线 C：Docker SonarQube |
|------|--------------------------|--------------------------------|--------------------------|
| 引擎 | sonarlint-ls.jar + 内嵌 sonarjava/python/js JAR（LSP/stdio 驱动） | oxlint+ESLint(sonarjs) / ruff+bandit / PMD(+SpotBugs+FSB) / gitleaks / SQLFluff | SonarQube Community Build + REST API |
| 规则保真度 | 最高（全量 Sonar 规则） | 中高（JS/TS 保留约一半 Sonar 规则 + 更广的开源规则面；Py/Java 为同类规则 + 独有安全/密钥层） | 最高 |
| 许可合规 | ⚠️ SSALv1 AI 条款灰区 | ✅ 无灰区 | ⚠️ 同 SSALv1 |
| 工程复杂度 | 高（LSP 编排，协议无官方承诺） | 低（全是标准 CLI） | 中（容器编排 + 项目创建 + 轮询） |
| 首次开销 | ~170MB + JDK 11+ | 每引擎几十 MB（oxlint/ruff/gitleaks 为单二进制，秒装） | 分钟级启动 + 4GB 内存 |
| 扫描速度 | 中 | **快**（oxlint 万文件 ~100ms；ruff 秒级；gitleaks dir 秒级） | 慢（含服务端分析） |
| 离线 | ✅ | ✅ | ❌（需拉镜像） |
| 维护风险 | 协议无承诺，升级可能 break | 各引擎独立升级，官方 CLI 稳定 | 随 SonarQube 大版本变化 |

---

## 5. 推荐方案与实现设计

### 5.1 总体架构

```text
用户（"扫一下代码"）
        │
        ▼
┌─ SKILL.md（触发与编排指令）────────────────────────────────────┐
│                                                                │
│  codespot scan --scope auto                                    │
│        │                                                       │
│        ▼                                                       │
│  ┌─ scope.py ───────── git 范围计算 → 目标文件 + 语言检测      │
│        │                                                       │
│        ▼                                                       │
│  ┌─ engine adapters（并行，按语言/维度分发）────────────────┐  │
│  │ 常开层（任何语言都跑）:                                    │  │
│  │   engine_secrets.py   gitleaks dir（密钥，critical）      │  │
│  │ 语言层（按目标文件语言启用）:                              │  │
│  │   engine_js.py        oxlint（快） + ESLint/sonarjs（深） │  │
│  │   engine_py.py        ruff（质量+json带fix） + bandit     │  │
│  │   engine_java.py      PMD（源码级，always）               │  │
│  │                       + SpotBugs/FindSecBugs（可编译时）  │  │
│  │   engine_sql.py       SQLFluff（AM/ST/RF 默认开）         │  │
│  │   engine_sonarls.py   (Phase 3, --engine sonar 实验选项)  │  │
│  └──────────────────┬─────────────────────────────────────────┘ │
│                     ▼ 统一 issue JSON                            │
│  ┌─ merge + severity 归一化（rules-severity.json）+ 去重 ────┐  │
│                     ▼                                           │
│   .codespot/report.json（agent 读）                             │
│   .codespot/report.md （人读摘要）                              │
│                     ▼                                           │
│   agent 呈现修复选项（AskUserQuestion）                         │
│                     ▼                                           │
│   修复循环：修复 → 重扫改动文件 → ≤3 轮 → 汇总                 │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 目录结构（codespot 仓库本身即 skill 包）

```text
codespot/                        # 根目录就是一个 skill
├── SKILL.md                     # 触发词 + 工作流编排（何时调哪个脚本、如何呈现修复选项）
├── scripts/
│   ├── codespot                 # 主控 CLI（Python 3，仅标准库）：setup | scope | scan | report
│   ├── setup.sh                 # 幂等下载各引擎到 ~/.codespot/engines/<name>-<version>/
│   ├── engines/                 # 每引擎一个适配器（契约见 6.2）——并行开发的单元
│   │   ├── registry.json        # 引擎注册表：语言、文件 glob、运行时依赖、默认开关
│   │   ├── engine_js.py         # oxlint + eslint(sonarjs) 去重编排
│   │   ├── engine_py.py         # ruff + bandit
│   │   ├── engine_java.py       # PMD + SpotBugs/FindSecBugs（探测构建）
│   │   ├── engine_sql.py        # SQLFluff（dialect 探测）
│   │   ├── engine_secrets.py    # gitleaks dir
│   │   └── engine_sonarls.py    # (Phase 3) sonarlint-ls LSP 驱动
│   ├── scope.py                 # git 范围计算
│   └── rules-severity.json      # 各引擎规则 → 统一四级 severity 的映射表（用户可覆盖）
├── assets/
│   ├── eslint.config.mjs        # sonarjs + eslint-plugin-oxlint 去重配置
│   ├── .oxlintrc.json           # correctness 类默认
│   ├── pmd-ruleset.xml
│   └── sqlfluff-defaults        # 关 LT/CP 的规则组配置
├── tests/fixtures/              # 每引擎一组夹具（含已知问题与预期发现）
└── docs/
    └── feasibility-research.md  # 本报告
```

安装：`ln -s <repo> ~/.agents/skills/codespot`（ZCode 标准发现路径，也兼容 `.zcode/skills` 覆盖机制）。

### 5.3 用户旅程（七步）

1. **触发**：用户说"扫一下代码 / codespot / 静态检查"→ SKILL.md 指示 agent 执行 `codespot scan`。
2. **首次自动 setup**：按目标文件语言懒下载引擎（只装用得上的），幂等、带版本锁定。oxlint/ruff/gitleaks 为单二进制（秒级安装）；ESLint 系需 node_modules；PMD 需 JRE 8+；SQLFluff 需 Python 3.10+（独立 venv，不污染用户环境）。
3. **增量范围**（三档 + 自定义，默认取第一个有内容的档位）：
   - `uncommitted`：`git status --porcelain`（含未跟踪文件）
   - `unpushed`：`git diff --name-only @{u}..HEAD` + 未提交部分（无上游分支时回退与 main 比较）
   - `ref:<ref>` / `all`：自定义基线 / 全量
4. **并行扫描**：常开层（gitleaks）+ 语言层按目标文件语言分发，输出归一为统一 issue 结构（5.4）。**去重**：JS/TS 内部由 eslint-plugin-oxlint 在规则层去重；跨引擎按 `file+line+message-hash` 保守合并（仅合并近乎相同的 finding，其余全部保留并标注引擎来源）。
5. **双报告**：`.codespot/report.json`（agent 读）+ `report.md`（按严重级分组的人读摘要，每条带可点击的 `file:line` 与规则链接）。
6. **修复选项**（agent 用 AskUserQuestion 呈现）：仅严重（critical）/ 重要及以上（major+）/ 全部 / 自定义（按规则或文件挑选）/ 仅查看报告。
7. **修复循环**：按文件分组修复 → 对改动文件重扫验证 → 最多 3 轮直到目标范围清零 → 汇总剩余问题与建议；提供"标记误报"通道（gitleaks 类写 `.gitleaksignore`，其余写 `.codespot/ignore`）；**不自动 commit**。

### 5.4 统一 issue 格式（report.json）

```json
{
  "tool": "gitleaks",
  "language": "*",
  "rule": "aws-access-token-id",
  "ruleUrl": "https://…",
  "severity": "critical",
  "file": "src/config.py",
  "line": 10,
  "column": 20,
  "message": "AWS Access Key ID detected",
  "snippet": "AKIA…(脱敏)",
  "cwe": "798",
  "fixHint": { "edit": "…可选，来自 ruff fix / eslint fixable…" }
}
```

密钥类 finding 的 `snippet` **必须脱敏**（只保留前后各 4 字符），避免报告本身泄漏密钥。

### 5.5 severity 归一化（rules-severity.json）

| 引擎 | 原始值 → critical / major / minor / info |
|------|------------------------------------------|
| gitleaks | 一律 critical（泄漏即最重） |
| ruff | 按规则族映射（S 家族高危→critical，F/E/W→major/minor），映射表可配置 |
| bandit | H→critical、M→major、L→minor |
| oxlint | 按 category：correctness 违规按规则映射（默认 major 起），style→minor |
| eslint（sonarjs） | bug 类→major+、code smell→minor，映射表可配置 |
| PMD | priority High→critical / Medium High→major / Medium→minor / Low→info |
| SpotBugs/FindSecBugs | rank 1–4（Scariest）→critical、5–9（Scary）→major、10–14→minor、15–20→info；FindSecBugs 安全类整体提一档 |
| SQLFluff | AM（歧义）/ST（结构）→major、RF→major/minor、CV 语义类→minor、LT/CP→info（默认关） |

---

## 6. 并行实施路径与迭代计划

### 6.1 设计原则：适配器契约先行，轨道互不依赖

引擎适配器是**并行开发的自然单元**：每轨交付物 = 一个 `engine_*.py` + 对应 `assets/` 配置 + `tests/fixtures/` 夹具，只要遵守统一契约，各轨可由不同会话/子代理同时开发、独立测试，最后只做注册合并。**关键路径不在引擎数量，而在基座（Track 0）与修复循环（Track F）**。

### 6.2 适配器契约（使并行可实施的核心约定）

```text
engine_<name>.py 的调用契约（由主控 CLI 保证）：
  输入:  --workdir <仓库根> --files <清单文件> --out <结果json路径>
         [--config <项目配置覆盖>] [--setup-only]
  输出:  统一 issue JSON（schema 见 5.4），外加 engine 级元信息（耗时、引擎版本、退出原因）
  退出码: 0 = 引擎运行成功（不论有无发现）；2 = 引擎自身失败（缺运行时/配置错）
          ——"发现问题的数量"不进退出码，由主控合并后统一判定
  注册:  engines/registry.json 声明 { languages, glob, runtime, always_on, setup_cmd, version_lock }
```

主控 CLI 只做四件事：范围计算 → 按注册表选引擎并行调用 → 合并归一化 → 出双报告。引擎增删不触碰主控代码。

### 6.3 轨道划分与依赖关系

```text
Track 0 基座（串行，先行，~半天）
  主控 CLI + scope.py + 注册表 + 统一 issue schema + 双报告渲染 + SKILL.md 骨架
        │
        ├── 解锁以下六轨（互相独立，可全并行）:
        │
        ├─ Track A  JS/TS 引擎      oxlint + ESLint(sonarjs) + 去重 + 夹具
        ├─ Track B  Python 引擎      ruff + bandit + 夹具
        ├─ Track C  Java 引擎        PMD（前半）→ SpotBugs/FSB 编排（后半）
        ├─ Track D  密钥层           gitleaks dir + 脱敏渲染 + .gitleaksignore 通道
        ├─ Track E  SQL 引擎         SQLFluff + dialect 探测 + LT/CP 分流
        └─ Track F  修复循环打磨     SKILL.md 工作流 + 修复选项 + 重扫验证 + ignore 通道
        │
        └── 后置轨道（依赖前面成果）:
           Track G  实验与扩展   sonarlint-ls 适配器 / tsgolint 类型感知 / Opengrep 自写规则
           Track H  发布         ZCode plugin 打包 / CI SARIF / 文档
```

### 6.4 里程碑（每步都有可验收的端到端演示）

| 里程碑 | 内容 | 包含轨道 | 验收标准 |
|--------|------|----------|----------|
| **M0 端到端闭环** | 基座 + 两个最轻引擎（gitleaks + ruff） | 0 + D + B(ruff 部分) | 夹具项目（含硬编码 AWS key + Python 问题代码）→ `scan --scope uncommitted` → 双报告 → agent 呈现修复选项 → 修复 → 重扫清零；密钥在报告中脱敏 |
| **M1 核心三语言** | JS/TS 双层 + Java 源码级 + 修复循环完整 | + A + C(前半) + F | JS/TS/Java 夹具扫描+修复；oxlint 与 ESLint 对同一问题**不重复报告**；修复循环 ≤3 轮收敛 |
| **M2 深度与长尾** | SpotBugs/FindSecBugs 编排 + bandit + SQLFluff + severity 配置化 | + C(后半) + B(bandit) + E | Maven 与 Gradle 夹具编译后能扫出 FindSecBugs 问题（含 CWE 编号）；SQL 夹具 dialect 探测或友好询问；`rules-severity.json` 用户可覆盖 |
| **M3 实验与增强** | sonarlint-ls 实验适配器（明示 SSALv1 灰区）、tsgolint 类型感知、Opengrep 自写规则评估、`.codespot.toml` | + G | `--engine sonar` 在夹具上跑通（标注实验性）；类型感知规则在合成 tsconfig 下生效 |
| **M4 发布** | ZCode plugin 打包、CI SARIF 上传、文档 | + H | 作为 plugin 安装后开箱可用；SARIF 可被 GitHub code scanning 消费 |

### 6.5 引擎优先级矩阵（价值/工作量/风险）

| 引擎 | 用户价值 | 实现工作量 | 风险 | 优先级 |
|------|---------|-----------|------|--------|
| gitleaks（密钥） | 高（AI 代码高频问题，泄漏代价极大） | 极低（单二进制 + json） | 低 | **P0** |
| ruff（Python） | 高 | 低 | 低 | **P0** |
| oxlint+ESLint(sonarjs)（JS/TS） | 高 | 中（双引擎编排 + 去重配置） | 低（均有官方支持） | **P1** |
| bandit（Python 安全） | 中高 | 低 | 低 | **P1** |
| PMD（Java） | 高（Java 用户刚需） | 低 | 低 | **P1** |
| 修复循环（Track F） | **极高（产品核心体验）** | 中 | 中（需反复调 SKILL.md 措辞） | **P1（与引擎并行）** |
| SpotBugs+FSB（Java 深度） | 中（需可编译项目） | 中高（构建探测编排） | 中（mvn/gradle 环境差异） | P2 |
| SQLFluff | 中（SQL 项目才用） | 中（dialect 探测） | 中（慢、解析失败处理） | P2 |
| sonarlint-ls（sonar 风味） | 中（规则全但有替代） | 高（LSP 编排） | 高（协议 + SSALv1） | P3 |
| Opengrep（自写规则） | 中低（前期） | 高（规则开发） | 中（规则生态薄弱） | P3 |
| tsgolint 类型感知 | 中 | 中 | 中（TS 7 依赖） | P3 |

### 6.6 "并行"在开发方式上的落地

- **多会话/多代理并行**：Track A–F 各自独立成任务，可派子代理或开独立会话同时开发（每轨 = 一个适配器文件 + 夹具 + 在 registry.json 加一行），互不冲突；合并只涉及注册表。
- **同会话串行的推荐顺序**（单人实施时）：M0（Track 0+D+B）→ A+C 前半+F（M1）→ 其余。
- **夹具即测试**：每轨的 `tests/fixtures/` 内放"已知问题 + 预期发现清单"，`codespot selftest` 子命令回归全量夹具——任何引擎升级后跑一遍即可验证不破坏契约。

---

## 7. 风险与限制（如实列出）

| 风险 | 说明 | 缓解 |
|------|------|------|
| SSALv1 AI 条款 | 若引入 sonar 系引擎（路线 A/C），"AI 摄取输出数据"条款存在灰区 | v1 用干净引擎；`--engine sonar` 启用时明示风险；开源分发前法务确认 |
| oxlint jsPlugins 是 alpha | 未来可用 oxlint 直载 sonarjs 插件，但当前生产风险高 | v1 用"oxlint + ESLint + eslint-plugin-oxlint 去重"的官方稳妥路线 |
| 类型感知规则 | sonarjs 数十条规则要求被扫文件在 tsconfig 内 | v1 跳过；Phase 3 合成 tsconfig / 评估 tsgolint |
| Java 深度分析需编译 | SpotBugs 层要求 mvn/gradle 编译成功，AI 半成品常不满足 | PMD 源码级为主引擎；SpotBugs 仅在构建可用时启用并跳过得体 |
| SQLFluff 体验 | 必须显式 dialect；大文件偏慢；LT/CP 规则产生修复噪音 | dialect 探测链 + 询问用户；默认关 LT/CP；解析失败单列不进修复清单 |
| gitleaks 退出码歧义 | 1 同时表示"发现泄漏"和"出错" | 适配器结合 stderr/报告文件判定 |
| 误报 | 静态分析误报会污染 AI 修复循环 | SKILL.md 写死"agent 修复前先判断 issue 合理性"；`.gitleaksignore` / `.codespot/ignore` 误报通道 |
| 首次下载与环境 | 依赖网络与 node/java/python 运行时（各引擎要求不一） | setup 做环境探测并给出缺失项提示；单二进制引擎（oxlint/ruff/gitleaks）优先 |
| sonarlint-ls 协议（Phase 3） | 自定义扩展协议无官方承诺，版本升级可能 break | 锁定 LS 版本；适配器隔离在单文件 |
| 规则 ID 体系差异 | ruff/PMD/oxlint 与 Sonar RSPEC 编号不同 | 映射表启发式对齐（ruleUrl 始终指向官方文档） |
| Opengrep 规则生态 | 无官方 registry，规则必须自备 | 降级 Phase 3；若做则自写 LGPL 规则包 |

---

## 8. 附录：版本快照（2026-09-23 核验）

| 组件 | 版本 | 许可 | 核验渠道 |
|------|------|------|----------|
| oxlint | 1.85.0（2026-09-21，周更） | MIT | npm registry API |
| eslint-plugin-oxlint | 1.85.0（与 oxlint 同步发布） | MIT | npm registry API |
| oxlint-tsgolint | 7.0.2002（2026-09-18，编码 TS 7.0.2） | MIT | npm registry API |
| ESLint | 9.x | MIT | npm |
| eslint-plugin-sonarjs | 4.2.1（2026-09-15） | ⚠️ LICENSE 文件 SSALv1 / package.json LGPL-3.0-only（矛盾，保守对待） | npm registry API |
| SonarJS 分析器 | 13.9.0（2026-09-08） | SSALv1 | GitHub Releases |
| typescript-eslint | 8.70.1 | MIT | npm registry API |
| @microsoft/eslint-formatter-sarif | 3.1.0（2024-04-12 后未更新） | MIT | npm registry API |
| ruff | 0.16.8 | MIT | PyPI API |
| bandit | 1.9.4 | Apache-2.0 | PyPI API |
| pylint | 4.0.8 | GPL-2.0 | PyPI API |
| PMD | 7.27.0（2026-08-28） | Apache-2.0 | GitHub Releases |
| Checkstyle | 14.1.0（2026-08-30） | LGPL-2.1 | GitHub Releases（JDK 21 依据仓库 pom.xml） |
| SpotBugs | 4.10.4（2026-08-20） | LGPL-2.1 | GitHub Releases |
| spotbugs-maven-plugin | 4.10.4.1（2026-09） | LGPL-2.1 | 官方插件站点 |
| spotbugs-gradle-plugin | 6.5.6（配 SpotBugs 4.10.2） | LGPL-2.1 | GitHub |
| find-sec-bugs | 1.14.0（2025-06-17；144 检测器） | LGPL-2.1 | GitHub Releases API |
| gitleaks | 8.30.1（2026-03-21；222 条内置规则） | MIT | GitHub Releases API |
| SQLFluff | 4.3.0（2026-08-07；SARIF 自 4.0.1） | MIT | PyPI API |
| sonarlint-language-server | 5.9.0.79716（2026-09-14） | LGPL-3.0 | Maven Central |
| sonarlint-backend-cli (sonarlint-core) | 11.10.0.86299 | LGPL-3.0 | Maven Central |
| sonarlint-vscode VSIX | 5.10.0+80769 | — | GitHub Releases（内嵌 LS + 14 分析器 JAR） |
| SonarQube CLI (`sonar`) | 1.8.0.5274（2026-09-15） | CLI 代码 LGPL-3.0 | GitHub Releases API |
| Opengrep | 1.30.0（2026-09-07）+ 1.30.1-RC | LGPL-2.1（引擎） | GitHub Releases |
| semgrep CE | 引擎 LGPL-2.1；官方规则 = Semgrep Rules License v1.0（仅内部使用） | — | 官方 licensing 文档 |
| @microsoft/sarif-multitool | 5.7.0 | MIT | npm registry API |
| sarif-tools | 3.0.5 | MIT | PyPI API |
| trufflehog（对比项） | — | **AGPL-3.0**（不集成） | GitHub |
| detect-secrets（对比项） | — | Apache-2.0（活跃度下滑，不集成） | GitHub |

---

## 9. 参考链接汇总

**Sonar 官方**
- SSALv1 公告：<https://community.sonarsource.com/t/a-new-sonar-license-for-sonarqube-analyzers/120106>
- SonarQube CLI：<https://github.com/SonarSource/sonarqube-cli> · <https://docs.sonarsource.com/sonarqube-cli/>
- sonarlint-language-server：<https://github.com/SonarSource/sonarlint-language-server> · Maven：<https://repo1.maven.org/maven2/org/sonarsource/sonarlint/ls/sonarlint-language-server/>
- sonarlint-vscode releases（VSIX 内嵌分析器）：<https://github.com/SonarSource/sonarlint-vscode/releases>
- sonar-java：<https://github.com/SonarSource/sonar-java> · sonar-python：<https://github.com/SonarSource/sonar-python> · SonarJS：<https://github.com/SonarSource/SonarJS>
- SonarLint 产品页（standalone 模式）：<https://www.sonarsource.com/products/sonarlint/>
- SonarQube 语言矩阵：<https://docs.sonarsource.com/sonarqube-server/analyzing-source-code/languages/overview/>
- SonarQube SARIF 导入 severity 映射：<https://docs.sonarsource.com/sonarqube-server/latest/analyzing-source-code/importing-external-issues/importing-issues-from-sarif-reports/>

**社区实证**
- sonarlint-ls-cli（路线 A 原型）：<https://github.com/vincentfenet/sonarlint-ls-cli>
- sonarlint.nvim：<https://gitlab.com/schrieveslaach/sonarlint.nvim> · sonarlint-ls-wrapper：<https://github.com/burrima/sonarlint-ls-wrapper>
- sonarless（Docker 临时 SonarQube 先例）：<https://github.com/gitricko/sonarless>

**JS/TS**
- oxlint 文档：<https://oxc.rs/docs/guide/usage/linter>（规则 / config / cli / type-aware / js-plugins 各子页）
- oxc 仓库：<https://github.com/oxc-project/oxc> · tsgolint：<https://github.com/oxc-project/tsgolint>
- eslint-plugin-oxlint（去重插件）：<https://github.com/oxc-project/eslint-plugin-oxlint>
- oxlint 1.0 公告：<https://voidzero.dev/posts/announcing-oxlint-1-stable>
- eslint-plugin-sonarjs：<https://www.npmjs.com/package/eslint-plugin-sonarjs> · 规则表：<https://github.com/SonarSource/SonarJS/blob/master/packages/analysis/src/jsts/rules/README.md>
- @microsoft/eslint-formatter-sarif：<https://www.npmjs.com/package/@microsoft/eslint-formatter-sarif> · sarif-js-sdk：<https://github.com/Microsoft/sarif-js-sdk>
- typescript-eslint typed-linting：<https://typescript-eslint.io/linting/typed-linting/>

**Python / Java**
- ruff 规则/配置/输出格式：<https://docs.astral.sh/ruff/rules/> · <https://docs.astral.sh/ruff/configuration/>
- bandit formatters：<https://github.com/PyCQA/bandit/tree/main/bandit/formatters>
- PMD CLI/报告格式：<https://docs.pmd-code.org/latest/pmd_userdocs_cli_reference.html> · <https://docs.pmd-code.org/latest/pmd_userdocs_report_formats.html>
- SpotBugs 运行文档：<https://spotbugs.readthedocs.io/en/latest/running.html> · findsecbugs-cli 教程：<https://github.com/find-sec-bugs/find-sec-bugs/wiki/CLI-Tutorial>
- spotbugs-maven-plugin：<https://spotbugs.github.io/spotbugs-maven-plugin/plugin-info.html> · spotbugs-gradle-plugin：<https://github.com/spotbugs/spotbugs-gradle-plugin>
- find-sec-bugs：<https://find-sec-bugs.github.io/> · 描述符：<https://github.com/find-sec-bugs/find-sec-bugs/blob/master/findsecbugs-plugin/src/main/resources/metadata/findbugs.xml>

**密钥 / SQL / 跨语言**
- gitleaks：<https://github.com/gitleaks/gitleaks>（命令/退出码/ignore/baseline 均见 README 与 cmd/ 源码）
- SQLFluff 文档：<https://docs.sqlfluff.com/en/stable/>（cli / rules / dialects 各参考页）· PyPI：<https://pypi.org/project/sqlfluff/>
- semgrep 许可：<https://docs.semgrep.dev/licensing/> · OSS 更新公告：<https://semgrep.dev/blog/2024/important-updates-to-semgrep-oss/> · FAQ：<https://docs.semgrep.dev/faq>
- Opengrep：<https://github.com/opengrep/opengrep> · 归档规则库：<https://github.com/opengrep/opengrep-rules>

**SARIF 与许可证**
- SARIF 2.1.0 规范：<https://docs.oasis-open.org/sarif/sarif/v2.1.0/os/sarif-v2.1.0-os.html>
- SARIF MultiTool：<https://github.com/microsoft/sarif-sdk> · npm：<https://www.npmjs.com/package/@microsoft/sarif-multitool> · sarif-tools：<https://pypi.org/project/sarif-tools/>
- GNU GPL/LGPL FAQ：<https://www.gnu.org/licenses/gpl-faq.en.html> · LGPL-3.0 文本：<https://www.gnu.org/licenses/lgpl.html>

**AI + 静态分析先例**
- sonarqube-mcp-server：<https://github.com/SonarSource/sonarqube-mcp-server>
- semgrep/mcp：<https://github.com/semgrep/mcp> · Semgrep Guardian：<https://docs.semgrep.dev/semgrep-guardian/>
- SonarSource AI Code Assurance：<https://www.sonarsource.com/solutions/ai-code-assurance/>
- MegaLinter：<https://megalinter.io>
