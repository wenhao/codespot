# Spec Delta

## MODIFIED Requirements

### Requirement: setup 幂等安装

setup SHALL 支持第五种安装形态来源 `--offline-dir <dir>`：venv 引擎安装改用 `pip install --no-index --find-links <dir>/wheels/<py大版本>`（离线 wheel 解析，含全部传递依赖）；平台二进制/raw/npm 形态在 offline-dir 就位时依赖 `engines/` 预置内容（跳过下载）。幂等与失败清理语义不变。

#### Scenario: 直链二进制安装

- **WHEN** 执行 `codespot setup osv-scanner`
- **THEN** 二进制从 release 直链下载、`--version` 校验通过；重复执行跳过

#### Scenario: 一个引擎失败不影响其余安装

- **WHEN** osv-scanner 安装失败但平台二进制引擎正常
- **THEN** setup 对其余引擎安装成功，对失败引擎打印原因并继续，整体退出码非零

#### Scenario: 重复 setup

- **WHEN** 连续执行两次 `codespot setup`
- **THEN** 第二次的下载步骤全部跳过，退出码 0

#### Scenario: 重复 setup 幂等

- **WHEN** 连续执行两次 `codespot setup`
- **THEN** 第二次全部跳过，退出码 0

#### Scenario: 网络失败不落半成品

- **WHEN** 任一形态的安装中途失败
- **THEN** `~/.codespot/engines/` 下不残留该引擎的不完整目录，stderr 给出重试提示

#### Scenario: 离线 wheel 安装

- **WHEN** 携带离线包的 `--offline-dir` 执行 setup（venv 引擎）
- **THEN** pip 以 `--no-index` 从 wheels 目录完成安装，无任何网络请求

#### Scenario: Windows venv 工具路径

- **WHEN** 在 Windows 上 setup venv 形态引擎（bandit/sqlfluff）
- **THEN** 安装成功且工具可从 `Scripts\` 目录解析调用
