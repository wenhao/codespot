---
name: codespot
description: Local static code scanning for AI-generated code. Use whenever the user asks to scan, lint, or statically check code, find bugs, secrets leaks, or security issues in their working tree — including phrases like "扫一下代码", "检查一下刚生成的代码", "静态检查", "有没有密钥泄漏" — even when they don't name codespot.
---

# codespot

本地多引擎静态扫描：对 git 范围内（未提交 / 未推送 / 全量）的代码运行 gitleaks（密钥）与 ruff（Python 质量）等引擎，产出 AI 可读的 `.codespot/report.json` 与人读的 `report.md`。

## 工作流

1. **前置检查**：目标目录必须是 git 仓库。引擎二进制装在 `~/.codespot/engines/`；未安装时先运行 setup（幂等，失败会提示）：
   ```bash
   <skill目录>/scripts/codespot setup
   ```
2. **扫描**（在用户项目根目录）：
   ```bash
   <skill目录>/scripts/codespot scan --scope auto
   ```
   `--scope` 取值：`auto`（默认：uncommitted → unpushed → all 依次取第一个非空）/ `uncommitted` / `unpushed` / `ref:<ref>` / `all`。
3. **读报告**：读 `.codespot/report.json`（结构化 issues，按 severity 排序）。`engine_errors` 非空时如实告知用户哪些引擎失败，不要假装扫描完整。
4. **呈现**：用中文向用户摘要（各严重级数量、最关键的几条），然后**必须**用 AskUserQuestion 呈现修复选项：
   - 仅修复 🔴 严重（critical）
   - 修复 🟠 重要及以上（major+）
   - 全部修复
   - 仅查看报告，不修复
5. **修复**（用户选择修复时）：按文件分组逐条判断 issue 合理性（可能是误报）→ 编辑代码修复 → 修复完成后对改动文件重跑 `codespot scan` 验证。最多 3 轮，向用户汇总剩余问题。
6. **收尾**：提醒用户将 `.codespot/` 加入其项目 `.gitignore`（报告是本地产物）。**不要**自动 commit。

## 规则与边界

- **本版本不含自动修复循环**：第 5 步由你（agent）直接编辑代码完成；不要执行任何"自动改写"脚本。
- 密钥类（gitleaks）发现**永远先提醒用户轮换密钥**，而不是仅仅"删除该行"——已提交历史中的密钥应视为已泄漏。
- 修复前判断合理性：对疑似误报（如测试代码中的 assert、示例占位符），跳过并向用户说明，或建议加入 `.codespot/ignore`（格式 `[{"tool":"ruff","file":"...","rule":"..."}]`）与 `.gitleaksignore`。
- 引擎失败（exit 2 / engine_errors）：报告失败原因与 setup 命令，不要静默降级为"没有问题"。
- `codespot selftest` 可在怀疑引擎安装损坏时做回归自检。
