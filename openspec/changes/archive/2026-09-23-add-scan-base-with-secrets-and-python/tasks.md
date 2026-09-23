# Tasks

## 1. 基座骨架

- [x] 1.1 建 `scripts/engines/registry.json`（含 gitleaks:always_on、ruff:py 两个条目，版本锁定 gitleaks 8.30.1 / ruff 0.16.8，预留 checksum 字段）；验证：`python3 -c "import json;json.load(open('scripts/engines/registry.json'))"` 通过
- [x] 1.2 建 `scripts/engines/common.py`：清单读取（--files）、结果写出（--out）、统一 issue schema 校验、脱敏函数、severity 归一化（读 rules-severity.json + `.codespot/severity-overrides.json` 覆盖）；验证：`python3 -m py_compile scripts/engines/common.py`
- [x] 1.3 建 `scripts/codespot` 主控（argparse：setup/scope/scan/report/selftest，scan 先以串行占位打通）；验证：`./scripts/codespot --help` 列出五个子命令
- [x] 1.4 建 `scripts/scope.py`：四档范围计算 + auto 降级 + 语言检测 + 排除规则，输出清单 JSON；验证：在本仓库对 uncommitted 档执行并人工核对输出清单
- [x] 1.5 建 `scripts/setup.sh` + 主控 setup 子命令：按 registry 下载 gitleaks/ruff 官方二进制到 `~/.codespot/engines/<name>-<version>/`，`--version` 校验，幂等跳过，失败清理半成品；验证：连续执行两次，第二次全部 skip，且断网模拟（错误 URL 覆盖）时无残留目录并报错

## 2. 密钥引擎（gitleaks 适配器）

- [x] 2.1 实现 `scripts/engines/engine_secrets.py`：dir 模式调用（≤50 文件逐个调用，>50 符号链接聚合目录）、退出码 1 双义性消解（报告可解析即成功）、issue 转换（severity=critical、cwe=798）、snippet 脱敏（前后 4 字符）；验证：对夹具运行，产出含 AWS key 的 critical issue 且报告无完整密钥原文
- [x] 2.2 误报通道：适配 `.gitleaksignore`（fingerprint）与 `.codespot/ignore`（tool=gitleaks 按 file+rule 过滤）；验证：写入 fingerprint 后重扫该条消失

## 3. Python 引擎（ruff 适配器）

- [x] 3.1 建 `assets/ruff-defaults.toml`（select 精选质量规则族含 S 高危项，不含纯格式规则）；验证：`ruff check --config assets/ruff-defaults.toml` 在夹具上产出预期规则集
- [x] 3.2 实现 `scripts/engines/engine_py.py`：JSON 输出解析、fix 字段透传 fixHint、>100 文件分批调用、ruleUrl 按官方规则页生成；验证：夹具产出的每条 issue 字段齐全、ruleUrl 可访问（抽查）、可修复违规的 fixHint 非空

## 4. 合并与报告

- [x] 4.1 主控 scan 完成"调度→并行执行（ThreadPool，300s 超时）→合并去重→severity 归一→engine_errors 收集"流程；验证：人为令 ruff 二进制缺失，报告仍含 gitleaks 结果且 engine_errors 有 ruff 条目、整体退出 0
- [x] 4.2 实现 report.json（generatedAt/scope/issues/engine_errors/summary）与 report.md（按严重级分组、file:line 链接、脱敏 snippet、空结果通过结论）渲染；验证：夹具扫描后 summary 计数与 issues 一致，空目录扫描产出通过结论
- [x] 4.3 主控退出码语义落地（0=流程完成，2=编排失败）；验证：范围计算失败场景返回 2，正常有发现场景返回 0

## 5. SKILL.md 与收尾

- [x] 5.1 写 `SKILL.md`（frontmatter name=codespot、description 覆盖触发场景；正文：setup→scan→读 report→摘要+AskUserQuestion 四选项→提示 .gitignore；注明本批不含自动修复循环）；验证：文件存在于 skill 发现路径（软链 `~/.agents/skills/codespot`）
- [x] 5.2 建 `tests/fixtures/`：python 夹具（含未使用 import、S101 等 ≥5 条已知违规）、secrets 夹具（EXAMPLE 假 AWS key）、预期发现清单 expected.json；验证：夹具文件齐全且假密钥使用明显示例值
- [x] 5.3 实现 `codespot selftest`：对夹具跑全部已装引擎，校验统一 schema、预期发现命中、脱敏生效；验证：`./scripts/codespot selftest` 全绿
- [x] 5.4 README 补最小使用说明（安装/三条命令）；验证：README 含 setup/scan/selftest 说明
- [x] 5.5 端到端验收：在含未提交 Python 文件（带假密钥+违规）的演示仓库执行 `codespot scan --scope uncommitted`，双报告生成、退出 0、密钥脱敏；验证：演示输出与 report.md 人工复核
