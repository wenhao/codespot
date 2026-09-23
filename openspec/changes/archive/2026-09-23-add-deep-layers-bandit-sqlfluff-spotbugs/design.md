# Design

## Context

M0/M1 已归档。本批按调研报告 3.5（bandit/SQLFluff/SpotBugs+FSB 行）、3.8（SQLFluff 细节）、3.9（SpotBugs 编排）与第 6 章 M2 里程碑实施。

## Decisions

### D1. bandit 独立适配器（engine_bandit.py）
与 ruff 分开而不是合进 engine_py：两工具升级节奏、依赖运行时不同（bandit 在 venv 里），独立适配器让 registry 可分别锁定/降级。bandit 装进 sqlfluff 同款 venv 形态？不——bandit 装到自己的 `bandit-1.9.4` venv，互不影响。bandit 退出码：0=无发现，1=有发现，其他=错误。

### D2. SpotBugs 作为 engine_java 的内部第二层（不新开 registry 条目）
吸取 M1 教训：同语言多层放同一适配器内部编排，避免调度重复。spotbugs 发行包（zip）+ findsecbugs-plugin.jar（Maven Central 下载）都放进 `spotbugs-4.10.4` 目录；引擎运行时：PMD 必跑 → 探测构建文件 → 编译 → `spotbugs -textui -pluginList fsb.jar -sarif=... <classes目录>`。编译产物目录按构建系统取 target/classes 或 build/classes/java/main。规则元数据（rank/priority/cweid）从 SARIF driver.rules[].properties 读。

### D3. SQLFluff venv 形态
`python3 -m venv <dir> && <dir>/bin/pip install sqlfluff==4.3.0`。适配器用 `<dir>/bin/sqlfluff` 绝对路径调用。配置：`--config` 指向 assets/sqlfluff.cfg（关闭 LT/CP），输出 `--format json`（比 SARIF 解析更直接，含 unparsable 信息？——4.x json 每条含 violation code；PRS 规则 code 为 PRS，据其打标）。dialect 用 `--dialect` 显式传。

### D4. severity-overrides 增强（D-default）
common.normalize_severity 已按 overrides→defaults 顺序查 rules 与 default；本批仅补 pmd/bandit/sqlfluff/oxlint 默认映射数据并加两个单测场景（已由 selftest 覆盖）。无代码结构变化。

### D5. 夹具策略
- bandit：sample_bad.py 已含 eval（B307）与 hardcoded password（B105 可能与 ruff S105 重复行）——补 fixture 文件 sample_security.py（B105 + B101 assert? tests/** ignored only for ruff；bandit 独立）。
- SQL：sample_bad.sql（小写关键字+裸 UNION+LIMIT 无 ORDER BY 等语义问题 + 解析失败片段）。
- SpotBugs：fixtures 复用 M1 的 Repo.java？需要编译产物——selftest 里对 java 夹具用 javac 编到临时目录再触发 spotbugs 层？简化：SpotBugs 层依赖"项目构建"，selftest 用最小 pom.xml 夹具 + mvn compile 太重。**取舍**：selftest 对 spotbugs 层只验证"无构建文件时得体跳过"（夹具无 pom），完整注入路径在 e2e 验收用演示仓库覆盖（有 mvn）。记录为已知验证边界。

## Risks / Trade-offs

- [mvn 首次编译下载依赖慢] → 300s 超时 + stderr 提示；演示仓库预置本地依赖。
- [SQLFluff 首次启动慢（~2s）] → SQL 文件少，可接受。
- [findsecbugs 与 spotbugs 版本匹配] → registry 锁 spotbugs 4.10.4 + fsb 1.14.0（官方兼容组合）。

## Open Questions

（无）
