# Project Infra · Ubuntu / Linux 自包含便携版

这个包已经包含 Project Infra、Python 运行时和所需 Python 模块。无需安装 Python、创建虚拟环境或运行 pip。

## 开始使用

解压整个压缩包，然后进入 `ProjectInfra` 文件夹：

```sh
tar -xzf project-infra-*-linux-x86_64-portable.tar.gz
cd ProjectInfra
./ProjectInfra
```

桌面程序会让你选择项目文件夹，并在系统默认浏览器打开看板。第一次选择空目录时，会询问是否生成项目骨架；已有文件会保留。

不要只复制单个 `ProjectInfra` 文件，旁边的 `_internal` 目录是应用的一部分。请把整个 `ProjectInfra` 文件夹放在当前用户可写的位置，例如主目录下的 `Applications`；不要放在需要 root 权限的系统目录。

如果文件管理器没有直接运行程序，可在终端执行上面的 `./ProjectInfra`。某些桌面环境还需要在文件属性中允许“作为程序执行”。

## 无图形环境

服务器、SSH 会话或容器中使用随包提供的 CLI，不需要 Tk 窗口：

```sh
./project-infra --root '/path/to/project' init
./project-infra --root '/path/to/project' serve --port 8765
```

然后在同一台机器的浏览器打开 <http://127.0.0.1:8765/>。服务只监听本机；远程访问需要由用户自行建立可信的 SSH 端口转发，本程序不会公开监听公网。

## 搬动与项目数据

退出应用后可以移动整个 `ProjectInfra` 文件夹。项目数据独立保存在你选择的项目目录中，不会藏在应用包里。最近项目记录保存在应用旁边的 `settings.json`；删除该文件只会清空最近记录，不会删除项目。

应用打开项目时会更新项目内的 `.work/infra-runtime.md`，其中记录当前包里的 CLI 路径，供 Agent 或终端使用。搬动应用后重新打开项目即可刷新。

## 平台边界

Linux 便携包必须在 Linux 上构建，不能由 Windows 包转换而来。发行文件名标明 CPU 架构；`linux-x86_64` 包不能在 ARM64 上运行。

包内包含 Python，但仍依赖目标 Linux 系统的内核、glibc 和基础桌面图形库。官方 x86_64 包以 Ubuntu 22.04 为最低构建基线，适用于 Ubuntu 22.04 及更新兼容版本；在更新系统上构建的临时包不应冒充该正式基线。

独立质疑者的项目级写保护目前只支持 Windows ACL，因此 Linux 上该能力会保持禁用；看板、CLI、初始化、实验记录和其他本地工作流不受影响。
