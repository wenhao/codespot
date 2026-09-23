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

SKILL.md 编排 SHALL 升级为完整修复循环（见 fix-loop 能力）：修复范围选项、合理性判断、≤3 轮重扫验证、误报登记、不自动 commit。

#### Scenario: 修复循环演练

- **WHEN** 用户在选项中选择"全部修复"
- **THEN** agent 按修复循环工作流执行并在收敛后给出三类汇总
