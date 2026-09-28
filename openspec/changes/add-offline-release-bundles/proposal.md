# Proposal

## Why

用户需要对外发布**离线 release**：包内自带全部引擎与漏洞数据，下载后全程零网络可用，覆盖 linux/macOS/windows。引擎二进制不能进 git 仓库，但 GitHub **Release 资产**正是为此设计（不属于 git 历史、单资产 ≤2GB）。用户已确认默认方案：TruffleHog 进包（附 AGPL 源码链接履行再分发义务）；Release 保持 public。

## What Changes

- 新增 `skill/scripts/make_bundle.py`（维护者打包工具）：单平台上收集 skill 载荷 + 已装引擎（engines/ 原样含 .ok）+ venv 引擎的离线 wheels（`pip download` 全传递依赖）+ OSV 离线库缓存 + Semgrep 规则快照 + `THIRD-PARTY-NOTICES`（各引擎许可与上游源码链接，TruffleHog AGPL 源码可得）+ 生成的 `install-offline.sh/.bat`，产出 `codespot-offline-<version>-<os>-<arch>` 包。
- setup 离线分支：`codespot setup --offline-dir <包>/offline` 时 venv 引擎走 `pip --no-index --find-links wheels/`（离线安装）；wheels 目录按平台与 python 大版本自动匹配。
- engine_semgrep：默认规则选择升级——`~/.codespot/semgrep-rules/` 存在（离线包装机后生成）则用它作默认 `--config`，否则维持 `auto`。
- 新增 `.github/workflows/release.yml`：push tag `v*` / 手动触发；四平台矩阵各构建一个 bundle 并上传 artifact；publish 作业创建 GitHub Release 并附 4 个资产；构建作业内做离线冒烟（解包 → install-offline → `--offline-dir` scan）。
- README 英中新增 "Offline release" 章节；许可边界更新（对外分发 = 附带各引擎许可与 AGPL/LGPL 源码链接）。

## Capabilities

### New Capabilities
- `offline-release`: 离线发布包——内容清单、wheel 离线安装、install 脚本、平台矩阵与发布流程。

### Modified Capabilities
- `scan-orchestration`: setup 支持 `--offline-dir`（wheel 离线安装分支）。

## Impact

- 新增 make_bundle.py 与 release.yml；setup_engine/setup CLI 小改；engine_semgrep 默认规则回退逻辑；文档。
- 语义：对外发布=再分发，须附第三方许可与源码链接（工具自动生成清单）。
