# Tasks

## 1. 安装形态扩展

- [x] 1.1 registry.json 新增 oxlint / pmd（平台二进制形态，版本锁定）与 eslint-layer（npm 形态）；setup_engine 支持 `install: npm` 形态（写 package.json + npm install 锁版本），单引擎失败继续其余并最终非零提示；验证：`codespot setup` 装齐，模拟 npm 缺失时其余引擎仍装上
- [x] 1.2 现场确认 oxlint 与 pmd 的 release 资源命名（GitHub API），registry URL 模板按实调整；验证：setup 下载后 `--version` 校验通过

## 2. JS/TS 双层引擎

- [x] 2.1 建 assets：`eslint.config.mjs`（sonarjs recommended + eslint core 质量子集，末位加 plugin-oxlint 关闭清单）与 `.oxlintrc.json`（correctness 类）；验证：手工在夹具上运行两层各自产出预期规则
- [x] 2.2 实现 `engine_js.py`：oxlint 层（json 输出解析、ruleUrl 指向 oxc 规则页）+ ESLint 深度层（node_modules 存在时运行，--no-error-on-unmatched-pattern；缺失时 degraded 标注）合并输出；验证：无 npm 时仅 oxlint 层、退出 0、degraded 原因在 stderr
- [x] 2.3 去重验证：夹具含两层都会命中的规则，合并结果该问题只出现一次；验证：selftest 断言

## 3. Java PMD 引擎

- [x] 3.1 建 assets/pmd-ruleset.xml（quickstart 精简：优先级 ≥2 的 bug/安全规则）；验证：pmd check 在夹具上产出 SARIF
- [x] 3.2 实现 `engine_java.py`：JRE 探测（缺失→空结果+stderr 提示，退出 0）、SARIF 解析、priority→severity 映射（1→critical/2→major/3→minor/4,5→info）、ruleUrl 生成；验证：夹具 Java 文件检出已知规则、severity 正确；无 java 时行为符合 spec

## 4. 修复循环与收尾

- [x] 4.1 SKILL.md 升级：触发描述扩展 JS/TS/Java；工作流替换为修复循环（范围选项→合理性判断→修复→重扫≤3 轮→汇总已修复/跳过/剩余；误报登记到 .codespot/ignore 与 .gitleaksignore；不自动 commit）；验证：文件审阅 + 场景演练
- [x] 4.2 夹具扩充：JS 夹具（oxlint 与 sonarjs 各 ≥2 条命中、1 条双层重叠规则）+ Java 夹具（PMD 已知规则 ≥2 条）+ expected.json 扩展；验证：selftest 全绿
- [x] 4.3 端到端验收：演示仓库含未提交 JS + Java 文件，scan 出双报告 → 模拟修复 → 重扫清零 → ignore 登记生效；验证：全流程输出人工复核
- [x] 4.4 README 更新支持语言矩阵；验证：README 与实际引擎一致
