# Windows 安装向导试用

双击 dist/ProjectInfra-0.2.0-Setup.exe，按中文向导完成安装。

1. 阅读说明，选择软件安装位置。默认位于当前用户的 LocalAppData\Programs\ProjectInfra，可改为其他可写目录。
2. 保持“创建桌面快捷方式”勾选，点击安装。
3. 完成后启动软件，选择你的项目目录。项目可以在任何其他磁盘；新空目录会在确认后生成项目骨架。
4. 以后双击桌面“Project Infra”即可，最近项目会自动打开。软件窗口负责服务，看板在浏览器显示。
5. 若要卸载，先关闭软件窗口及其命令行服务，再打开 Windows“设置 → 应用 → 已安装的应用”，找到 Project Infra 并卸载。

安装与日常使用不需要另装 Python、Node，不修改 PATH。安装目录和项目目录独立；向导不允许直接装到已经初始化的项目根目录。
卸载仅删除安装程序登记的软件文件、快捷方式及卸载登记，不遍历删除项目目录。最近项目设置会保留，便于重装后继续使用；保留设置不代表安装目录中还留有完整软件。

本地测试包尚未做代码签名，Windows 可能显示未知发布者。这与用于构建的 Inno Setup 编译器自身签名不同。
当前包针对 Windows x64 构建；其他操作系统不适用。

## 建议本次实验

先选一个新的测试项目目录，确认安装位置与项目位置不同；从桌面快捷方式打开，初始化并创建一条 Plan，关闭后再次打开确认记录仍在。
需要验证卸载时，先停止软件，再通过 Windows 设置卸载，检查该项目目录与记录仍在。把遇到的提示、卡住的步骤或异常发回即可。

## 构建和验证入口

安装包复用便携版程序，脚本为 installer/ProjectInfra.iss；先通过 scripts/build_portable.py 构建干净程序，再运行：

```powershell
python scripts/build_installer.py --compiler 'Inno Setup 编译器目录\ISCC.exe'
python -X utf8 tests/smoke_installer.py 'Inno Setup 编译器目录\ISCC.exe'
```

smoke_installer 用独立测试名称登记安装、创建临时快捷方式，并在最后卸载清理；不会占用正式 Project Infra 的卸载身份。测试项目和日志保留在 .work/installer-check-*。
向导由 [Inno Setup](https://jrsoftware.org/isdl.php) 构建，简体中文语言文件来自其[翻译页面](https://jrsoftware.org/files/istrans/)，原文件保留维护者说明。
