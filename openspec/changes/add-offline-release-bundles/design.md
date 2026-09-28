# Design

## Context

对外发布离线 release。引擎二进制不进 git，走 GitHub Release 资产；CI 四平台矩阵在原生 runner 上构建（venv wheel 与平台二进制天然匹配）。

## Decisions

### D1. venv 引擎离线 = wheel 而非搬 venv
venv 内含绝对路径不可搬移。构建机 `pip download --only-binary --python-version {3.10,3.11}` 拉全传递依赖到 `wheels/3x|4x/`；用户侧 `setup --offline-dir` 时 venv 引擎改 `pip --no-index --find-links`。按 python 大版本分子目录，安装时取 venv 实际大版本。

### D2. semgrep 离线规则 = OSS 规则仓库浅克隆
`~/.semgrep` 缓存无裸 yml（新版规则走临时目录）不可提取；semgrep.dev 的 `p/` 端点对程序化拉取 404。可靠源：github.com/semgrep/semgrep-rules（LGPL-2.1，浅克隆 ~22MB）。注意仓库根有 template.yaml 等非规则文件——**按语言子目录引用**（engine_semgrep.offline_rules_for），不整目录喂。

### D3. OSV 库随包
构建机先 `update-db`，打包时复制 osv-scalibr 缓存；install 脚本复制到目标机缓存目录（macOS Library/Caches、Linux ~/.cache、Windows AppData/Local）。库时效=构建日，MANIFEST 与 Release 说明标注。

### D4. 安装脚本生成于 make_bundle（sh+bat）
复制 engines→~/.codespot/engines、osv-db→缓存、semgrep-rules→~/.codespot/semgrep-rules、skill→~/.agents/skills/codespot（复制非软链，离线环境零外部依赖）。

### D5. 许可
THIRD-PARTY-NOTICES 列全部引擎许可与上游源码链接（TruffleHog AGPL 源码可得声明）。对外再分发合规。

## Risks / Trade-offs
- [wheel 按 py 大版本，3.9 机器装不上] → 离线包面向 python≥3.10（与主控推荐一致）；3.9 用户走在线安装的回退版本。
- [semgrep-rules 快照滞后于 registry] → 快照即发布时点规则，Release 说明标注构建日期。

## Open Questions
（无）
