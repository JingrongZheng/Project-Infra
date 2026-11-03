# 本地安装与空白项目实验

如果希望直接双击、无需命令，使用 [Windows 便携应用](portable-use.md)。本页保留原 Python 安装方式。
需要已有 Python 3.11 或更新版本。只在本地安装，不访问包索引，不发布；日常使用不需要 Node、Playwright 或开发目录。

## 安装一次

解压 project-infra-0.3.0-local.zip。使用 PowerShell 在解压目录运行：

```powershell
# 选择一个尚不存在的工具安装目录，和研究项目目录分开
powershell -NoProfile -ExecutionPolicy Bypass -File .\install-local.ps1 -Destination "$env:LOCALAPPDATA\ProjectInfra-0.3.0"
```

这里的 ExecutionPolicy Bypass 只作用于本次安装进程，不改全局设置。脚本只创建所选目录下的独立 Python 环境与命令入口，不修改 PATH 或系统 Python，也不下载依赖。若 python 未在 PATH 中，可追加 `-Python '你的python.exe完整路径'`。安装目录已存在时会停止，不覆盖已有环境。

## 在全新空目录开始

```powershell
# 先进入你准备使用的新项目目录
Set-Location '你的新项目目录'
$infra = "$env:LOCALAPPDATA\ProjectInfra-0.3.0\project-infra.cmd"
& $infra init
& $infra validate
& $infra serve --port 8765
```

浏览器打开 http://127.0.0.1:8765/，终端保留运行，Ctrl+C 停止。端口冲突时换用其他端口，例如 8767；当前开发项目的 8766 服务可以保持运行。

将新项目目录交给零背景 Agent，只说明你准备做什么，让它先读 AGENTS.md，填写 PROJECT.md，再开始探索。首次看板只有空项目入口，没有我们的开发记录、示例 Plan/Experiment、验证截图或机器路径。

以后每个项目只需要 init 一次；重复执行只补缺失文件，不覆盖已有 AGENTS.md、README.md、主干或对象。已有文件保留时需按实际项目合并必要指引；.gitignore 会补充临时文件忽略规则，不删除原规则。不自动提交 Git。

从项目子目录运行时自动向上寻找最近的 .project/config.toml；也可明确指定：

```powershell
& $infra --root '你的项目目录' validate
& $infra --root '你的项目目录' serve --port 8767
```

方向、设计和实验保存在项目目录，工具代码保存在安装目录。安装包无需放进每个项目；更新工具也不自动改写项目内容。

## 不使用安装脚本

也可自行建立独立虚拟环境，然后从本地 wheel 安装：

```powershell
python -m venv '你的安装目录\.venv'
& '你的安装目录\.venv\Scripts\python.exe' -m pip install --no-index --no-deps '.\project_infra-0.3.0-py3-none-any.whl'
& '你的安装目录\.venv\Scripts\project-infra.exe' --version
```

安装好后在项目目录使用该 project-infra.exe；激活对应虚拟环境后可直接使用 project-infra 命令。
