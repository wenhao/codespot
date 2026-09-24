<div align="center">

# codespot

**Local multi-engine static code scanning, built for AI coding agents.**

![engines](https://img.shields.io/badge/engines-10-blue)
![languages](https://img.shields.io/badge/languages-12%2B-green)
![runtime](https://img.shields.io/badge/runtime-python%20stdlib%20only-informational)
![offline](https://img.shields.io/badge/offline-ready%20(via%20update--db)-9cf)
![license](https://img.shields.io/badge/license-internal%20use-important)

English | [中文](README.zh.md)

📖 [Project Report](docs/project-report.html) · [Feasibility Research](docs/feasibility-research.md) · [Validation Report](docs/validation-report.html)

</div>

## Overview

- **A skill, not a server.** codespot runs entirely on your machine as an AI-agent skill: no SonarQube-style server, no accounts, no code leaves the repo. Any agent that discovers skills under `~/.agents/skills` can use it.
- **Ten engines, one report.** Secrets, Python quality & security, JS/TS, Java (source + bytecode), SQL, cross-language taint analysis, dependency CVEs — all normalized into one severity-ranked report with stable `CS-xxxxx` rule ids.
- **Incremental by default.** Scans what you changed (uncommitted → unpushed → full, automatic fallback), which fits the AI-coding loop of "generate, scan, fix, rescan".
- **Agent-first output.** `report.json` keeps full internals (tool / rule / ruleUrl / fixHint) for the agent to fix precisely; `report.md` and `codespot show` are human-facing, codespot-branded, with secrets always redacted.

## Features

- **Incremental scan scopes** — `auto` / `uncommitted` / `unpushed` / `ref:<ref>` / `all`; findings never change the exit code, so CI can publish reports without failing builds.
- **AI semantic review (on by default)** — every scan writes a review plan; the agent itself reviews what static rules can't catch (logic, concurrency, error-handling gaps, cross-file inconsistencies) and merges validated findings with `codespot ai-scan absorb`.
- **AI fix loop** — severity-filtered fix options, agent edits code, rescans to verify (≤3 rounds), summarizes fixed / skipped / remaining; false positives go to ignore lists.
- **Secrets detection** — 222-rule always-on layer with redacted reporting and a rotate-first workflow; optional TruffleHog deep layer (800+ detectors, liveness verification available but off by default).
- **Dependency vulnerabilities (SCA)** — OSV-Scanner against requirements/lockfiles/pom/go.mod, with an offline vulnerability DB (`codespot update-db`) and an upgrade target on every finding.
- **Rule governance** — three config layers (native tool configs > `.codespot/config.json` categories > built-in defaults), severity overrides, per-finding ignore lists.
- **Regression built in** — `codespot selftest` runs every engine against fixtures; `codespot show` browses findings by severity / file / CS id.

## Why codespot

AI-generated code needs more than AI review. Model-based scanning alone is non-deterministic: there is no rule catalog underneath, no CVE database, no secret signatures — hallucinated assurances and silent misses come with the territory. codespot pairs deterministic engines with the agent's semantics: rules, CVEs and secret patterns are checked by tools, and the model only reviews what rules cannot express.

Traditional scanners don't fit this loop either. They assume a CI pipeline and a server to talk to; an agent working locally in a git repo can't call them on demand, and none of them close the "scan → report → fix → rescan" cycle. codespot is a local CLI built for that cycle, driven by natural language ("scan my code").

License hygiene was a design constraint from day one. SonarSource analyzers moved to the non-open SSALv1 (which restricts feeding analyzer output to non-bundled AI), so codespot assembles clean-license engines (MIT / Apache / LGPL), downloads them at runtime from official sources, and never bundles or redistributes them.

## Quick Start: Scan a repo with codespot

### 1. Install via your AI agent

In ZCode (or any agent with `~/.agents/skills` discovery), just say:

> Install the skill from https://github.com/wenhao/codespot.git and scan this repo with codespot

The agent runs the equivalent of:

```bash
git clone --depth 1 https://github.com/wenhao/codespot.git ~/.codespot/src/codespot
ln -s ~/.codespot/src/codespot/skill ~/.agents/skills/codespot   # skill payload only
~/.agents/skills/codespot/scripts/codespot setup                  # engines, idempotent
```

### 2. Run your first scan

Trigger it in natural language ("scan my code"), or run the CLI:

```bash
~/.agents/skills/codespot/scripts/codespot scan --scope auto
```

The scan also writes `.codespot/ai-plan.json`; the agent reviews per the plan, writes `ai-result.json`, then merges:

```bash
~/.agents/skills/codespot/scripts/codespot ai-scan absorb
```

Read the results:

```bash
cat .codespot/report.md                                      # human-readable, CS ids
~/.agents/skills/codespot/scripts/codespot show --severity critical,major
```

The agent then presents fix options (critical / major+ / all / browse details), fixes the code, rescans to verify, and summarizes.

### 3. Tune rules and iterate

Drop a native config (`.ruff.toml`, `.oxlintrc.json`, `.sqlfluff`, `.gitleaks.toml`) — codespot uses it instead of its defaults. Or use category switches:

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

### Prefer manual install?

```bash
git clone https://github.com/wenhao/codespot.git && ln -s "$(pwd)/codespot/skill" ~/.agents/skills/codespot
```

Update with `git -C ~/.codespot/src/codespot pull` + re-run `setup`; uninstall by removing the symlink and `~/.codespot/`.

## Engine matrix

| Category (config key) | Engine | Requires | Notes |
|---|---|---|---|
| `secrets` (always on) | gitleaks 8.30 | — | `dir` mode, redacted reports |
| `python_lint` | ruff 0.16 | — | JSON output keeps fix suggestions |
| `python_security` | bandit | python3 (venv) | |
| `js_lint` | oxlint 1.85 | — | fast layer |
| `js_lint` (deep) | ESLint + eslint-plugin-sonarjs | node/npm | graceful fallback to fast layer |
| `java` | PMD 7.27 | JRE 8+ | source-level, no compile needed |
| `java` (deep, optional) | SpotBugs 4.10 + FindSecBugs 1.14 | mvn/gradle + JDK | skipped when project isn't buildable |
| `sql` | SQLFluff | python3 (venv) | dialect auto-detection chain |
| `semantic` | Semgrep CE 1.177 (1.136 on py3.9) | python3 (venv) | Go/C#/Kotlin/Ruby/PHP/Rust/Terraform…; rules fetched from the official registry |
| `dependencies` | OSV-Scanner 2.6 | — (queries osv.dev) | offline DB via `codespot update-db` |
| `secrets_deep` (**opt-in**) | TruffleHog 3.97 | — | `--engine trufflehog`; `--no-verification` by default |
| `ai_review` (**on by default**) | the AI agent itself | — | plan → analyze → `ai-scan absorb`; disable via `rules.ai_review.disabled` |

### Rules per language — counts & de-duplication

Counts are what codespot actually enables (verified against installed engines, 2026-09-23).

| Language | Quality / style | Security | Dependency |
|---|---|---|---|
| Python | ruff: **503 enabled** (of 970) | ruff S-family + bandit (32 plugins) | OSV-Scanner |
| JavaScript / TypeScript | oxlint: **335** + sonarjs: **~215** | same + Semgrep | OSV-Scanner |
| Java | PMD: **213** | SpotBugs **~470** + FindSecBugs **144** (CWE-tagged) | OSV-Scanner |
| SQL | SQLFluff: **~48** (of 68) | — | — |
| Go / C# / Kotlin / Ruby / PHP / Rust / Swift / Scala | — | Semgrep `auto` packs (**2800+**) | OSV-Scanner |
| Secrets (any language) | — | gitleaks **222**; TruffleHog 800+ (opt-in) | — |

De-duplication is by design: `eslint-plugin-oxlint` disables every ESLint rule the oxlint layer already owns; sonarjs contributes only unique Sonar rules; PMD (source) and SpotBugs (bytecode) are complementary layers; ruff-S and bandit-B intentionally coexist (different semantics, distinct rule ids).

## CLI Overview

| Command | Description |
|---|---|
| `codespot setup [engines…]` | Install engines (idempotent, version-locked; per-engine failures don't block others) |
| `codespot scope --scope <tier>` | Print the file list a scan would use |
| `codespot scan --scope <tier> [--engine name…]` | Run matching engines + any requested opt-in engines; writes both reports and the AI review plan |
| `codespot show [--severity s1,s2] [--file prefix] [--rule CS-xxxxx] [--limit N] [--all]` | Browse issue details from the last report |
| `codespot ai-scan absorb` | Validate & merge agent-written AI review results into the last report |
| `codespot update-db` | Download/refresh the local OSV vulnerability DB (enables offline dependency scans) |
| `codespot report` | Print the last report.json |
| `codespot selftest` | Fixture-based regression across all engines |

## Configuration

Three layers, highest priority first:

1. **Native config files** — `.ruff.toml` / `ruff.toml` / `[tool.ruff]` in pyproject, `.oxlintrc.json`, `.sqlfluff`, `.gitleaks.toml`. When present, codespot uses them instead of its built-in defaults (full parameter power).
2. **`.codespot/config.json`** — category switches (`disabled` / `ignore` / `enabled`), SQL `dialect`, `semgrep_config`. Categories: `secrets`, `python_lint`, `python_security`, `js_lint`, `java`, `sql`, `semantic`, `dependencies`, `secrets_deep`, `ai_review`.
3. **Built-in defaults** in `skill/assets/`.

### Exclusions (`.codespotignore`)

A `.codespotignore` file at the repo root excludes files/folders from every scan scope, using gitignore-subset syntax — one pattern per line, `#` comments, trailing `/` for directories only, patterns containing `/` anchored to the repo root (otherwise matching at any depth), `*` / `?` / `**` wildcards, and `!` negation where the last matching pattern wins:

```gitignore
# generated artifacts
*.log
dist/
docs/generated/**

# keep this one
!keep.log
```

Built-in excludes always apply and cannot be re-included with `!`: `.git/`, `.codespot/`, `.codespotignore`, `node_modules/`, `vendor/`, `dist/`, `build/`, binary files.

Severity tuning: `.codespot/severity-overrides.json` (`{"ruff": {"rules": {"RUF100": "info"}}}`). One-off false positives: `.codespot/ignore` (`[{"tool": "ruff", "file": "src/app.py", "rule": "PLW0603"}]`); secrets use `.gitleaksignore` fingerprints.

## Vulnerability DB & engine updates

- **OSV-Scanner is offline-first**: with a local DB (run `codespot update-db` once, cached under `~/Library/Caches/osv-scalibr/` or `~/.cache/osv-scalibr/`) dependency scans run fully offline; without one they query osv.dev live. Re-run `update-db` to refresh.
- **Semgrep rules** cache under `~/.semgrep/`; delete the cache to force a refresh, or point `semgrep_config` at a local rules dir for strict-offline setups.
- **Engine upgrades**: bump the `version` field in `skill/scripts/engines/registry.json` and re-run `setup`; reset an engine with `rm -rf ~/.codespot/engines/<name>-<version>`.

## Extending: adding an engine

1. Write `skill/scripts/engines/engine_<name>.py` implementing the adapter contract: `--workdir <root> --files <list.json> --out <result.json>`; exit `0` with a JSON array of issues, `2` with the failure reason on stderr.
2. Emit the unified issue schema (`common.make_issue`); severity normalizes via `rules-severity.json`.
3. Register it in `registry.json` (install form, version, languages, category) and add fixtures to `skill/tests/fixtures/` + `expected.json`.

## Project Structure

```text
codespot/
├── skill/                        # installable skill payload (symlink this)
│   ├── SKILL.md                  # agent workflow & triggers
│   ├── scripts/
│   │   ├── codespot              # main CLI
│   │   ├── scope.py              # git scope calculation
│   │   ├── setup_engine.py       # installer (binary/zip/npm/venv/raw)
│   │   ├── rules-severity.json   # severity mapping
│   │   └── engines/              # adapters + registry.json
│   ├── assets/                   # default engine configs
│   └── tests/fixtures/           # selftest fixtures + expectations
├── docs/                         # research & reports (not part of the skill)
└── openspec/                     # spec-driven change history (archived)
```

## Offline & platform notes

- After `setup` + `update-db` (once, online), everything except Semgrep works fully offline; Semgrep needs its rule cache or a local rules dir.
- Windows: works except Semgrep (WSL2/Docker) plus small registry/wrapper additions; validated on macOS/Linux. Details in the [Chinese README](README.zh.md).

## Known limitations

- Type-aware JS/TS rules are off (need tsconfig); SpotBugs layer needs a buildable project (PMD still covers source-level).
- Dockerfile (no extension) isn't language-detected; cover via `semgrep_config`.
- SQLFluff on py3.9 machines runs the 3.x line (4.x needs python ≥ 3.10).

## License

Internal use only. Engines are downloaded at runtime from official sources and never bundled; Semgrep CE registry rules are used under the Semgrep Rules License "internal business purposes" terms, and TruffleHog is AGPL-3.0 — do not sell or externally distribute codespot with these engines enabled. See [README.zh.md](README.zh.md) for the full Chinese documentation.
