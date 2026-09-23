# Design

## Context

方案 B（干净许可引擎组合）的第一批实施。调研依据：docs/feasibility-research.md（引擎矩阵 3.5、gitleaks 3.7、ruff 相关 3.5/3.6、并行实施路径第 6 章）。本批建立基座 + 两个 P0 引擎（gitleaks、ruff），后续批次只往 registry.json 加适配器，不改基座。

## Goals / Non-Goals

- Goals：端到端可运行的 scan→report 闭环；适配器契约成为后续并行开发的稳定接口；夹具驱动的自测。
- Non-Goals：修复循环（自动改代码 + 重扫验证，M1 的 Track F）；JS/TS、Java、SQL 引擎；`.codespot.toml` 项目配置（本批用 `.codespot/severity-overrides.json` 最小实现）；并行多引擎的复杂调度 UI。

## Decisions

### D1. 主控语言：Python 3 标准库单文件 CLI
选择 Python 而非 Node/Bash：目标用户机器上 Python 3 几乎必装，标准库足够（subprocess/concurrent.futures/json/argparse）；不需要任何 pip 依赖。主控是单入口文件 `scripts/codespot`（可执行），逻辑模块放 `scripts/` 旁（scope.py 等）以便适配器复用工具函数。**备选否决**：Bash（字符串处理与 JSON 太痛苦）、Node（要求用户先有 node 才能扫描 Python 项目，反向依赖）。

### D2. 引擎安装：用户级缓存目录 + 版本锁定
所有引擎装到 `~/.codespot/engines/<name>-<version>/`，由 registry.json 锁定版本（gitleaks 8.30.1、ruff 0.16.8 起步）。下载来源：GitHub Releases 官方二进制（gitleaks 按 OS/ARCH 选 tarball；ruff 同理）。校验：下载后执行 `--version` 验证可运行即视为成功（首版不引入 checksum 表，减少维护面；registry 预留 `checksum` 字段后续启用）。**备选否决**：包管理器安装（brew/pipx——不强制用户有且污染全局）。

### D3. 适配器契约（稳定接口，后续批次不得破坏）
```
调用:  engine_<name>.py --workdir <root> --files <list.json> --out <result.json>
成功:  退出 0，result.json = [issue, ...]（统一 schema）
失败:  退出 2，stderr 带一行可读原因
```
工具函数（读清单、写结果、脱敏）放 `scripts/engines/common.py`，适配器 import 复用。**这是并行开发的接缝**：后续引擎（Track A/C/E）只依赖本契约。

### D4. gitleaks 调用：dir 模式 + 临时聚合目录
`gitleaks dir` 只接受单路径。范围文件少于阈值（50）时逐文件调用可接受；更多时把清单文件以**符号链接**聚合到临时目录再 `dir` 一次（避免复制大文件；Windows 兼容性首版不做——本工具面向本机 darwin/linux）。退出码 1 的双义性按 spec：以报告文件可解析为准。

### D5. ruff 调用：--file-list？不，用文件参数直传
ruff 支持直接传文件路径列表（`ruff check f1.py f2.py`）且支持 `--output-format json`；文件多时注意 ARG_MAX——超过约 100 个文件改用 `ruff check .` 加 `--extend-exclude` 临时配置或分批调用（实现取分批，简单可靠）。默认规则面：`select = ["E","F","W","PL","S"]` 的精选子集写入 assets/ruff-defaults.toml，风格类（formatter 职责）不选。

### D6. 并行调度：ThreadPoolExecutor，失败隔离
适配器是子进程型任务，用 `concurrent.futures.ThreadPoolExecutor`（IO 等待为主，无需进程池）并行执行，`max_workers = min(4, 引擎数)`。单引擎异常/超时（默认 300s）捕获为 engine_error，不中断整体。合并时按 (file,line,rule) 简单去重（跨引擎几乎不会撞，保守保留）。

### D7. 报告与状态目录
输出固定 `.codespot/`（report.json/report.md/tmp/）。首版不持久化"上次扫描"状态（增量只靠 git 范围），报告每次全量重写。

### D8. severity 映射数据化
`scripts/rules-severity.json`：结构 `{"<tool>": {"default": "major", "rules": {"<rule>": "critical"}}}`。ruff 的 S 族细目与 gitleaks 全 critical 在此维护；`.codespot/severity-overrides.json` 同结构，合并时覆盖。归一化函数放 common.py。

## Risks / Trade-offs

- [GitHub 下载在网络受限环境失败] → setup 报错并提示可手动放置二进制到缓存目录（文档写明目录约定）。
- [ruff 大量文件分批调用] → 批间结果合并即可，无状态。
- [夹具中的假密钥可能触发用户机器上的其他扫描器告警] → 用明显假的 `EXAMPLE` 值 + README 注明。
- [gitleaks 符号链接聚合在极端情况下权限问题] → 降级为复制（shutil.copy2），小文件代价可接受。

## Open Questions

- ruff 默认规则面的具体 select 列表在实现时按夹具预期发现微调（不影响契约）。
