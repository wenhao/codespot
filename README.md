# codespot
code static analysis tool

AI agent skill for local static code scanning: detect changed files via git (uncommitted / unpushed / full), run pluggable scan engines per language, and produce machine-readable reports that drive an AI-assisted fix loop.

- **8 check dimensions** (see [engine matrix](#engine-matrix)): secrets, Python quality & security, JS/TS, Java (source + bytecode), SQL, dependency vulnerabilities, cross-language semantic/taint.
- **Incremental by default**: scans what you changed (uncommitted → unpushed → all, automatic fallback).
- **Agent-friendly**: `.codespot/report.json` keeps full internals for the AI; `.codespot/report.md` is a human-readable, codespot-branded summary with stable `CS-xxxxx` rule ids.
- **License note**: internal tool. Semgrep CE registry rules are used under "internal business purposes" only — see [License boundary](#license-boundary).

## Quick start

**Install as a skill** (everything the user needs lives in `skill/`; docs & openspec stay out of the way):

```bash
ln -s <repo>/skill ~/.agents/skills/codespot
```

```bash
# 1. Install engines (idempotent; installs only what your project needs)
~/.agents/skills/codespot/scripts/codespot setup

# 2. Scan (in any git repo; scope auto = uncommitted → unpushed → all)
~/.agents/skills/codespot/scripts/codespot scan --scope auto

# 3. Read the reports
cat .codespot/report.md     # human-readable, codespot-branded (CS-xxxxx ids)
cat .codespot/report.json   # agent-facing: internals (tool/rule/ruleUrl) + csId
~/.agents/skills/codespot/scripts/codespot show --severity critical,major
~/.agents/skills/codespot/scripts/codespot show --rule CS-5ebd4

# Regression check (fixture-based, all engines)
~/.agents/skills/codespot/scripts/codespot selftest
```

Engines are downloaded into `~/.codespot/engines/` (version-locked); reports land in the target repo's `.codespot/` — add `.codespot/` to your project's `.gitignore`.

## CLI reference

| Command | Purpose |
|---|---|
| `codespot setup [engines…]` | Install engines (idempotent, version-locked; per-engine failures don't block others) |
| `codespot scope --scope <tier>` | Print the file list a scan would use |
| `codespot scan --scope <tier> [--engine name…]` | Run all matching engines (plus any explicitly requested opt-in engines), write both reports |
| `codespot show [--severity s1,s2] [--file prefix] [--rule CS-xxxxx] [--limit N] [--all]` | Browse issue details from the last report |
| `codespot report` | Print the last report.json |
| `codespot selftest` | Fixture-based regression across all engines |

**Opt-in engines**: registry entries marked `opt_in` (currently TruffleHog) never run by default — request them with a repeatable `--engine <name>` flag, or enable permanently via `.codespot/config.json`: `{"rules": {"secrets_deep": {"enabled": true}}}`.

**Scan scopes** (`--scope`): `auto` (default: first non-empty of uncommitted → unpushed → all), `uncommitted` (includes untracked), `unpushed` (falls back to `main` if no upstream), `ref:<ref>`, `all`.

**Exit codes** (scan/setup): `0` = completed (findings don't change this — the agent decides what to do with the report); `2` = orchestration/setup failure. CI tip: scan always exits 0 when the run itself succeeded, so a pipeline step can publish reports without failing the build.

## Engine matrix

| Category (config key) | Engine | Requires | Notes |
|---|---|---|---|
| `secrets` (always on) | gitleaks 8.30 | — | `dir` mode, reports are redacted |
| `python_lint` | ruff 0.16 | — | JSON output keeps fix suggestions |
| `python_security` | bandit | python3 (venv-isolated) | |
| `js_lint` | oxlint 1.85 | — | fast layer |
| `js_lint` (deep) | ESLint + eslint-plugin-sonarjs | node/npm | graceful fallback to fast layer |
| `java` | PMD 7.27 | JRE 8+ | source-level, no compile needed |
| `java` (deep, optional) | SpotBugs 4.10 + FindSecBugs 1.14 | mvn/gradle + JDK | skipped when project isn't buildable |
| `sql` | SQLFluff | python3 (venv-isolated) | dialect auto-detection chain |
| `semantic` | Semgrep CE 1.177 (fallback 1.136 on py3.9) | python3 (venv) | Go/C#/Kotlin/Ruby/PHP/Rust/Terraform…; rules fetched from official registry |
| `dependencies` | OSV-Scanner 2.6 | — (queries osv.dev) | scans requirements/lockfiles/pom/go.mod for known CVEs |
| `secrets_deep` (**opt-in**) | TruffleHog 3.97 | — | 800+ detectors; `--no-verification` by default (fully local); runs only via `--engine trufflehog` or `rules.secrets_deep.enabled` |
| `ai_review` (**opt-in**, agent-driven) | the AI agent itself | — | semantic review (logic/concurrency/error-handling gaps); `scan --engine ai` → analyze per `.codespot/ai-plan.json` → `codespot ai-scan absorb`; findings are advisory with confidence |

### Rules per language — counts & de-duplication

Rule counts below are what codespot actually enables (verified against the installed engines, 2026-09-23), not the tools' full catalogs.

| Language | Quality / style | Security | Dependency & supply chain |
|---|---|---|---|
| Python | ruff: **503 enabled** (of 970 defined; E/W/F/PL/B/RUF families, style noise excluded) | ruff S-family + bandit (32 plugins, B1xx–B7xx) | OSV-Scanner (osv.dev advisories) |
| JavaScript / TypeScript | oxlint: **335 enabled** (correctness 272 + suspicious 63, of 870 defined) | eslint-plugin-sonarjs: **~215 Sonar rules** (bug/security/smell) | OSV-Scanner (package-lock/yarn.lock) |
| Java | PMD: **213 enabled** (226 category rules − 13 excluded; errorprone/bestpractices/security/design/multithreading) | SpotBugs **~470 bug patterns** + FindSecBugs **144 security detectors** (CWE-tagged, bytecode-level, needs buildable project) | OSV-Scanner (pom.xml) |
| SQL | SQLFluff: **~48 enabled** (of 68; layout/capitalisation groups dropped) | — | — |
| Go / C# / Kotlin / Ruby / PHP / Rust / Swift / Scala | oxlint/ESLint where applicable | Semgrep `auto` packs (**2800+** registry rules) | OSV-Scanner (go.mod/Cargo/composer/Gemfile/*.csproj) |
| Secrets (any language) | — | gitleaks: **222 rules** (vendor keys, private keys, entropy heuristics); TruffleHog deep layer (opt-in): **800+ detectors** | — |

**De-duplication between tools** (by design, verified in the express/jsoup validation scans):

- **JS/TS**: `eslint-plugin-oxlint` turns off every ESLint-core/typescript-eslint rule the fast oxlint layer already owns — one finding per issue. sonarjs contributes only its *unique* Sonar rules (its `no-unused-vars` duplicate is explicitly disabled).
- **Python**: ruff's flake8-bandit (`S`) family and bandit's `B` family intentionally overlap on security topics; both run because their rule semantics differ. Findings keep distinct rule ids, so nothing is silently lost.
- **Java**: PMD (source-level, no compile) and SpotBugs/FindSecBugs (bytecode-level, compile required) are complementary layers; the small overlap (e.g. resource-handling) is kept deliberately.
- Cross-engine duplicate *findings* on the same line are not merged — different tools' verdicts are preserved and attributed.

## Rule trimming, tuning & parameters

All configuration lives in the **target project**, never in `~/.codespot`. Three layers, highest priority first:

### 1. Native config files (full power, recommended for tuning)

If the project has a native config, codespot uses it **instead of** its built-in defaults for that engine:

| File | Affects |
|---|---|
| `.ruff.toml` / `ruff.toml` / `[tool.ruff]` in `pyproject.toml` | ruff — select/ignore rules, `line-length` and every other parameter |
| `.oxlintrc.json` | oxlint — categories & rules |
| `.sqlfluff` | SQLFluff — dialect, rules, layout behaviour |
| `.gitleaks.toml` | gitleaks — extra rules / allowlists |

Example — allow longer lines and drop two ruff rules by creating `.ruff.toml`:

```toml
line-length = 120
[lint]
ignore = ["E501", "PLR0913"]
```

### 2. `.codespot/config.json` (simple switches, codespot-style)

Use **check categories** (no engine names needed):

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

- `rules.<category>.disabled: true` — skip that category entirely.
- `rules.<category>.ignore: [rule ids…]` — drop specific findings (ids are the underlying rule codes as they appear in `report.json`).
- `dialect` — SQLFluff dialect when file comments/heuristics can't detect it.
- `semgrep_config` — override the default `auto` ruleset with any `--config` value (registry set, local rules dir, single rule file).

Categories: `secrets`, `python_lint`, `python_security`, `js_lint`, `java`, `sql`, `semantic`, `dependencies`.

### 3. codespot built-in defaults (fallback)

Live in `codespot/assets/` — used when neither of the above exists.

**Severity adjustments** (a rule fires too often at the wrong level) via `.codespot/severity-overrides.json`:

```json
{"ruff": {"rules": {"RUF100": "info"}}, "pmd": {"default": "minor"}}
```

**False positives** (one specific occurrence): add to `.codespot/ignore`:

```json
[{"tool": "ruff", "file": "src/app.py", "rule": "PLW0603"}]
```

Secrets false positives use gitleaks' own fingerprint file: echo the `Fingerprint` from the finding into `.gitleaksignore` at the repo root.

## Vulnerability database & engine updates

- **Dependency vulnerabilities (OSV-Scanner)** — offline-first:
  - No local DB yet → queries the live [osv.dev](https://osv.dev) API on every scan (always current, needs network).
  - Run `codespot update-db` once to download the local vulnerability DB (cached under `~/Library/Caches/osv-scalibr/` or `~/.cache/osv-scalibr/`).
  - With a local DB present, dependency scans run fully offline (`--offline-vulnerabilities`); re-run `codespot update-db` to refresh it. The adapter picks automatically: offline DB present → offline; absent → online.
- **Semgrep rules**: fetched from the official registry and cached under `~/.semgrep/`. Re-scanning reuses the cache; delete `~/.semgrep/cache` (or run with a different ruleset) to force a refresh.
- **Engine upgrades**: engines are pinned in `scripts/engines/registry.json` (`version` field). To upgrade an engine, bump the version there and re-run `scripts/codespot setup` (old versions stay in `~/.codespot/engines/` and can be deleted manually).
- **Reset an engine**: `rm -rf ~/.codespot/engines/<name>-<version>` then `codespot setup`.

## Reports & branding

- `report.md` / `codespot show` are **codespot-branded**: every rule gets a stable `CS-xxxxx` id (derived from the underlying rule — same rule, same id, across repos and runs). Underlying engine names are never shown to users.
- `report.json` is the agent-facing interface: it keeps `tool` / `rule` / `ruleUrl` / `csId` / `fixHint` per issue so the AI can research and fix precisely.
- Secrets findings are always redacted in both reports (first/last 4 characters). If a real secret is found: **rotate it first**, deleting the line is not enough once it has been committed.

## Adding a new engine

Engines are self-contained adapters. To add one:

1. Drop `scripts/engines/engine_<name>.py` implementing the contract: `--workdir <root> --files <list.json> --out <result.json>`; exit `0` on success (issues as JSON array), `2` on engine failure (reason on stderr).
2. Emit the unified issue schema (see `common.make_issue`) — severity is normalized via `scripts/rules-severity.json`.
3. Register it in `scripts/engines/registry.json` (install form, version, languages, category) and add fixtures under `tests/fixtures/` + `expected.json`.

## Known limitations & suggested improvements

- **Type-aware JS/TS rules** are off (need tsconfig); Python-only repos don't lose anything.
- **SpotBugs layer** needs a buildable project; it silently skips otherwise (PMD still covers source-level).
- **OSV-Scanner needs network**; an offline vulnerabilities-DB mode is a possible future addition.
- **Dockerfile files** (no extension) aren't language-detected yet; semgrep can still cover them via `semgrep_config`.
- **`.codespot/config.json` is the only project config** — a `.codespot.toml` variant and per-path rule scopes could be added on demand.
- **SQLFluff on py3.9 machines** runs the older 3.x line (4.x needs python ≥3.10).

## License boundary

codespot is an internal tool. Semgrep CE and its registry rules are used under the Semgrep Rules License "internal business purposes" only — rules are fetched at runtime on the user's machine and are not bundled with or distributed by codespot. Do not sell or externally distribute codespot with this engine enabled.
