# Design

## Context

OCR 引擎集成被否（用户不接受 LLM 后端配置），吸收其三项工程实践进内置 agent 审查。改动集中在 engine_ai.py 的 plan 生成与 SKILL.md 措辞。

## Decisions

### D1. bundle 聚类算法（engine_ai.py，纯标准库）
1. 读取每个目标文件的 import 行（正则 `^\s*(from|import)\s+([\w\.]+)`，取模块名）；
2. 建文件→本地模块名映射（路径去扩展名转点分）；同目录文件共享目录前缀；
3. 并查集（union-find）：同目录两两并；文件 A import 了文件 B 的本地模块名 → 并；
4. 输出 bundles=[[path,...],...]（按组内总行数降序）；无法关联的文件自成一组。
5. plan 新增 `bundles` 字段（每组含 files 与 totalLines），保留原 `files` 平铺清单（向后兼容）。

### D2. 分轮指引以 bundle 为单位
超限时指引文案改为"按 bundle 边界分轮，每轮 bundle 总行数 ≤5000"，不再按文件数切。

### D3. P2/P3 落在 SKILL.md（行为约束，无代码强制）
证据门槛与定位纪律是 agent 行为要求，写入 4c/4d 步骤；absorb 已有行号范围校验作最后防线（不改）。

## Risks / Trade-offs
- [聚类把弱相关文件并组] → 并查集只并"同目录"与"显式 import"，阈值保守；
- [大目录全并一组超限] → 分轮指引按 bundle 切，超限 bundle 内再按文件切（指引说明）。

## Open Questions
（无）
