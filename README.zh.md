<div align="center">

# codespot（中文说明）

**为 AI 编码 agent 而生的本地多引擎静态代码扫描。**

![engines](https://img.shields.io/badge/engines-10-blue)
![languages](https://img.shields.io/badge/languages-12%2B-green)
![runtime](https://img.shields.io/badge/runtime-python%20stdlib%20only-informational)
![offline](https://img.shields.io/badge/offline-ready%20(via%20update--db)-9cf)
![license](https://img.shields.io/badge/license-internal%20use-important)

[English](README.md) | 中文

📖 [项目汇报（图文版）](docs/project-report.html) · [可行性调研报告](docs/feasibility-research.md) · [验证报告](docs/validation-report.html)

</div>

## 概览

- **是 skill，不是服务器。** codespot 完全运行在本机、以 AI agent skill 形态存在：没有 SonarQube 式服务端、没有账号、代码不出仓库。任何支持 `~/.agents/skills` 发现机制的 agent 都能使用。
- **十个引擎，一份报告。** 密钥、Python 质量与安全、JS/TS、Java（源码+字节码）、SQL、跨语言 taint、依赖 CVE——全部归一为一份按严重级排序的报告，规则带稳定 `CS-xxxxx` 编号。
- **默认增量扫描。** 只扫你改动的部分（未提交 → 未推送 → 全量自动降级），契合"生成、扫描、修复、重扫"的 AI 编码节奏。
- **Agent 优先输出。** `report.json` 保留完整内部字段（tool/rule/ruleUrl/fixHint）供 agent 精确修复；`report.md` 与 `codespot show` 面向人类、codespot 品牌、密钥强制脱敏。

## 功能特性

- **增量扫描范围** —— `auto` / `uncommitted` / `unpushed` / `ref:<ref>` / `all`；发现不改变退出码，CI 可发布报告而不打断构建。
- **AI 语义审查（默认开启）** —— 每次扫描生成审查计划；agent 审查静态规则抓不到的问题（逻辑、并发、错误处理缺口、跨文件不一致），经 `codespot ai-scan absorb` 校验合并。
- **AI 修复闭环** —— 按严重级选择修复范围，agent 改码、重扫验证（≤3 轮）、汇总已修复/跳过/剩余；误报进白名单。
- **密钥检测** —— 常开层 222 条规则 + 报告脱敏 + "先轮换后清理"工作流；可选 TruffleHog 深度层（800+ 检测器，活体验证默认关闭）。
- **依赖漏洞（SCA）** —— OSV-Scanner 扫 requirements/锁文件/pom/go.mod，支持离线漏洞库（`codespot update-db`），每条发现附升级目标版本。
- **规则治理** —— 三层配置（原生工具配置 > `.codespot/config.json` 类别开关 > 内置默认）、severity 覆盖、单条误报白名单。
- **内建回归** —— `codespot selftest` 全引擎夹具自检；`codespot show` 按严重级/文件/CS 编号浏览发现。

## 为什么需要 codespot

AI 生成的代码需要的不止 AI 审查。纯模型扫描是非确定性的：底下没有规则目录、没有 CVE 数据库、没有密钥特征库——幻觉式保证与静默漏报与生俱来。codespot 把确定性引擎与 agent 语义配对：规则、CVE、密钥模式交给工具，模型只审查规则表达不了的东西。

传统扫描器也嵌不进这个循环。它们假设 CI 流水线和一个可连接的服务端；在本地 git 仓库里工作的 agent 无法按需调用它们，更没有一个能闭环"扫描→报告→修复→重扫"。codespot 就是为这个闭环而生的本地 CLI，自然语言即可驱动（"扫一下代码"）。

许可合规是从第一天起的设计约束。Sonar 系分析器已转向非开源的 SSALv1（限制把分析结果喂给非捆绑 AI），因此 codespot 组装干净许可的引擎（MIT/Apache/LGPL），运行时从官方源下载、绝不打包再分发。

## 快速开始：用 codespot 扫描一个仓库

### 1. 让 AI agent 安装

在 ZCode（或任何支持 `~/.agents/skills` 发现的 agent）里直接说：

> 安装 https://github.com/wenhao/codespot.git 中的 skill 并使用 codespot 扫描当前仓库

agent 会执行等价于：

```bash
git clone --depth 1 https://github.com/wenhao/codespot.git ~/.codespot/src/codespot
ln -s ~/.codespot/src/codespot/skill ~/.agents/skills/codespot   # 仅软链 skill 载荷
~/.agents/skills/codespot/scripts/codespot setup                  # 引擎安装（幂等）
```

### 2. 跑第一次扫描

自然语言触发（"扫一下代码"），或直接 CLI：

```bash
~/.agents/skills/codespot/scripts/codespot scan --scope auto
```

扫描同时生成 `.codespot/ai-plan.json`；agent 按计划审查、写 `ai-result.json`，然后合并：

```bash
~/.agents/skills/codespot/scripts/codespot ai-scan absorb
```

查看结果：

```bash
cat .codespot/report.md                                      # 人读报告，CS 编号
~/.agents/skills/codespot/scripts/codespot show --severity critical,major
```

随后 agent 呈现修复选项（仅严重 / 重要+ / 全部 / 先看详情）、修复代码、重扫验证并汇总。

### 3. 调规则、持续迭代

放一个原生配置（`.ruff.toml`、`.oxlintrc.json`、`.sqlfluff`、`.gitleaks.toml`）——codespot 将以它替代内置默认。或用类别开关：

```json
// .codespot/config.json
{
  "dialect": "postgres",
  "rules": {
    "python_lint": { "ignore": ["RUF100"] },
    "secrets_deep": { "enabled": true }
  }
}
```

### 更喜欢手动安装？

```bash
git clone https://github.com/wenhao/codespot.git && ln -s "$(pwd)/codespot/skill" ~/.agents/skills/codespot
```

升级：`git -C ~/.codespot/src/codespot pull` 后重跑 `setup`；卸载：删除软链与 `~/.codespot/`。

## 引擎矩阵

| 类别（配置键） | 引擎 | 运行要求 | 说明 |
|---|---|---|---|
| `secrets`（常开） | gitleaks 8.30 | — | `dir` 模式，报告脱敏 |
| `python_lint` | ruff 0.16 | — | JSON 输出保留修复建议 |
| `python_security` | bandit | python3（venv） | |
| `js_lint` | oxlint 1.85 | — | 快速层 |
| `js_lint`（深度） | ESLint + eslint-plugin-sonarjs | node/npm | 缺失时优雅降级为快速层 |
| `java` | PMD 7.27 | JRE 8+ | 源码级，无需编译 |
| `java`（深度，可选） | SpotBugs 4.10 + FindSecBugs 1.14 | mvn/gradle + JDK | 项目不可编译时自动跳过 |
| `sql` | SQLFluff | python3（venv） | 方言自动探测链 |
| `semantic` | Semgrep CE 1.177（py3.9 回退 1.136） | python3（venv） | Go/C#/Kotlin/Ruby/PHP/Rust/Terraform…；规则运行时从官方 registry 拉取 |
| `dependencies` | OSV-Scanner 2.6 | —（查询 osv.dev） | 离线库经 `codespot update-db` |
| `secrets_deep`（**opt-in**） | TruffleHog 3.97 | — | `--engine trufflehog`；默认 `--no-verification` |
| `ai_review`（**默认开启**） | AI agent 本身 | — | 计划 → 分析 → `ai-scan absorb`；`rules.ai_review.disabled` 可关 |

### 各语言规则数量与去重

数量为 codespot 实际启用数（2026-09-23 对本机引擎实测）。

| 语言 | 质量 / 规范 | 安全 | 依赖 |
|---|---|---|---|
| Python | ruff：**启用 503**（共 970） | ruff S 族 + bandit（32 插件） | OSV-Scanner |
| JavaScript / TypeScript | oxlint：**335** + sonarjs：**约 215** | 同左 + Semgrep | OSV-Scanner |
| Java | PMD：**213** | SpotBugs **约 470** + FindSecBugs **144**（CWE 标注） | OSV-Scanner |
| SQL | SQLFluff：**约 48**（共 68） | — | — |
| Go / C# / Kotlin / Ruby / PHP / Rust / Swift / Scala | — | Semgrep `auto` 规则包（**2800+**） | OSV-Scanner |
| 密钥（任意语言） | — | gitleaks **222**；TruffleHog 800+（opt-in） | — |

去重是设计使然：`eslint-plugin-oxlint` 关闭快速层已覆盖的全部 ESLint 规则；sonarjs 只贡献独有 Sonar 规则；PMD（源码）与 SpotBugs（字节码）互补；ruff-S 与 bandit-B 有意并存（语义不同、规则号独立）。

## CLI 一览

| 命令 | 说明 |
|---|---|
| `codespot setup [引擎…]` | 安装引擎（幂等、版本锁定；单引擎失败不阻塞其他） |
| `codespot scope --scope <档位>` | 打印扫描将使用的文件清单 |
| `codespot scan --scope <档位> [--engine 名称…]` | 运行匹配引擎 + 显式点名的 opt-in 引擎；写出双报告与 AI 审查计划 |
| `codespot show [--severity 级别] [--file 前缀] [--rule CS-编号] [--limit N] [--all]` | 浏览最近一次报告的问题详情 |
| `codespot ai-scan absorb` | 校验并合并 agent 写入的 AI 审查结果到最近报告 |
| `codespot update-db` | 下载/刷新本地 OSV 漏洞库（启用离线依赖扫描） |
| `codespot report` | 打印最近一次 report.json |
| `codespot selftest` | 夹具驱动的全引擎回归自检 |

## 配置

三层，优先级从高到低：

1. **原生配置文件** —— `.ruff.toml` / `ruff.toml` / pyproject 的 `[tool.ruff]`、`.oxlintrc.json`、`.sqlfluff`、`.gitleaks.toml`。存在即整体替代内置默认（参数能力完整）。
2. **`.codespot/config.json`** —— 类别开关（`disabled` / `ignore` / `enabled`）、SQL `dialect`、`semgrep_config`。类别：`secrets`、`python_lint`、`python_security`、`js_lint`、`java`、`sql`、`semantic`、`dependencies`、`secrets_deep`、`ai_review`。
3. **内置默认** —— 位于 `skill/assets/`。

### 排除（`.codespotignore`）

仓库根的 `.codespotignore` 文件可从所有扫描档位排除文件/目录，语法为 gitignore 子集——逐行一个模式、`#` 注释、尾 `/` 仅目录、含 `/` 的模式锚定仓库根（否则匹配任意层级）、`*` / `?` / `**` 通配、`!` 反选（后行胜出）：

```gitignore
# 生成物
*.log
dist/
docs/generated/**

# 保留这一个
!keep.log
```

内置排除始终生效且不可被 `!` 反选：`.git/`、`.codespot/`、`.codespotignore`、`node_modules/`、`vendor/`、`dist/`、`build/`、二进制文件。

严重级调整：`.codespot/severity-overrides.json`（`{"ruff": {"rules": {"RUF100": "info"}}}`）。单条误报：`.codespot/ignore`（`[{"tool": "ruff", "file": "src/app.py", "rule": "PLW0603"}]`）；密钥误报用 `.gitleaksignore` 指纹。

## 漏洞库与引擎更新

- **OSV-Scanner 离线优先**：有本地库（跑一次 `codespot update-db`，缓存于 `~/Library/Caches/osv-scalibr/` 或 `~/.cache/osv-scalibr/`）时依赖扫描完全离线；无库时实时查询 osv.dev。重跑 `update-db` 即刷新。
- **Semgrep 规则** 缓存于 `~/.semgrep/`；删缓存强制刷新，严格离线可把 `semgrep_config` 指向本地规则目录。
- **引擎升级**：改 `skill/scripts/engines/registry.json` 的 `version` 后重跑 `setup`；重置：`rm -rf ~/.codespot/engines/<name>-<version>`。

## 扩展：新增引擎

1. 编写 `skill/scripts/engines/engine_<name>.py`，实现适配器契约：`--workdir <根> --files <清单.json> --out <结果.json>`；成功退出 `0`（issue JSON 数组），失败退出 `2`（原因写 stderr）。
2. 输出统一 issue schema（`common.make_issue`）；severity 经 `rules-severity.json` 归一。
3. 在 `registry.json` 注册（安装形态、版本、语言、类别），并在 `skill/tests/fixtures/` + `expected.json` 添加夹具。

## 项目结构

```text
codespot/
├── skill/                        # 可安装 skill 载荷（软链此目录）
│   ├── SKILL.md                  # agent 工作流与触发
│   ├── scripts/
│   │   ├── codespot              # 主 CLI
│   │   ├── scope.py              # git 范围计算
│   │   ├── setup_engine.py       # 安装器（binary/zip/npm/venv/raw）
│   │   ├── rules-severity.json   # severity 映射
│   │   └── engines/              # 适配器 + registry.json
│   ├── assets/                   # 引擎默认配置
│   └── tests/fixtures/           # selftest 夹具与预期
├── docs/                         # 调研与报告（不属于 skill）
└── openspec/                     # 规格驱动变更历史（归档）
```

## 离线与平台说明

- 联网做一次 `setup` + `update-db` 后，除 Semgrep 外全部能力离线可用；Semgrep 需规则缓存或本地规则目录。
- Windows：除 Semgrep（需 WSL2/Docker）外可用，另需少量 registry/wrapper 适配；当前在 macOS/Linux 充分验证。

### 平台兼容性（Windows 支持现状）

| 维度 | 现状 |
|---|---|
| 主控 CLI / 报告 / scope | 兼容（纯 Python 标准库，路径统一正斜杠） |
| gitleaks / ruff / oxlint / OSV-Scanner | 官方有 Windows 二进制；registry 的 `os_map` 需补 `windows` 映射 |
| PMD / SpotBugs | 发行包跨平台；wrapper 需改用自带 `.bat` 启动器 |
| SQLFluff / bandit | 纯 Python venv，天然跨平台 |
| Semgrep CE | 不支持 Windows 原生（需 WSL2/Docker），`semantic` 类别不可用，其余不受影响 |
| 符号链接聚合 | 已有复制回退 |

正式支持 Windows 预计约一天（补平台映射、wrapper 改 .bat、修 `file:///C:/...` 解析）并需真机 selftest。

### 离线使用指南

**提前准备（联网做一次）**：① `codespot setup`（引擎本地化）；② `codespot update-db`（OSV 离线库）；③ 跑一次在线扫描预热 Semgrep 规则缓存。

| 引擎 | 离线状态 |
|---|---|
| gitleaks / ruff / oxlint / PMD / SpotBugs / SQLFluff / bandit / ESLint 深度层 | 完全离线 |
| OSV-Scanner | 有本地库时完全离线；无库时引擎失败并被隔离 |
| Semgrep | 有缓存通常可用；严格离线建议 `semgrep_config` 指向本地规则目录 |

任何引擎离线失败只进 `engine_errors`，不污染其他结果。

## 已知限制

- JS/TS 类型感知规则未开启（需 tsconfig）；SpotBugs 层需项目可编译（PMD 源码级仍覆盖）。
- Dockerfile（无扩展名）未被语言检测识别；可经 `semgrep_config` 覆盖。
- py3.9 机器上 SQLFluff 运行 3.x 旧线（4.x 需 python ≥3.10）。

## 许可

仅限内部使用。引擎运行时从官方源下载、绝不随工具打包分发；Semgrep CE registry 规则按 Semgrep Rules License "internal business purposes" 条款使用，TruffleHog 为 AGPL-3.0——请勿在启用这些引擎的状态下对外销售或分发 codespot。完整英文文档见 [README.md](README.md)。
