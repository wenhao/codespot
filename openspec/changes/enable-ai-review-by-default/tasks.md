# Tasks

- [x] 1. registry：ai 引擎移除 opt_in、置 always_on；验证：默认 scan 生成 ai-plan.json，config disabled 后不生成
- [x] 2. SKILL.md：标准流程插入 AI 审查三步（absorb 后再呈现选项）；"只扫不审"跳过；AI 章节标题与措辞更新；验证：文件审阅
- [x] 3. README 英中 + 两版汇报文档：ai_review 从 opt-in 改"默认开启（可关闭）"，opt-in 段落仅剩 TruffleHog，用法示例更新；验证：文档一致
- [x] 4. 回归：selftest 全绿；e2e 默认扫描含 AI 引擎且 TruffleHog 仍不参与；验证：输出复核
