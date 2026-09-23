# Spec Delta

## Purpose

定义 gitleaks 密钥扫描适配行为：dir 模式扫描、报告脱敏、误报通道。密钥引擎跨语言常开。

## ADDED Requirements

### Requirement: dir 模式扫描工作区

适配器 SHALL 使用 `gitleaks dir <目标>` 扫描工作区文件（不触碰 git 历史）；每次调用传入单个路径（多目标时由适配器按目录聚合，不做逐文件循环调用）。

#### Scenario: 检出硬编码密钥

- **WHEN** 目标文件含 AWS Access Key 样例
- **THEN** 产出 issue 的 rule 为对应 gitleaks 规则 ID，severity 为 critical，cwe 为 798

### Requirement: 报告脱敏

issue 的 snippet 字段 MUST 脱敏：仅保留命中内容的前 4 与后 4 个字符，中间以 `…` 代替；report.md 中同样只出现脱敏形式。密钥原文 MUST NOT 出现在任何报告产物中。

#### Scenario: snippet 不泄漏原文

- **WHEN** 扫描含 `AKIAIOSFODNN7EXAMPLE` 的文件
- **THEN** 报告中该行 snippet 呈现为 `AKIA…MPLE` 之类的前后 4 字符形式，全文检索报告文件找不到完整密钥

### Requirement: 退出码歧义消解

gitleaks 退出码 1 同时表示"发现泄漏"与"运行出错"：适配器 MUST 以"是否生成了可解析的报告文件"区分二者——有报告则按发现处理（退出 0），无报告则按引擎失败处理（退出 2 并带原因）。

#### Scenario: 发现泄漏时适配器返回 0

- **WHEN** gitleaks 因发现密钥返回退出码 1 但报告文件有效
- **THEN** 适配器解析报告并产出 issue，自身退出码为 0

### Requirement: 误报 ignore 通道

适配器 SHALL 尊重仓库根的 `.gitleaksignore`（fingerprint 精确忽略）；`.codespot/ignore` 中 `tool=gitleaks` 的条目（按 file+rule 匹配）SHALL 在合并阶段过滤。

#### Scenario: fingerprint 忽略生效

- **WHEN** 将某条 finding 的 fingerprint 写入 `.gitleaksignore` 后重扫
- **THEN** 该条不再出现在报告中
