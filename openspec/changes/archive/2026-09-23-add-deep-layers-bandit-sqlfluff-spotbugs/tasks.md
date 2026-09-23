# Tasks

## 1. 安装与配置

- [x] 1.1 setup_engine 增加 venv 形态（python3 -m venv + pip 锁版本）；registry 新增 bandit 1.9.4（venv）、sqlfluff 4.3.0（venv）、spotbugs 4.10.4（zip+wrapper，附 findsecbugs-plugin 1.14.0 下载）；验证：`codespot setup` 全部装齐且幂等
- [x] 1.2 rules-severity.json 补 bandit（H/M/L→critical/major/minor）、sqlfluff（AM/ST→major，PRS→minor）映射；验证：selftest severity 断言

## 2. bandit 引擎

- [x] 2.1 实现 engine_bandit.py（json 解析、severity/confidence 映射、B 编码 ruleUrl）；验证：夹具检出 B105 等 ≥2 条

## 3. SQLFluff 引擎

- [x] 3.1 建 assets/sqlfluff.cfg（关 LT/CP）与 engine_sql.py（dialect 探测链、json 解析、PRS 打 unparsable 标）；验证：夹具 SQL 语义规则命中、LT/CP 不出现、无 dialect 时 ansi 兜底+提示

## 4. SpotBugs+FindSecBugs 层

- [x] 4.1 扩展 engine_java.py：构建探测→编译→spotbugs SARIF 扫描→CWE/rank/severity 映射→安全类提档；无构建文件/编译失败得体跳过；验证：无 pom 夹具跳过路径生效（e2e 演示仓库验证完整注入路径）

## 5. 收尾

- [x] 5.1 SKILL.md 触发描述扩展 SQL；README 引擎矩阵更新；验证：文档与实现一致
- [x] 5.2 夹具扩充（sample_security.py、sample_bad.sql）+ expected.json 扩展；selftest 全绿；验证：`codespot selftest`
- [x] 5.3 端到端验收：演示仓库（带 pom.xml 的 Java 注入样例 + SQL + Python）全量扫描；验证：五维度发现齐全、双报告正常、退出 0
