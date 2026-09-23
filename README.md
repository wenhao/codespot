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
cat .codespot/report.json   # for AI agents
cat .codespot/report.md     # human-readable summary

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

Severity can be tuned per project via `.codespot/severity-overrides.json` (per-rule and per-tool defaults); SQL dialect goes in `.codespot/config.json` (`{"dialect": "postgres"}`).

## Documentation
- [可行性调研报告](docs/feasibility-research.md) — 技术选型、引擎矩阵、路线对比、实现设计与并行迭代计划（2026-09-23，两轮调研）
- 实施按 OpenSpec 变更分批推进：`openspec/changes/`（当前：`add-scan-base-with-secrets-and-python`，M0 基座 + gitleaks + ruff）
