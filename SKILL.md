---
name: codespot
description: Local static code scanning for AI-generated code. Use whenever the user asks to scan, lint, or statically check code, find bugs, secrets leaks, or security issues in their working tree — including phrases like "扫一下代码", "检查一下刚生成的代码", "静态检查", "扫扫这个 Java 文件", "检查 JS 代码", "检查 SQL 规范", "有没有密钥泄漏" — even when they don't name codespot.
---

# codespot

本地多引擎静态扫描 + AI 修复循环。对 git 范围内（未提交 / 未推送 / 全量）的代码运行 gitleaks（密钥）、ruff（Python 质量）、bandit（Python 安全）、oxlint + ESLint/sonarjs（JS/TS）、PMD + SpotBugs/FindSecBugs（Java，后者需项目可编译）、SQLFluff（SQL），产出 AI 可读的 `.codespot/report.json` 与人读的 `report.md`。

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
   `--scope`：`auto`（默认）/ `uncommitted` / `unpushed` / `ref:<ref>` / `all`。
3. **读报告**：读 `.codespot/report.json`。`engine_errors` 非空时如实说明哪些引擎失败，不要假装扫描完整。
4. **呈现 + 修复选项**：用中文摘要（各严重级数量、最关键的几条），**必须**用 AskUserQuestion 呈现：
   - 仅修复 🔴 严重（critical）
   - 修复 🟠 重要及以上（major+）
   - 全部修复
   - 仅查看报告，不修复
5. **修复循环**（用户选择修复时，按选定范围执行）：
   - 逐条处理 issue，**修复前先判断合理性**：疑似误报（测试代码、示例占位符、有意为之）→ 跳过并记录原因；
   - 按文件分组编辑修复；密钥类发现**永远提醒用户轮换密钥**（历史中已提交的密钥视为已泄漏），而非仅删行；
   - 每轮修复后重跑 `codespot scan`（同 scope）验证；**最多 3 轮**；
   - 确认的误报登记：普通工具写入 `.codespot/ignore`（`[{"tool":"ruff","file":"...","rule":"..."}]`），gitleaks 用其 fingerprint 写 `.gitleaksignore`；重扫确认不再出现；
   - 收敛后给出汇总：**已修复 N 条 / 跳过 M 条（含原因）/ 剩余 K 条**。
6. **收尾**：提醒将 `.codespot/` 加入项目 `.gitignore`。**不要**自动 commit。

## 规则与边界

- 引擎失败（exit 2 / engine_errors）：报告原因与 setup 命令，不要静默降级为"没有问题"。
- JS/TS 深度层（sonarjs）依赖 node/npm，缺失时仅有 oxlint 快速层覆盖——摘要中说明覆盖面。
- 不要执行任何"自动改写"脚本；修复由你（agent）直接编辑代码完成。
- 跳过修复的 issue 必须逐条给出理由，不允许无解释跳过。
- `codespot selftest` 可在怀疑引擎损坏时做回归自检。
