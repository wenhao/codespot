---
name: codespot
description: Local static code scanning for AI-generated code. Use whenever the user asks to scan, lint, or statically check code, find bugs, secrets leaks, or security issues in their working tree — including phrases like "扫一下代码", "检查一下刚生成的代码", "静态检查", "扫扫这个 Java 文件", "检查 JS 代码", "检查 SQL 规范", "有没有密钥泄漏", "依赖有没有漏洞" — even when they don't name codespot.
---

# codespot

本地多引擎静态扫描 + AI 修复循环。对 git 范围内（未提交 / 未推送 / 全量）的代码运行 gitleaks（密钥）、ruff（Python 质量）、bandit（Python 安全）、oxlint + ESLint/sonarjs（JS/TS）、PMD + SpotBugs/FindSecBugs（Java，后者需项目可编译）、SQLFluff（SQL）、Semgrep CE（跨语言语义/taint：Go、C#、Kotlin、Ruby、PHP、Rust、Terraform 等；规则从官方 registry 运行时拉取，首次扫描需联网）、OSV-Scanner（依赖漏洞/供应链：查 requirements、package-lock、pom.xml、go.mod 等清单里的已知 CVE，需联网）、TruffleHog（可选深度密钥检测，800+ 检测器，仅在用户 `--engine trufflehog` 显式指定时运行）、AI 深度审查（可选，`--engine ai` 由你按计划执行语义级审查），产出 AI 可读的 `.codespot/report.json` 与人读的 `report.md`。

## 工作流

1. **前置检查**：目标目录必须是 git 仓库。引擎装在 `~/.codespot/engines/`；未安装时先运行 setup（幂等）：
   ```bash
   <skill目录>/scripts/codespot setup
   ```
   个别引擎安装失败（如无 npm / 无 JRE）不影响其余引擎；对应语言将缺少覆盖，需如实告知用户。
2. **扫描**（在用户项目根目录）：
   ```bash
   <skill目录>/scripts/codespot scan --scope auto
   ```
   `--scope`：`auto`（默认）/ `uncommitted` / `unpushed` / `ref:<ref>`（评审特定基线以来的改动）/ `all`。
3. **读报告**：读 `.codespot/report.json`。`engine_errors` 非空时如实说明哪些引擎失败，不要假装扫描完整。
4. **AI 语义审查**（增量档位默认开启：uncommitted / unpushed / ref 自动包含；全量扫描（scope=all，含 auto 降级）默认跳过并向用户转述 CLI 提示——"全量扫描已跳过 AI 审查，如需开启可 `--engine ai` 重跑或在 config 设 `rules.ai_review.enabled`"。另两种跳过情形：用户明确说"只扫不审"；config 已关闭 ai_review。未跳过时按 4a~4e 执行）：
   - **4a 准备**：扫描已自动产出 `.codespot/ai-plan.json`（目标文件、输出 schema、审查重点、超限分批指引）；单独补跑用 `codespot scan --engine ai`。同时按当前 scope 的基线解析 `git diff --unified=0`，建立每个目标文件的**变更行区间清单**（uncommitted → 对 HEAD；unpushed → 对 upstream 跟踪分支；ref → 对该 ref）。行号核对与告警筛选都以这份清单为准。
   - **4b 独立评审**：逐 hunk 覆盖全部变更区间，先通读改动及其所属方法/调用链，形成自己的缺陷判断。**不要以 plan 为分析起点**——先读 plan 会先入为主、抑制独立发现。检查清单：
     - 空值/解引用：可空返回值、自动拆箱、Map.get 结果、Optional 误用；
     - 异常路径：吞异常、中断标志未恢复、错误上下文丢失；
     - 边界条件：off-by-one、空/零/NaN、漏分支、区间端点；
     - 并发：共享状态无同步、检查后执行、死锁风险；
     - 资源泄漏：流/连接/句柄未关闭；
     - 日志滥用：热路径 debug、敏感信息入日志；
     - 跨文件契约（必做）：对每个改动的公共方法，用 grep 找 1~2 个调用点核对新签名/新语义是否破坏调用方；
     - 配置默认值自洽、文档与行为一致；
     - 死代码残留：unused imports、未用变量。
     - 其他性能/安全/可维护性等问题。
   - **4c 对照 plan 补充**：现在才读 ai-plan.json 交叉核对。plan 中指向**缺陷类**问题（空值/异常/泄漏/并发/边界/逻辑/安全）而自己未发现的，且位置落在该文件变更行区间 ±10 行内 → 核实后补入自己的结果；与自己已有发现按「同文件且行号相差 ≤3」判重。plan 中复杂度、风格、文档类告警不采纳。（注意：这是筛选你写入 ai-result.json 的内容；report.json 中静态引擎的原始告警不受此影响。）
   - **4d 写结果并合并**：每条发现按 schema 写 `.codespot/ai-result.json`（无发现写 `[]`）：
     - `file:line` **锚定在问题可见的那一行**（解引用发生的行、缺 break 的 case 行、日志语句行）——写之前重读该行，确认与描述一致；禁止用方法签名行或代码块首行顶替；
     - `severity` 按实际影响给单一级别：数据错误/安全/崩溃=critical，功能缺陷=major，改进建议=minor；
     - `confidence` 必填，不确定用 low；
     - `message` 给出依据（为什么是问题），`snippet` 摘问题行。
     完成后执行 `codespot ai-scan absorb` 合并。合并报告中 AI 发现标注为**建议性**（advisory）并附 confidence；修复建议同样先判断合理性。
   - **4e 补漏复查**（absorb 前的最后一道）：列出零发现的文件与 hunk，快速复查一遍（零发现可能属实，也可能是漏看）；多文件改动的 diff 只报出 1~2 条通常意味着覆盖不足；plan 中被静态引擎密集标记而你零产出的文件优先复查。
   **absorb 完成后**才进入第 5 步呈现（基于合并后报告）。
5. **呈现 + 修复选项**：用中文摘要（各严重级数量、最关键的几条），**必须**用 AskUserQuestion 呈现：
   - 先查看问题详情（用 `codespot show` 按严重级/文件分批呈现，看完回到本选项）
   - （报告含密钥发现时可提示）启用深度密钥检测：`codespot scan --engine trufflehog`——800+ 检测器；默认 `--no-verification` 纯本地检测，不联网验证密钥是否存活
   - 仅修复 🔴 严重（critical）
   - 修复 🟠 重要及以上（major+）
   - 全部修复
   - 仅查看报告，不修复
6. **修复循环**（用户选择修复时，按选定范围执行）：
   - 逐条处理 issue，**修复前先判断合理性**：疑似误报（测试代码、示例占位符、有意为之）→ 跳过并记录原因；
   - 按文件分组编辑修复；密钥类发现**永远提醒用户轮换密钥**（历史中已提交的密钥视为已泄漏），而非仅删行；
   - 每轮修复后重跑 `codespot scan`（同 scope）验证；**最多 3 轮**；
   - 确认的误报登记：普通问题写入 `.codespot/ignore`（`[{"tool":"...","file":"...","rule":"..."}]`，键名用 report.json 的原始字段值），密钥类用其 fingerprint 写 `.gitleaksignore`；重扫确认不再出现；
   - 收敛后给出汇总：**已修复 N 条 / 跳过 M 条（含原因）/ 剩余 K 条**。
7. **收尾**：提醒将 `.codespot/` 加入项目 `.gitignore`。**不要**自动 commit。

## 品牌与呈现边界

- **对用户呈现时只说 codespot**：问题编号一律用 `CS-xxxxx`（report.md / `codespot show` 输出的编号），不要向用户提及任何底层开源工具名。
- `report.json` 是给 agent 的内部接口，保留原始字段（tool/rule/ruleUrl）供你修复时使用——内部决策可用，转述给用户时必须 codespot 化。
- 排除文件/目录：引导用户写仓库根 `.codespotignore`（gitignore 子集语法：`*.log`、`generated/`、`!keep.log` 后行胜出；内置排除不可反选）。规则删减/调参：引导用户写 `.codespot/config.json`（`rules` 段按检查类别：python_lint / python_security / js_lint / java / sql / secrets / semantic，支持 `disabled` 与 `ignore`）；高级用户可直接放原生配置文件（`.ruff.toml`、`.oxlintrc.json`、`.sqlfluff` 等），原生优先。

## 规则与边界

- 引擎失败（exit 2 / engine_errors）：报告原因与 setup 命令，不要静默降级为"没有问题"。
- JS/TS 深度层（sonarjs）依赖 node/npm，缺失时仅有 oxlint 快速层覆盖——摘要中说明覆盖面。
- 不要执行任何"自动改写"脚本；修复由你（agent）直接编辑代码完成。
- 跳过修复的 issue 必须逐条给出理由，不允许无解释跳过。
- `codespot selftest` 可在怀疑引擎损坏时做回归自检。
