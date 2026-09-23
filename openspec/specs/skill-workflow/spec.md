# skill-workflow Specification

## Purpose
定义 SKILL.md 的触发条件与本批编排指令范围（到"呈现报告与修复选项"为止，修复执行属后续批次）。

## Requirements

### Requirement: 技能触发

SKILL.md frontmatter 的 name MUST 为 `codespot`；description MUST 覆盖触发场景：用户要求扫描/静态检查/lint 代码、检查 AI 生成的代码、找密钥泄漏或安全问题，即使未点名 codespot 也应触发。

#### Scenario: 自然语言触发

- **WHEN** 用户说"帮我扫一下刚才生成的代码有没有问题"
- **THEN** 技能被触发并按 SKILL.md 指令执行 `codespot scan`

### Requirement: 编排指令范围（本批）

SKILL.md SHALL 指示 agent：① 首次运行先执行 setup（幂等）；② 执行 scan 并读取 report.json；③ 以人读语言摘要报告并按 AskUserQuestion 呈现后续选项（仅修复 critical / major 及以上 / 全部 / 仅查看），**本批选项仅影响 agent 后续的人工修复范围，不涉及自动修复循环**；④ 提示 `.codespot/` 应加入用户项目 .gitignore。

#### Scenario: 呈现选项

- **WHEN** 报告含 critical 与 minor 发现
- **THEN** agent 呈现的选项至少包含"仅修复严重"、"重要及以上"、"全部"、"仅查看报告"四项

### Requirement: JS/TS 与 Java 场景触发

description MUST 额外覆盖 JS/TS 与 Java 项目场景（"检查一下 JS 代码"、"扫扫这个 Java 文件"等）。

#### Scenario: Java 项目触发

- **WHEN** 用户说"帮我扫一下这个 Java 文件"
- **THEN** 技能触发并按 SKILL.md 工作流执行（Java 引擎按需安装）

### Requirement: 编排指令升级为修复循环

SKILL.md 修复选项 SHALL 增加"先查看问题详情"：agent 以 `codespot show` 分批呈现详情（按严重级/文件分组，含 CS 编号）后，重新呈现修复选项；呈现给用户的文案 MUST NOT 出现底层引擎名，涉及规则时只用 CS 编号；引擎名仅允许出现在 agent 内部决策（读 report.json）中。

#### Scenario: 先看详情再决策

- **WHEN** 用户选择"先查看问题详情"
- **THEN** agent 用 show 呈现详情后重新给出修复选项

#### Scenario: 修复循环演练

- **WHEN** 用户在选项中选择"全部修复"
- **THEN** agent 按修复循环工作流执行并在收敛后给出三类汇总

### Requirement: SQL 场景触发

description SHALL 额外覆盖 SQL 场景（"扫一下这几个 SQL 文件"、"检查 SQL 规范"等）。

#### Scenario: SQL 项目触发

- **WHEN** 用户说"帮我检查一下迁移目录里的 SQL"
- **THEN** 技能触发，SQL 引擎按需安装并扫描

### Requirement: 依赖漏洞场景触发

description SHALL 覆盖依赖/供应链场景（"查一下依赖有没有漏洞"、"依赖安全检查"等）。

#### Scenario: 依赖检查触发

- **WHEN** 用户说"帮我看看 requirements 里的依赖有没有漏洞"
- **THEN** 技能触发并按 SKILL.md 工作流执行（依赖引擎按需安装）
