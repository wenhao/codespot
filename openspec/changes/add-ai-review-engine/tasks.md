# Tasks

## 1. 引擎与计划

- [x] 1.1 registry 新增 ai 引擎（opt_in/agent_driven/category=ai_review/无安装）；实现 engine_ai.py 计划生成（文件行数、schema、示例、审查重点、分批指引），scan --engine ai 走通；验证：ai-plan.json 存在且内容齐全
## 2. absorb

- [x] 2.1 实现 `codespot ai-scan absorb`：校验（字段/severity/file/line/AI- 前缀/confidence）、make_issue 构造、替换式合并、summary 重算、双报告重写；验证：合法条目合并、越界条目拒绝、旧 AI 条目被替换

## 3. 收尾

- [x] 3.1 SKILL.md 三步工作流 + README 英中同步（opt-in 用法、advisory 边界）；验证：文档一致
- [x] 3.2 端到端验收：演示仓库 scan --engine ai → 手写 ai-result.json（2 合法 + 1 越界）→ absorb → 报告含 2 条 AI 发现（CS 编号、confidence）、md 无引擎名；验证：输出人工复核
