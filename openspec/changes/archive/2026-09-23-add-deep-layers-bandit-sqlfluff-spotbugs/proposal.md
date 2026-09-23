# Proposal

## Why

M1 后 codespot 已覆盖 JS/TS、Python 质量、Java 源码级与密钥检测。本批（调研报告里程碑 M2）补齐**深度层与长尾语言**：Python 安全（bandit）、Java 字节码级安全（SpotBugs+FindSecBugs，需项目可编译）、SQL 规范（SQLFluff），并将 severity 配置完善为项目级可覆盖。

## What Changes

- 新增 `engine_bandit.py`：Python 安全扫描（bandit `-f json`，severity(H/M/L)+confidence 透传，与 ruff 同语言共存）。
- 扩展 `engine_java.py` 增加 **SpotBugs+FindSecBugs 第二层**（可选）：探测 pom.xml/build.gradle → 调用 `mvn -q compile` 或 `gradle compileJava`（超时 300s，失败得体跳过）→ findsecbugs CLI 扫 classes 目录 → SARIF 解析（CWE 透传、FindSecBugs 安全类提一档 severity）；无构建文件则跳过该层。
- registry/setup 新增 spotbugs（zip + wrapper）与 sqlfluff（pipx/venv 形态：`python3 -m venv` + pip 锁版本）安装支持。
- 新增 `engine_sql.py`：SQLFluff 扫描——dialect 探测链（文件内注释 `sqlfluff:dialect` > 项目 `.codespot/config.json` 的 dialect 字段 > 启发式 > `ansi` 兜底并在 stderr 提示）；默认规则集关 LT/CP（纯排版），开 AM/ST/RF/CV 语义组；解析失败（PRS）发现单列标注、不计入可修复清单。
- severity 配置化完善：`.codespot/severity-overrides.json` 支持 `{"tool": {"default": "...}}` 全工具默认与 `rules` 逐规则覆盖（M0 已实现，本批补 SQLFluff/bandit 映射并验证）。
- 夹具扩充：Python 安全（bandit 已知规则）、SQL（已知语义规则）、Java 可编译夹具（SpotBugs 层）；expected.json 扩展。
- 本批**不包含**：sonarlint-ls / tsgolint / Opengrep（M3）、plugin 打包发布（M4）。

## Capabilities

### New Capabilities
- `python-security-engine`: bandit 适配——JSON 输出、severity/confidence 映射。
- `sql-engine`: SQLFluff 适配——dialect 探测、规则取舍、解析失败处理。
- `java-deep-engine`: SpotBugs+FindSecBugs 编排——构建探测、编译、扫描、CWE 透传、失败降级。

### Modified Capabilities
- `scan-orchestration`: setup 新增 venv/pip 安装形态；engine-java 适配器内部变为两层（PMD 必跑、SpotBugs 可选层）。
- `engine-contract`: severity 覆盖行为明确（default+rules 两级）。
- `skill-workflow`: 触发描述扩展 SQL 场景。

## Impact

- 新增 scripts/engines/engine_bandit.py、engine_sql.py；扩展 engine_java.py、setup_engine.py、registry.json、rules-severity.json。
- 运行时依赖新增：python3 venv+pip（SQLFluff；装进独立 venv 不污染环境）。SpotBugs 层额外依赖用户项目的 mvn/gradle 与 JDK。
- 夹具/selftest 扩展；不改统一 issue 契约。
