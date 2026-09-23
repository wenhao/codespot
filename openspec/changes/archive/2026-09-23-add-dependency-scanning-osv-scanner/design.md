# Design

## Context

补齐供应链维度。OSV-Scanner 2.6.0（Google，Apache-2.0）为 release 直链裸二进制（darwin amd64/arm64、linux amd64/arm64），CLI `scan source -L <lockfile> -f json`，退出码 0=干净、1=有漏洞；查询 osv.dev 需联网。

## Decisions

### D1. 安装：raw_binary 形态
setup_engine 新增：registry download 带 `"raw_binary": true` 时跳过解压，直接下载到 `<dest>/<name>` + chmod + `.ok`。URL 模板 `.../download/{version}/osv-scanner_{os}_{arch}`（{ext} 置空）。

### D2. always_on + 清单自筛
依赖问题与"哪些文件改了"弱相关（改 .py 也可能受锁文件漏洞影响），故 registry `always_on: true`；适配器在清单不存在时秒级空结果，避免浪费。清单集合在适配器内维护（与 spec 一致）。

### D3. 调用：逐清单 `-L` 合并为一次调用
`osv-scanner scan source -L f1 -L f2 … -f json`（-L 可重复）。退出码 0/1 视为成功；`--allow-no-lockfiles` 加上以防边界；subprocess 超时 300s。

### D4. 解析与 severity
JSON：`results[].packages[].package.{name,version}` + `vulnerabilities[].{id,summary,aliases,database_specific.severity? , affected[].ranges[].events[].fixed}`。severity：vulnerability `database_specific.severity`（有的话）按文本映射（CRITICAL/HIGH→按 codespot 表），缺省 major；`rule`=vuln id（GHSA-…），`ruleUrl`=https://osv.dev/vulnerability/<id>；fixHint 取 fixed 版本首个。

### D5. category=dependencies 联动
ignore 语义：对 dependencies 类别，ignore 列表匹配 vuln id（跳过特定 CVE/GHSA）；disabled 整体关闭。均由既有 merge/select 机制承接，零新代码。

## Risks / Trade-offs

- [每次扫描都查 osv.dev（在线）] → 清单少时仅数秒；离线 DB 放后续批次。
- [lockfile 必须是真锁文件（package-lock 而非 package.json）才能定版本] → requirements.txt 视为 pin 清单可用；package.json（无锁）精度差，仍传给扫描器由其自判。
- [非范围清单（未改动）不在增量范围] → 定位为"增量扫描关注改动面"；全量审计用 `--scope all`。

## Open Questions

（无）
