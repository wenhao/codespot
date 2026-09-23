# Proposal

## Why

codespot 现有 7 引擎均扫描代码本身，缺少供应链维度——项目依赖里的已知漏洞（CVE）无法被检出。kaipanla 类多语言项目（Python/前端/Java）都有真实依赖面。已确认集成 **OSV-Scanner**（Google，Apache-2.0，基于 OSV 漏洞库，轻量低噪音）作为第 8 引擎、新类别 `dependencies`；TruffleHog 不集成（gitleaks 已覆盖）。

## What Changes

- registry 新增 `osv-scanner`：类别 `dependencies`，always_on，平台直链二进制安装形态（setup_engine 新增 `raw_binary` 支持），版本锁定 2.6.0。
- 新增 `engine_deps.py`：在范围内查找依赖清单/锁文件（requirements*.txt、package-lock.json、pom.xml、go.mod、Cargo.lock、composer.lock、Gemfile.lock、*.csproj、pyproject.toml 等），逐个以 `-L` 传入 `osv-scanner scan source -f json`；解析 results→统一 issue（`rule`=GHSA/OSV id，`severity` 优先取 CVSS 汇总否则 major，`cwe` 缺省，fix 建议透传 `fixed` 版本）；无清单时输出空结果。
- csId/品牌/报告/双层配置自动继承（category=dependencies：`disabled`/`ignore` 即可用）。
- 夹具：含已知漏洞旧版本 pin 的 requirements.txt；selftest 标记 `selftest_optional`（需联网查 osv.dev）。
- SKILL.md/README 更新。本批不含：离线漏洞库（`--offline`+本地 DB）、容器镜像扫描。

## Capabilities

### New Capabilities
- `dependency-engine`: OSV-Scanner 适配——清单发现、调用、JSON 解析、severity 映射、网络语义。

### Modified Capabilities
- `scan-orchestration`: setup 新增 raw_binary 安装形态（直链下载二进制 + chmod）。
- `skill-workflow`: description 增加"依赖漏洞/供应链"触发场景。

## Impact

- 新增 scripts/engines/engine_deps.py；setup_engine.py 加 raw_binary；registry/category 自动使 config.json 的 `rules.dependencies.disabled/ignore` 生效。
- 运行语义：清单检出需联网查询 osv.dev（结果由 API 返回），断网时该引擎记 engine_error 不阻塞其他引擎。
