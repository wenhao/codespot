# Tasks

- [x] 1. 主控：select_engines 增加有效档位与显式开启判断（--engine / config enabled），全量默认跳过 ai 并打提示行；验证：spec 5 场景实测（uncommitted 含 / all 跳过+提示 / all --engine ai 生成 / config enabled 生成 / config disabled 无提示）
- [x] 2. SKILL.md 3a 步与 README 英中同步（全量默认跳过+提示+开启方式）；验证：文档一致
- [x] 3. 回归 selftest 全绿；auto 降级 all 场景实测同样跳过；验证：输出复核
