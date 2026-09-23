# Spec Delta

## MODIFIED Requirements

### Requirement: setup 幂等安装

setup SHALL 支持两种安装形态：平台二进制（tar.gz，M0 已有）与 npm 项目（在 `~/.codespot/engines/<name>-<version>/` 内 `npm install` 锁定版本）；单引擎安装失败 MUST 中止该引擎并继续其余引擎（逐引擎降级），最终以非零码提示存在失败项；scan 时将"未安装且被需要"的引擎记为 engine_error。

#### Scenario: 一个引擎失败不影响其余安装

- **WHEN** npm 引擎安装失败（npm 缺失）但平台二进制引擎正常
- **THEN** setup 对二进制引擎安装成功，对失败引擎打印原因并继续，整体退出码非零

#### Scenario: 重复 setup

- **WHEN** 连续执行两次 `codespot setup`（混合形态引擎）
- **THEN** 第二次的下载与 npm install 全部跳过，退出码 0

#### Scenario: 网络失败不落半成品

- **WHEN** 任一形态的安装中途失败
- **THEN** `~/.codespot/engines/` 下不残留该引擎的不完整目录，stderr 给出重试提示
