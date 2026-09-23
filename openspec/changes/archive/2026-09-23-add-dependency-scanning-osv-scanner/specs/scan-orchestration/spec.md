# Spec Delta

## MODIFIED Requirements

### Requirement: setup 幂等安装

setup SHALL 支持第四种安装形态 `raw_binary`：直接下载单文件二进制（URL 直链 release 资产，按 os/arch 映射）到 `~/.codespot/engines/<name>-<version>/<name>` 并加执行位；幂等与失败清理语义不变。

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
