# Tasks

- [x] 1. registry：windows os/arch/ext 映射（gitleaks zip x64、ruff/oxlint zip x86_64-pc-windows-msvc、trufflehog zip amd64、osv raw .exe、PMD/SpotBugs windows_binary）+ semgrep platforms；验证：macOS 本地 setup 全绿不受影响
- [x] 2. setup_engine：IS_WINDOWS 分支（venv python/Scripts、wrapper .bat、raw .exe）+ resolve_engine_cmd 统一解析；八个适配器 find_* 换用；验证：macOS selftest 全绿
- [x] 3. 调度与 selftest 的 platforms 过滤 + stdout 提示；engine_java 的 cmd /c 与 file:///C:/ 修复；验证：spec 场景逻辑复核
- [x] 4. GitHub Actions windows-latest（setup+selftest+冒烟）；验证：push 后 Actions 绿灯
- [x] 5. README 英中 Windows 安装与平台说明更新；验证：文档一致
