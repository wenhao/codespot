# codespot（中文说明）
代码静态分析工具

面向 AI agent 的本地静态代码扫描 skill：通过 git 识别改动文件（未提交 / 未推送 / 全量），按语言调用多个扫描引擎，产出机器可读报告，驱动 AI 辅助修复闭环。

- **8 个检查维度**（见[引擎矩阵](#引擎矩阵)）：密钥泄漏、Python 质量与安全、JS/TS、Java（源码级 + 字节码级）、SQL、依赖漏洞、跨语言语义/taint 分析。
- **默认增量扫描**：只扫你改过的代码（未提交 → 未推送 → 全量，自动降级）。
- **对 AI 友好**：`.codespot/report.json` 保留完整内部字段供 AI 修复；`.codespot/report.md` 是面向人类的 codespot 品牌摘要（统一 `CS-xxxxx` 规则编号）。
- **许可说明**：内部工具。Semgrep CE 的官方规则按 "internal business purposes"（仅限内部业务使用）条款使用——见[许可边界](#许可边界)。

## 安装与快速开始

skill 的可安装载荷全部在 `skill/` 子目录（文档与 openspec 规划文件不进入用户环境）：

```bash
ln -s <仓库>/skill ~/.agents/skills/codespot
```

```bash
# 1. 安装引擎（幂等；按项目需要自动选择）
~/.agents/skills/codespot/scripts/codespot setup

# 2. 扫描（在任意 git 仓库；scope auto = 未提交 → 未推送 → 全量 自动降级）
~/.agents/skills/codespot/scripts/codespot scan --scope auto

# 3. 查看报告
cat .codespot/report.md     # 人类可读，codespot 品牌（CS-xxxxx 编号）
cat .codespot/report.json   # AI agent 用：内部字段（tool/rule/ruleUrl）+ csId
~/.agents/skills/codespot/scripts/codespot show --severity critical,major   # 浏览问题详情
~/.agents/skills/codespot/scripts/codespot show --rule CS-5ebd4             # 定位某条规则的命中

# 回归自检（夹具驱动，覆盖全部引擎）
~/.agents/skills/codespot/scripts/codespot selftest
```

引擎下载到 `~/.codespot/engines/`（版本锁定）；报告落在目标仓库的 `.codespot/`——请把 `.codespot/` 加进项目的 `.gitignore`。

## CLI 参考

| 命令 | 用途 |
|---|---|
| `codespot setup [引擎…]` | 安装引擎（幂等、版本锁定；单个失败不阻塞其他） |
| `codespot scope --scope <档位>` | 打印扫描将使用的文件清单 |
| `codespot scan --scope <档位> [--engine 名称…]` | 运行所有匹配引擎（含显式点名的 opt-in 引擎），写出双报告 |
| `codespot show [--severity 级别] [--file 前缀] [--rule CS-编号] [--limit N] [--all]` | 浏览最近一次报告的问题详情 |
| `codespot report` | 打印最近一次 report.json |
| `codespot update-db` | 下载/刷新本地 OSV 漏洞库（启用离线依赖扫描） |
| `codespot selftest` | 夹具驱动的全引擎回归自检 |

**opt-in 引擎**：registry 中标记 `opt_in` 的引擎（当前为 TruffleHog）默认绝不运行——用可重复的 `--engine <名称>` 显式点名，或通过 `.codespot/config.json` 永久启用：`{"rules": {"secrets_deep": {"enabled": true}}}`。

**扫描范围**（`--scope`）：`auto`（默认：未提交 → 未推送 → 全量取第一个非空）、`uncommitted`（含未跟踪文件）、`unpushed`（无上游分支时回退与 `main` 比较）、`ref:<ref>`、`all`。

**退出码**（scan/setup）：`0` = 流程完成（是否有问题不改变退出码——后续动作由 agent 依据报告决定）；`2` = 编排/安装失败。CI 提示：只要扫描流程本身成功退出码就是 0，流水线可以放心发布报告而不打断构建。

## 引擎矩阵

| 类别（配置键） | 引擎 | 运行要求 | 说明 |
|---|---|---|---|
| `secrets`（常开） | gitleaks 8.30 | — | `dir` 模式，报告强制脱敏 |
| `python_lint` | ruff 0.16 | — | JSON 输出保留修复建议 |
| `python_security` | bandit | python3（独立 venv） | |
| `js_lint` | oxlint 1.85 | — | 快速层 |
| `js_lint`（深度） | ESLint + eslint-plugin-sonarjs | node/npm | 无 node/npm 时优雅降级为快速层 |
| `java` | PMD 7.27 | JRE 8+ | 源码级，无需编译 |
| `java`（深度，可选） | SpotBugs 4.10 + FindSecBugs 1.14 | mvn/gradle + JDK | 项目不可编译时自动跳过 |
| `sql` | SQLFluff | python3（独立 venv） | 方言自动探测链 |
| `semantic` | Semgrep CE 1.177（py3.9 回退 1.136） | python3（独立 venv） | Go/C#/Kotlin/Ruby/PHP/Rust/Terraform…；规则从官方 registry 拉取 |
| `dependencies` | OSV-Scanner 2.6 | —（查询 osv.dev） | 扫描 requirements/锁文件/pom/go.mod 的已知 CVE |
| `secrets_deep`（**opt-in**） | TruffleHog 3.97 | — | 800+ 检测器；默认 `--no-verification`（纯本地）；仅 `--engine trufflehog` 或 `rules.secrets_deep.enabled` 时运行 |
| `ai_review`（**opt-in**，agent 驱动） | AI agent 本身 | — | 语义级审查（逻辑/并发/错误处理缺口）；`scan --engine ai` → 按 `.codespot/ai-plan.json` 分析 → `codespot ai-scan absorb`；发现为建议性并附 confidence |

## 各语言规则数量与去重

下表数量是 codespot **实际启用**的规则数（2026-09-23 对本机安装引擎逐一实测），不是各工具的完整目录。

| 语言 | 质量 / 规范 | 安全 | 依赖 / 供应链 |
|---|---|---|---|
| Python | ruff：**启用 503 条**（定义共 970；E/W/F/PL/B/RUF 族，剔除风格噪音） | ruff S 族 + bandit（32 个插件，B1xx–B7xx） | OSV-Scanner（osv.dev 公告库） |
| JavaScript / TypeScript | oxlint：**启用 335 条**（correctness 272 + suspicious 63，共 870） | eslint-plugin-sonarjs：**约 215 条 Sonar 规则**（bug/安全/坏味道） | OSV-Scanner（package-lock/yarn.lock） |
| Java | PMD：**启用 213 条**（226 条类别规则 − 13 条排除；errorprone/bestpractices/security/design/multithreading） | SpotBugs **约 470 个 bug 模式** + FindSecBugs **144 个安全检测器**（带 CWE，字节码级，需可编译） | OSV-Scanner（pom.xml） |
| SQL | SQLFluff：**启用约 48 条**（共 68；剔除 layout/capitalisation 排版组） | — | — |
| Go / C# / Kotlin / Ruby / PHP / Rust / Swift / Scala | 适用处由 oxlint/ESLint 覆盖 | Semgrep `auto` 规则包（**2800+** 条 registry 规则） | OSV-Scanner（go.mod/Cargo/composer/Gemfile/*.csproj） |
| 密钥（任意语言） | — | gitleaks：**222 条规则**（厂商密钥/私钥/熵值启发式）；TruffleHog 深度层（opt-in）：**800+ 检测器** | — |

**工具间去重**（有意设计，已在 express/jsoup 验证扫描中实测）：

- **JS/TS**：`eslint-plugin-oxlint` 会关闭所有快速层（oxlint）已覆盖的 ESLint-core/typescript-eslint 规则——每个问题只报一次。sonarjs 只贡献其独有的 Sonar 规则（与 no-unused-vars 重复的变体已显式关闭）。
- **Python**：ruff 的 flake8-bandit（`S` 族）与 bandit 的 `B` 族在安全主题上有意重叠；两者都运行，因为规则语义不同。发现保留各自规则编号，不会丢失信息。
- **Java**：PMD（源码级、无需编译）与 SpotBugs/FindSecBugs（字节码级、需可编译）是互补的两层；少量重叠（如资源关闭类）是有意保留的。
- 同一行上不同引擎的重复**发现**不做合并——不同工具的判定结果都被保留并标注来源。

## 规则删减、调参与参数调整

所有配置都在**被扫描的项目**里，绝不放在 `~/.codespot`。三层配置，优先级从高到低：

### 1. 原生配置文件（能力完整，调参推荐）

项目里存在原生配置时，codespot 对该引擎**直接采用**（替代内置默认）：

| 文件 | 作用范围 |
|---|---|
| `.ruff.toml` / `ruff.toml` / `pyproject.toml` 的 `[tool.ruff]` | ruff——规则选择/忽略、`line-length` 等全部参数 |
| `.oxlintrc.json` | oxlint——类别与规则 |
| `.sqlfluff` | SQLFluff——方言、规则、排版行为 |
| `.gitleaks.toml` | gitleaks——自定义规则 / 白名单 |

示例——放宽行宽并忽略两条 ruff 规则，创建 `.ruff.toml`：

```toml
line-length = 120
[lint]
ignore = ["E501", "PLR0913"]
```

### 2. `.codespot/config.json`（简单开关，codespot 风格）

使用**检查类别**（无需书写引擎名）：

```json
{
  "dialect": "postgres",
  "semgrep_config": "p/gosec",
  "rules": {
    "python_security": {"disabled": true},
    "python_lint": {"ignore": ["RUF100"]},
    "dependencies": {"ignore": ["GHSA-xxxx-yyyy-zzzz"]}
  }
}
```

- `rules.<类别>.disabled: true` —— 整体关闭该类别。
- `rules.<类别>.ignore: [规则编号…]` —— 删减特定发现（编号为 report.json 中出现的底层规则码）。
- `dialect` —— 方言无法自动探测时指定 SQLFluff 方言。
- `semgrep_config` —— 覆盖默认 `auto` 规则集（可为 registry 规则集、本地规则目录或单个规则文件）。

类别：`secrets`、`python_lint`、`python_security`、`js_lint`、`java`、`sql`、`semantic`、`dependencies`。

### 3. codespot 内置默认（兜底）

位于 `codespot/skill/assets/`——以上两层都不存在时生效。

**严重级调整**（某规则分级不合意）通过 `.codespot/severity-overrides.json`：

```json
{"ruff": {"rules": {"RUF100": "info"}}, "pmd": {"default": "minor"}}
```

**误报**（某处特定命中）：加入 `.codespot/ignore`：

```json
[{"tool": "ruff", "file": "src/app.py", "rule": "PLW0603"}]
```

密钥误报使用 gitleaks 自带的指纹文件：把发现中的 `Fingerprint` 写入仓库根目录的 `.gitleaksignore`。

## 漏洞数据库与引擎更新

- **依赖漏洞（OSV-Scanner）—— 离线优先**：
  - 尚无本地库时：每次扫描实时查询 [osv.dev](https://osv.dev) API（数据永远最新，需要联网）。
  - 运行一次 `codespot update-db` 下载本地漏洞库（缓存于 `~/Library/Caches/osv-scalibr/` 或 `~/.cache/osv-scalibr/`）。
  - 本地库存在后，依赖扫描完全离线（自动加 `--offline-vulnerabilities`）；重跑 `codespot update-db` 即可刷新。适配器自动选择：有离线库走离线，没有走在线。
- **Semgrep 规则**：从官方 registry 拉取后缓存于 `~/.semgrep/`。重复扫描复用缓存；删除 `~/.semgrep/cache`（或换用其他规则集）可强制刷新。
- **引擎升级**：引擎版本锁定在 `scripts/engines/registry.json`（`version` 字段）。升级时改版本号并重跑 `scripts/codespot setup`（旧版本保留在 `~/.codespot/engines/`，可手动删除）。
- **重置某个引擎**：`rm -rf ~/.codespot/engines/<name>-<version>` 后重新 `codespot setup`。

## 平台兼容性（Windows 支持现状）

codespot 主体为纯 Python 标准库实现，**大部分能力天然跨平台**，但当前版本在 Windows 上有以下已知差异（开发与验证均在 macOS/Linux 完成，Windows 属"可支持但未实测"）：

| 维度 | 现状 | 说明 |
|---|---|---|
| 主控 CLI / 报告 / scope | ✅ 兼容 | 纯 Python 标准库；路径已统一正斜杠输出 |
| gitleaks / ruff / oxlint / OSV-Scanner | ⚠️ 需补充 | 各自官方均有 Windows 二进制；registry 的 `os_map` 目前只登记了 darwin/linux，需增加 `windows` 条目 |
| PMD / SpotBugs | ⚠️ 需小改 | 发行包本身跨平台；codespot 生成的启动 wrapper 是 shell 脚本，需改用各自自带的 `.bat` 启动器 |
| SQLFluff / bandit | ✅ 兼容 | 纯 Python，venv 安装形态天然跨平台 |
| Semgrep CE | ❌ 不支持 | 官方不提供 Windows 原生版本，需 WSL2 或 Docker；这是 Windows 上唯一的功能性缺口（`semantic` 类别不可用，其余类别不受影响） |
| 符号链接聚合（密钥大批量场景） | ⚠️ 已有回退 | Windows 创建符号链接需要特权；适配器已有复制回退逻辑 |

若需要正式支持 Windows：预计工作量约一天（补 registry 平台映射、wrapper 改 .bat、修正 `file:///C:/...` URI 解析），并需在真实 Windows 环境跑一轮 selftest。

## 离线使用指南

**提前准备（联网环境做一次即可）**：

1. `codespot setup` —— 把全部所需引擎下载到本地（此后引擎本体不再需要网络）。
2. `codespot update-db` —— 下载 OSV 本地漏洞库，启用离线依赖扫描。
3. 跑一次在线扫描 —— 预热 Semgrep 规则缓存（`~/.semgrep/`）；JS/TS 深度层的 ESLint 规则随 setup 已本地化。

**之后离线扫描的各引擎表现**：

| 引擎 | 离线状态 |
|---|---|
| gitleaks / ruff / oxlint / PMD / SpotBugs / SQLFluff / bandit / ESLint 深度层 | ✅ 完全离线 |
| OSV-Scanner | ✅ 有本地库时完全离线（`update-db` 后）；无库时引擎失败并被隔离 |
| Semgrep | ⚠️ 有规则缓存时通常可用；`auto` 模式可能尝试访问 registry 失败——严格离线场景建议在 config.json 把 `semgrep_config` 指向本地规则目录 |

**失败语义**：任何引擎离线失败都会进入 `report.json` 的 `engine_errors`（并被人读报告以中性措辞提示），**不会阻塞或污染其他引擎的结果**。

## 报告与品牌

- `report.md` / `codespot show` 是 **codespot 品牌**：每条规则有稳定的 `CS-xxxxx` 编号（由底层规则派生——同规则同编号，跨仓库跨次扫描一致）。不会向用户显示底层引擎名称。
- `report.json` 是 agent 接口：每条问题保留 `tool` / `rule` / `ruleUrl` / `csId` / `fixHint`，AI 可据此精确研究与修复。
- 密钥类发现在两份报告中都强制脱敏（保留前后 4 字符）。发现真实密钥：**先轮换密钥**——已提交进历史的密钥，删行不等于止损。

## 新增引擎

引擎是自包含适配器，添加步骤：

1. 编写 `scripts/engines/engine_<name>.py`，实现契约：`--workdir <仓库根> --files <清单.json> --out <结果.json>`；成功退出 `0`（结果为 issue JSON 数组），失败退出 `2`（原因写 stderr）。
2. 输出统一 issue schema（见 `common.make_issue`）——severity 经 `scripts/rules-severity.json` 归一化。
3. 在 `scripts/engines/registry.json` 注册（安装形态、版本、语言、类别），并在 `tests/fixtures/` + `expected.json` 添加夹具。

## 已知限制与建议改进

- **JS/TS 类型感知规则**未开启（需要 tsconfig）；纯 Python 仓库不受影响。
- **SpotBugs 深度层**需要项目可编译；否则静默跳过（PMD 源码级仍然覆盖）。
- **OSV-Scanner 需要联网**（除非先 `update-db`）；离线漏洞库模式已支持。
- **Dockerfile**（无扩展名）尚未被语言检测识别；可通过 `semgrep_config` 让 semgrep 覆盖。
- **`.codespot/config.json` 是唯一的项目配置入口**——可按需增加 `.codespot.toml` 变体与按路径的规则作用域。
- **py3.9 机器上 SQLFluff** 运行 3.x 旧线（4.x 需要 python ≥3.10）。
- **Windows**：见[平台兼容性](#平台兼容性windows-支持现状)。

## 许可边界

codespot 是内部工具。TruffleHog（AGPL-3.0）与 Semgrep CE 及其 registry 规则按 Semgrep Rules License 的 "internal business purposes"（仅限内部业务使用）条款使用——规则在用户机器上运行时拉取，不随 codespot 打包或分发。**请勿在启用该引擎的状态下对外销售或分发 codespot。**

## 文档
- [可行性调研报告](docs/feasibility-research.md) — 技术选型、引擎矩阵、路线对比、实现设计与并行迭代计划（2026-09-23，两轮调研）
- [开源项目验证报告](docs/validation-report.html) — requests / express / jsoup 三仓库实测（2026-09-23）
- 实施按 OpenSpec 变更分批推进：`openspec/changes/archive/`（M0 基座、M1 JS/TS + Java + 修复循环、M2 深度层、semgrep 与依赖扫描均已交付；实验性 M3/M4 已取消）
