# Proposal

## Why

目前排除项是内置硬编码（`.git`、`.codespot`、node_modules 等），用户无法按项目自定义忽略文件夹或文件类型。需要类 `.gitignore` 的排除语法让用户声明"哪些不扫"（生成物、vendored 代码、数据文件等）。

## What Changes

- 新增项目根 `.codespotignore` 文件支持，语法对齐 gitignore 子集：逐行模式、`#` 注释、尾 `/` 目录限定、含 `/` 锚定根、`*`/`?`/`**` 通配、`!` 反选（后行胜出）。
- scope 计算统一过滤：内置排除（不可被 `!` 反选）+ 用户模式过滤，作用于全部四档。
- `.codespotignore` 自身加入内置排除（配置非代码）。
- README（英/中）Configuration 章新增 Exclusions 小节（语法说明 + 示例 + 内置排除列表 + 反选边界）；SKILL.md 治理段补一句。

## Capabilities

### Modified Capabilities
- `scan-scope`: 输出文件清单要求扩展——.codespotignore 过滤语义与场景。

## Impact

- 仅改 skill/scripts/scope.py（模式加载与匹配）；测试夹具不动；文档同步。
