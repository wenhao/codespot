# Spec Delta

## Purpose

定义扫描目标范围（增量档位）的计算行为：从 git 状态推导待扫文件清单。

## ADDED Requirements

### Requirement: 四档扫描范围

`scope` SHALL 支持四档：`uncommitted`（git status --porcelain，含未跟踪文件）、`unpushed`（`@{u}..HEAD` 变更加上未提交部分；无上游分支时回退与 `main` 比较）、`ref:<ref>`（与指定基线的差异加未提交部分）、`all`（仓库全部受支持文件）。`scan --scope auto`（默认）SHALL 依序取 uncommitted → unpushed → all 中第一个非空档位。

#### Scenario: 默认档位自动降级

- **WHEN** 工作区干净但本地有未推送提交
- **THEN** `scan`（scope auto）实际扫描 unpushed 档位的文件

#### Scenario: 无上游分支回退 main

- **WHEN** 当前分支没有配置上游且本地存在 main 分支
- **THEN** unpushed 档位计算与 main 的差异，不报错

### Requirement: 输出文件清单

scope 结果 SHALL 输出 JSON 文件清单（绝对或仓库相对路径 + 检测到的语言），排除 `.git`、`.codespot` 目录与二进制文件；`uncommitted` 与 `unpushed` 档 MUST 包含未跟踪文件。

#### Scenario: 未跟踪新文件被纳入

- **WHEN** 新建的未 add 的 `src/new.py` 存在违规
- **THEN** uncommitted 档位清单包含该文件且扫描覆盖它
