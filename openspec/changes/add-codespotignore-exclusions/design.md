# Design

## Context

gitignore 子集自实现（Python 标准库无 gitignore matcher；pathlib.match 在 py3.9 不支持 `**`）。仅 scope.py 一个改动点。

## Decisions

### D1. 匹配器：模式 → 正则，逐条按序评估，后行胜出
每行编译为 (neg, dir_only, anchored, regex)：
- 翻译：`**`→`.*`，`*`→`[^/]*`，`?`→`[^/]`，其余 re.escape；
- 锚定（模式内含 `/`）：`^T(/|$)`；非锚定：`(^|/)T(/|$)`——`(/|$)` 使 `build` 也能命中 `build/x.py` 前缀，等价目录语义，dir_only 不需单独分支（对文件路径而言目录模式即前缀命中）；
- 评估：从上到下记录最后一个命中的模式的 neg；无命中 → 保留。

### D2. 过滤接入点
`compute()` 返回前统一 `_apply_excludes(root, files)`：先内置 EXCLUDED_DIRS/文件（不可反选），再用户模式。三档（uncommitted/unpushed/ref）与 all 共用；`.codespotignore` 加入内置排除。

### D3. 边界
- 反选只作用于用户模式之间的顺序，不覆盖内置；
- 模式以 `/` 开头视为锚定（去掉前导 `/`）；
- 空文件/不存在 → 行为与现状完全一致（零风险回退）。

## Risks / Trade-offs
- [gitignore 完整语义（字符类、转义）未实现] → 文档明确子集；fnmatch 风格已覆盖 99% 场景。
- [每文件 × 每模式正则] → 模式数与文件数都是百级，性能无虞。

## Open Questions
（无）
