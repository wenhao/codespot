# Proposal

## Why

codespot 定位为"AI agent 的本地静态扫描 skill"，但目前仓库只有调研报告，没有任何可运行实现。需要先落地**最小端到端闭环**（扫描 → 统一报告 → AI 可读），为后续按语言扩展引擎建立基座与适配器契约。本变更对应调研报告（docs/feasibility-research.md 第 6 章）的里程碑 **M0**，选用两个 P0 引擎：gitleaks（密钥，跨语言常开、价值最高、工作量极低）与 ruff（Python 质量，JSON 带 fix 建议、秒级）。

## What Changes

- 新增 skill 骨架：`SKILL.md`（触发词 + 工作流编排指令）。
- 新增主控 CLI `scripts/codespot`（Python 3 标准库），子命令：`setup` / `scope` / `scan` / `report` / `selftest`。
- 新增 git 范围计算 `scripts/scope.py`：`uncommitted`（默认，含未跟踪文件）/ `unpushed`（无上游时回退 main）/ `ref:<ref>` / `all` 四档。
- 新增引擎注册表 `scripts/engines/registry.json` 与适配器契约（统一输入 `--workdir --files --out`，统一 issue JSON 输出，退出码 0=运行成功 / 2=引擎失败）。
- 新增两个引擎适配器：`engine_secrets.py`（gitleaks `dir` 模式 + 报告脱敏 + `.gitleaksignore` 通道）与 `engine_py.py`（ruff，JSON 输出含 fix 字段）。
- 新增 setup 幂等安装：gitleaks（单二进制，版本锁定）与 ruff（单二进制，版本锁定），安装到 `~/.codespot/engines/<name>-<version>/`。
- 新增 severity 归一化（`scripts/rules-severity.json`）与双报告输出：`.codespot/report.json`（agent 读）+ `.codespot/report.md`（人读摘要，按严重级分组）。
- 新增测试夹具 `tests/fixtures/`：密钥泄漏样例 + Python 问题代码样例及预期发现清单，`codespot selftest` 回归验证。
- 本批**不包含**：修复循环编排（SKILL.md 中仅保留"呈现报告与选项"的最小指令）、JS/TS、Java、SQL 引擎、SpotBugs —— 后续批次追加。

## Capabilities

### New Capabilities
- `scan-orchestration`: 主控 CLI 与扫描编排——setup/scope/scan/report 子命令、引擎注册表、适配器调用契约、并行调度与失败隔离。
- `scan-scope`: git 增量范围计算——uncommitted/unpushed/ref/all 四档、文件清单与语言检测。
- `engine-contract`: 引擎适配器统一契约——输入参数、统一 issue JSON schema、退出码语义、severity 归一化。
- `secrets-engine`: gitleaks 适配——dir 模式扫描、报告脱敏、误报 ignore 通道。
- `python-engine`: ruff 适配——质量扫描、fix 建议透传、规则映射。
- `reporting`: 双报告——report.json（机器）与 report.md（人类）的格式与内容要求。
- `skill-workflow`: SKILL.md 触发与编排指令——何时扫描、如何呈现报告与修复选项（本批仅到"呈现"为止）。

### Modified Capabilities

（无——项目尚无既有 spec。）

## Impact

- 新增代码全部在 `scripts/`、`assets/`、`tests/fixtures/`、`SKILL.md`；不改任何既有文件（除 README 补一行使用说明）。
- 运行时依赖：Python 3.8+（主控，仅标准库）；引擎按需下载 gitleaks 与 ruff 单二进制到 `~/.codespot/`，不污染项目与系统环境。
- 产出物：`.codespot/report.json`、`.codespot/report.md`（建议加入用户项目的 .gitignore，由 skill 在首次扫描时提示）。
- 后续批次（JS/TS、Java、SQL、修复循环）直接复用本批的注册表与契约，无需改动基座设计。
