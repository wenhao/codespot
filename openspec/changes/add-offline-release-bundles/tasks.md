# Tasks

- [x] 1. make_bundle.py：载荷+引擎+wheels（pip download 3.10/3.11）+OSV 库+semgrep-rules 克隆+NOTICES+install 脚本+MANIFEST+归档；验证：本地构建 darwin-x64 包
- [x] 2. setup --offline-dir（wheel --no-index 安装）+ engine_semgrep 离线规则回退（按语言子目录）；验证：离线包重装后五引擎零网络语义扫描零错误
- [x] 3. release.yml：四平台矩阵构建+离线冒烟+Release 发布；验证：tag 触发后 Release 资产齐全
- [x] 4. README 英中 Offline release 章节 + 许可边界更新；验证：文档一致
