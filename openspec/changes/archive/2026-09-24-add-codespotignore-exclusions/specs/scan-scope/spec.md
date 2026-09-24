# Spec Delta

## MODIFIED Requirements

### Requirement: 输出文件清单

scope 结果 SHALL 输出 JSON 文件清单（路径 + 检测到的语言），语言检测后缀扩展支持：`.go`→go、`.rb`→ruby、`.php`→php、`.kt/.kts`→kotlin、`.rs`→rust、`.cs`→csharp、`.c/.h`→c、`.cpp/.cc/.hpp`→cpp、`.tf`→terraform、`.yaml/.yml`→yaml、`.swift`→swift、`.scala`→scala。

排除 SHALL 分两层，作用于全部四档：
1. **内置排除**（不可被用户反选）：`.git/`、`.codespot/`、`.codespotignore`、`node_modules/`、`vendor/`、`dist/`、`build/`、二进制文件；
2. **用户排除**：项目根 `.codespotignore`，gitignore 子集语法——逐行模式；`#` 注释与空行忽略；尾 `/` 表示仅匹配目录；模式内含 `/`（除尾部）时锚定仓库根，否则匹配任意层级路径名；支持 `*`、`?`、`**` 通配；`!` 前缀反选，**后行胜出**（最后匹配的模式决定结果）。

#### Scenario: Go 文件被检测语言

- **WHEN** 范围含 `main.go`
- **THEN** 清单中该文件 language=go，可供 semgrep 匹配

#### Scenario: 既有排除规则不变

- **WHEN** 范围含 `.codespot/report.json` 与 `node_modules` 下的文件
- **THEN** 两者均不出现在清单中

#### Scenario: 未跟踪新文件被纳入

- **WHEN** 新建的未 add 的 `src/new.go` 存在
- **THEN** uncommitted 档位清单包含该文件且 language=go

#### Scenario: 用户忽略文件类型

- **WHEN** `.codespotignore` 含 `*.log` 且范围含 `debug.log`
- **THEN** `debug.log` 不出现在任何档位清单中

#### Scenario: 用户忽略目录（任意层级）

- **WHEN** `.codespotignore` 含 `generated/` 且范围含 `src/generated/x.py` 与 `generated/y.py`
- **THEN** 两者均被排除

#### Scenario: 反选后行胜出

- **WHEN** `.codespotignore` 依次含 `*.log` 与 `!keep.log`，范围含 `keep.log`
- **THEN** `keep.log` 出现在清单中

#### Scenario: 内置排除不可反选

- **WHEN** `.codespotignore` 含 `!node_modules/`
- **THEN** node_modules 下文件仍被排除
