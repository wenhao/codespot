# Tasks

## 1. CS-ID 与品牌渲染

- [x] 1.1 common.make_issue 统一生成 csId（sha1(tool|rule) 前 5 hex，扫描内碰撞加后缀）；验证：selftest 断言每条 issue 有唯一合法 csId
- [x] 1.2 report.md 渲染 codespot 化：CS 编号取代规则链接、engine_errors 改"检查模块提示（类别别名）"、全文无引擎名；验证：夹具渲染后对引擎名清单做全文断言（selftest）

## 2. show 子命令

- [x] 2.1 实现 `codespot show`（--severity/--file/--rule/--limit），输出 CS 编号详情、无引擎名；验证：对夹具报告按各参数过滤人工核对

## 3. 双层规则配置

- [x] 3.1 registry 补 category 字段；common 新增 config rules 读取（disabled/ignore，未知键警告）；主控 select_engines 跳过 disabled 类别、merge_issues 应用 ignore 过滤（tool→category 映射）；验证：夹具上 disabled/ignore 场景分别生效
- [x] 3.2 原生配置优先：ruff（.ruff.toml/ruff.toml/pyproject [tool.ruff]→省略 --config）、oxlint（.oxlintrc.json→省略 -c）、sqlfluff（.sqlfluff→--config 指向）、gitleaks（文档说明原生自动读取）；bandit ignore→-s、eslint ignore→客户端过滤；验证：带 .ruff.toml 的演示项目行为遵循它

## 4. SKILL.md 与收尾

- [x] 4.1 SKILL.md：修复选项加"先查看问题详情"（codespot show 分批呈现→回到修复选项循环）；用户文案禁用引擎名、规则只用 CS 编号；验证：文件审阅
- [x] 4.2 selftest 扩展：csId 存在且稳定、md 无引擎名断言；验证：selftest 全绿
- [x] 4.3 README 更新（show、config.json rules 段、品牌说明）；验证：文档与实现一致
- [x] 4.4 端到端验收：kaipanla 重扫（md 无引擎名、csId 稳定、show 过滤可用、config disabled 场景生效）；验证：输出人工复核
