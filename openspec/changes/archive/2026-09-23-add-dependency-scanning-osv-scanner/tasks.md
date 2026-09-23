# Tasks

## 1. 安装形态

- [x] 1.1 setup_engine 支持 raw_binary（直链下载+chmod）；registry 新增 osv-scanner 2.6.0（raw_binary，category=dependencies，always_on）；验证：`codespot setup osv-scanner` 安装成功且幂等
- [x] 1.2 验证 CLI 行为：`scan source -L <清单> -f json` 的 JSON 结构与退出码（0/1/2）；验证：对含漏洞 pin 的样例清单手工运行

## 2. 适配器

- [x] 2.1 实现 engine_deps.py：清单发现、逐清单 `-L` 合并一次调用、JSON 解析（rule=id、ruleUrl=osv.dev 页、severity 映射、fixHint=fixed 版本、cwe 若有）、无清单空结果、退出码 0/1 成功；验证：夹具 requirements.txt 检出已知 CVE

## 3. 收尾

- [x] 3.1 夹具（vulnerable requirements.txt）+ expected.json（semgrep 同款 selftest_optional 处理）；selftest 全绿；验证：`codespot selftest`
- [x] 3.2 SKILL.md 触发描述 + README 引擎矩阵/许可说明；验证：文档一致
- [x] 3.3 端到端验收：kaipanla 重扫确认 dependencies 类别工作、双报告/品牌/show 正常；验证：输出人工复核
