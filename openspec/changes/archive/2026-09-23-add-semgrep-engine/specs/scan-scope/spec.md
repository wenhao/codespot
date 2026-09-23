# Spec Delta

## MODIFIED Requirements

### Requirement: 输出文件清单

scope 结果 SHALL 输出 JSON 文件清单（路径 + 检测到的语言），语言检测后缀扩展支持：`.go`→go、`.rb`→ruby、`.php`→php、`.kt/.kts`→kotlin、`.rs`→rust、`.cs`→csharp、`.c/.h`→c、`.cpp/.cc/.hpp`→cpp、`.tf`→terraform、`.yaml/.yml`→yaml、`.swift`→swift、`.scala`→scala；排除规则与既有行为不变（`.git`、`.codespot`、二进制文件、node_modules 等）。

#### Scenario: Go 文件被检测语言

- **WHEN** 范围含 `main.go`
- **THEN** 清单中该文件 language=go，可供 semgrep 匹配

#### Scenario: 既有排除规则不变

- **WHEN** 范围含 `.codespot/report.json` 与 `node_modules` 下的文件
- **THEN** 两者均不出现在清单中

#### Scenario: 未跟踪新文件被纳入

- **WHEN** 新建的未 add 的 `src/new.go` 存在
- **THEN** uncommitted 档位清单包含该文件且 language=go
