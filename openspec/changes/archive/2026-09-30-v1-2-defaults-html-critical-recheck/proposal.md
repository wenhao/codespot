# Proposal

## Why

四个体验打磨需求（用户 2026-09-30）：① OSV-Scanner 默认在线（数据最新、避免离线库缺失导致的失败），离线库变为显式选项；② Semgrep 默认使用本地规则（确定性、快——在线拉包正是超时元凶），并提供规则更新命令；③ 扫描产出 HTML 报告（人读/汇报）；④ critical 级发现默认由 AI 逐条复审后再呈现。

## What Changes

- `engine_deps.py`：默认在线查询 osv.dev；离线仅在 `.codespot/config.json` `"osv_offline": true` 或环境变量 `CODESPOT_OSV_OFFLINE=1` 时启用（此时要求离线库已由 update-db 就位）。
- Semgrep 本地规则成为一等公民：`codespot setup` 在安装 semgrep 引擎后自动克隆/更新 `~/.codespot/semgrep-rules`；新增 `codespot update-rules` 显式刷新；engine_semgrep 默认使用本地规则（按语言子目录），缺失时回退 `auto`。
- 主控 scan 额外产出 `.codespot/report.html`（codespot 品牌、自包含 CSS、严重级卡片+发现列表，与 md 同内容）；`codespot report --html` 输出其路径/内容。
- SKILL.md：critical > 0 时 agent 必须在呈现前逐条复审 critical 发现（读上下文 → 确认 / 疑似误报 / 需人工判断），摘要中标注结论；疑似误报默认不进修复范围。
- README 英中同步。

## Capabilities

### New / Modified Capabilities
- `dependency-engine`（MODIFIED）：默认在线、离线为显式选项。
- `semgrep-engine`（ADDED requirements）：本地规则默认与 update-rules。
- `reporting`（ADDED）：HTML 报告产物。
- `skill-workflow`（ADDED）：critical AI 复审步骤。

## Impact

- engine_deps.py / setup_engine.py 或 codespot（ensure rules + update-rules）/ codespot（report.html 渲染）/ SKILL.md / README；v1.1.1 及更早的离线 bundle 不受影响（其内嵌适配器为旧逻辑）。
