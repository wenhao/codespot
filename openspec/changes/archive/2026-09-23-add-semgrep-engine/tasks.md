# Tasks

## 1. 安装与配置

- [x] 1.1 registry 新增 semgrep（venv，1.177.0 / 回退 1.136.0，min_python 3.10）；`codespot setup` 安装成功且幂等；验证：`semgrep --version` 输出正常
- [x] 1.2 scope.py SUPPORTED_LANGS 扩展（go/ruby/php/kotlin/rust/csharp/c/cpp/terraform/yaml/swift/scala）；验证：scope 输出对 .go/.tf 等文件给出 language

## 2. 适配器

- [x] 2.1 实现 engine_semgrep.py：语言→规则集映射 + `.codespot/config.json` semgrep_config 覆盖 + `--json` 解析（check_id/path/extra 全字段、cwe、ruleUrl）+ severity 映射 + 退出码 ≥2 引擎失败；验证：对夹具运行命中预期规则、字段齐全
- [x] 2.2 许可边界落文档：适配器 docstring、README semgrep 段落均注明"仅限内部使用、规则运行时拉取、不随工具分发"；验证：文档审阅

## 3. 收尾

- [x] 3.1 夹具与 expected.json 扩展（如新增 go/security 夹具则同步 selftest；若本机规则拉取受限则记录验证边界）；验证：selftest 全绿（semgrep 可跳过需注明原因）
- [x] 3.2 端到端验收：kaipanla（Python/TS）真实仓库重扫对比基线，确认 semgrep 层产出且其他引擎无回归；验证：双报告正常、退出 0
- [x] 3.3 README/SKILL.md 更新语言矩阵与触发描述；验证：文档与实现一致
