# Python / 源码安装与空白项目实验

普通 Ubuntu 用户应优先使用[自包含 Linux 便携版](linux-portable-use.md)：它自带 Python，解压即可运行。本页保留面向开发者、源码调试和自定义 Python 环境的安装方式，需要 Python 3.11 或更新版本。

本地 wheel 包支持 Windows 和 Ubuntu / Linux。安装脚本只在指定目录创建独立 Python 环境与命令入口，不修改 `PATH` 或系统 Python，也不访问包索引。

如果希望在 Windows 直接双击、无需系统 Python，使用 [Windows 便携应用](portable-use.md)。

本地 ZIP 由维护者运行 `python scripts/build_local.py` 生成；它与自带 Python 的便携包不同，适合已经管理 Python 环境的开发者。

## Ubuntu / Linux 准备

Ubuntu 需要 Python、`venv` 和可用的浏览器：

```sh
sudo apt update
sudo apt install python3 python3-venv
```

只有使用可选的桌面项目选择器时才需要 Tk：

```sh
sudo apt install python3-tk
```

解压 `project-infra-1.0.0-local.zip`，在解压目录运行：

```sh
sh ./install-local.sh "$HOME/.local/opt/ProjectInfra-1.0.0"
```

安装目录必须尚不存在，脚本不会覆盖已有环境。若 `python3` 不是目标解释器，可把解释器作为第二个参数传入：

```sh
sh ./install-local.sh "$HOME/.local/opt/ProjectInfra-1.0.0" /usr/bin/python3
```

## Windows 准备

解压同一个本地包，使用 PowerShell 在解压目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-local.ps1 -Destination "$env:LOCALAPPDATA\ProjectInfra-1.0.0"
```

这里的 `ExecutionPolicy Bypass` 只作用于本次安装进程，不改全局设置。若 `python` 未在 `PATH` 中，可追加 `-Python '你的python.exe完整路径'`。

## 在全新空目录开始

Ubuntu / Linux：

```sh
mkdir -p "$HOME/projects/my-project"
cd "$HOME/projects/my-project"
infra="$HOME/.local/opt/ProjectInfra-1.0.0/project-infra"
"$infra" init
"$infra" validate
"$infra" serve --port 8765
```

Windows PowerShell：

```powershell
Set-Location '你的新项目目录'
$infra = "$env:LOCALAPPDATA\ProjectInfra-1.0.0\project-infra.cmd"
& $infra init
& $infra validate
& $infra serve --port 8765
```

浏览器打开 <http://127.0.0.1:8765/>，终端保留运行，按 `Ctrl+C` 停止。端口冲突时换用其他端口。服务只监听本机。

将新项目目录交给零背景 Agent，只说明你准备做什么，让它先读 `AGENTS.md`，填写 `PROJECT.md`，再开始探索。首次看板只有空项目入口，没有开发记录、示例 Plan / Experiment、验证截图或机器路径。

以后每个项目只需要 `init` 一次；重复执行只补缺失文件，不覆盖已有 `AGENTS.md`、`README.md`、主干或对象。已有文件保留时需按实际项目合并必要指引；`.gitignore` 会补充临时文件忽略规则，不删除原规则。不自动提交 Git。

从项目子目录运行时自动向上寻找最近的 `.project/config.toml`；也可明确指定：

```sh
"$infra" --root '/path/to/project' validate
"$infra" --root '/path/to/project' serve --port 8767
```

方向、设计和实验保存在项目目录，工具代码保存在安装目录。安装包无需放进每个项目；更新工具也不自动改写项目内容。

## 可选桌面项目选择器

Ubuntu 安装 `python3-tk` 后可运行：

```sh
"$HOME/.local/opt/ProjectInfra-1.0.0/project-infra-desktop"
```

它提供与 Windows 桌面版相同的项目文件夹选择、自动初始化和浏览器打开流程。若当前是无图形界面的服务器、SSH 会话或容器，请直接使用 `project-infra serve`，不要使用桌面入口。

## 不使用安装脚本

也可自行建立独立虚拟环境，然后从本地 wheel 安装。Ubuntu / Linux 示例：

```sh
python3 -m venv '/path/to/install/.venv'
'/path/to/install/.venv/bin/python' -m pip install --no-index --no-deps './project_infra-1.0.0-py3-none-any.whl'
'/path/to/install/.venv/bin/project-infra' --version
```

Windows 中对应入口位于 `.venv\Scripts\project-infra.exe`。激活虚拟环境后，两端均可直接使用 `project-infra` 命令。

## Python 安装版的 Ubuntu 边界

看板、CLI、项目初始化和本地桌面选择器支持 Ubuntu。独立质疑者的项目级写保护目前依赖 Windows ACL，因此 Ubuntu 上 `reviewer probe/check` 会明确拒绝启用；其他功能可以继续使用，并应以 `reviewer disable --reason "Ubuntu 当前不支持审查写保护"` 记录本次降级。不要把未执行独立审查写成审查通过。
