# codespot
code static analysis tool

AI agent skill for local static code scanning: detect changed files via git (uncommitted / unpushed / full), run pluggable scan engines per language, and produce machine-readable reports that drive an AI-assisted fix loop.

## Quick start

```bash
# 1. Install engines (idempotent; gitleaks + ruff in M0)
scripts/codespot setup

# 2. Scan (in any git repo; scope auto = uncommitted → unpushed → all)
scripts/codespot scan --scope auto

# 3. Read the reports
cat .codespot/report.json   # for AI agents (internal fields + csId)
cat .codespot/report.md     # human-readable, codespot-branded (CS-xxxxx ids)
scripts/codespot show --severity critical,major   # browse issue details

# Regression check
scripts/codespot selftest
```

Engines are downloaded into `~/.codespot/engines/` (version-locked); reports land in the target repo's `.codespot/` (add it to your `.gitignore`).

## Engine matrix (M0 + M1)

| Dimension | Engine | Requires |
|---|---|---|
| Secrets (always on) | gitleaks 8.30 | — |
| Python quality | ruff 0.16 | — |
| Python security | bandit | python3 (venv-isolated) |
| JS/TS fast layer | oxlint 1.85 | — |
| JS/TS deep layer | ESLint + eslint-plugin-sonarjs | node/npm (graceful fallback to fast layer) |
| Java (source-level, no compile) | PMD 7.27 | JRE 8+ |
| Java bytecode + security (optional layer) | SpotBugs 4.10 + FindSecBugs 1.14 | mvn/gradle + JDK (skipped when project isn't buildable) |
| SQL conventions | SQLFluff | python3 (venv-isolated) |
| Cross-language semantic/taint (Go, C#, Kotlin, Ruby, PHP, Rust, Terraform…) | Semgrep CE 1.177 (fallback 1.136 on py3.9) | python3 (venv); first run fetches rules from the official registry |
| Dependency vulnerabilities (supply chain) | OSV-Scanner 2.6 | — (queries osv.dev; needs network) |

Severity can be tuned per project via `.codespot/severity-overrides.json` (per-rule and per-tool defaults); SQL dialect and a custom semgrep ruleset go in `.codespot/config.json` (`{"dialect": "postgres", "semgrep_config": "p/gosec"}`).

### Branding & rule configuration

- Human-facing output (report.md, `codespot show`) carries only codespot branding: rules get stable `CS-xxxxx` ids derived from the underlying rule. `report.json` (the agent-facing interface) additionally keeps the original tool/rule/ruleUrl fields for fix work.
- Disable whole check categories or drop specific rules via `.codespot/config.json`:
  ```json
  {"rules": {
    "python_security": {"disabled": true},
    "python_lint": {"ignore": ["RUF100"]}
  }}
  ```
  Categories: `secrets`, `python_lint`, `python_security`, `js_lint`, `java`, `sql`, `semantic`.
- Power users: project-native config files win over codespot defaults — `.ruff.toml`/`ruff.toml`/`[tool.ruff]` in pyproject, `.oxlintrc.json`, `.sqlfluff`, `.gitleaks.toml` are picked up automatically.

**License boundary**: codespot is an internal tool. Semgrep CE and its registry rules are used under the Semgrep Rules License "internal business purposes" only — rules are fetched at runtime on the user's machine and are not bundled with or distributed by codespot. Do not sell or externally distribute codespot with this engine enabled.

## Documentation
- [可行性调研报告](docs/feasibility-research.md) — 技术选型、引擎矩阵、路线对比、实现设计与并行迭代计划（2026-09-23，两轮调研）
- 实施按 OpenSpec 变更分批推进：`openspec/changes/archive/`（M0 基座 + 密钥/Python、M1 JS/TS + Java PMD + 修复循环、M2 bandit + SQLFluff + SpotBugs 层均已交付；实验性 M3/M4 已取消，项目定稿于 M2）
