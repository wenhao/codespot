# Design

## Context

调度层一处判断 + 一行提示。有效档位在 do_scan 中已由 ensure_scope_list 返回（`effective`），传给 select_engines 即可。

## Decisions

### D1. 调度判断
select_engines(entries, requested, effective_scope)：key=="ai" 且 effective_scope=="all" 且 key 不在 requested 且 config ai_review.enabled 不为 true → 跳过。返回值附带 `ai_skipped_full` 标记供提示（disabled 导致的跳过不标记）。

### D2. 提示通道
do_scan 在调度后：若 ai_skipped_full → stdout `scan: full-scope — AI review skipped (add --engine ai to enable)`。agent 经 SKILL.md 指引在摘要中转述。不写入 report.json（属会话性提示，非发现）。

### D3. auto 降级到 all 同样生效
effective 由 compute() 返回（auto 已解析），天然覆盖；无需单独处理 ref 大范围（ref 可大可小，保持简单，文档不承诺）。

## Risks / Trade-offs
- [ref:<大基线> 也可能很大] → 本批只按档位判断，保持语义简单；文档如实写"增量档位默认开、全量默认跳过"。

## Open Questions
（无）
