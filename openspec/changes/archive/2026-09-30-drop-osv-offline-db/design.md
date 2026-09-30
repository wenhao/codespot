# Design

## Decisions

### D1. 移除面收敛在三处
engine_deps.py（去 offline 分支与 offline_db_available）、codespot（do_update_db + parser + ensure_semgrep_rules 保留——semgrep 本地规则默认不受影响）、make_bundle.py（去 collect_osv_db 与 OSV_CACHE_BASES）。README/SKILL.md 文案同步。

### D2. 断网语义沿用既有隔离
engine_errors 记录 + md 中性提示，不改。

## Open Questions
（无）
