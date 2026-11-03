# 开发、构建与验证

## 从源码运行

需要 Python 3.11+。在仓库根目录安装命令，然后在一个独立目录初始化项目：

```powershell
python -m pip install -e .
project-infra --root '你的项目目录' init
project-infra --root '你的项目目录' serve --port 8765
```

项目数据目录和源码仓库是两个不同概念。仓库里的 examples/document-qa 是明确标注的演示项目，不含真实研究结果。

## 程序结构

软件版本只在 project_infra/__init__.py 的 __version__ 定义；Python 包动态读取它，构建脚本把同一版本写入 EXE 资源、安装器及文件名。不要覆盖旧版本 Release，使用独立 Git 分支、提交与版本标签。
便携载荷包含 build-info.json 的版本和源码指纹；安装包构建会同时检查该指纹及实际 CLI --version，拒绝用旧载荷套上新版本号。构建过程中源码变化也会被拒绝。

| 文件 | 职责 |
|---|---|
| project_infra/bootstrap.py | 新项目空白骨架与 Agent 导航模板 |
| project_infra/documents.py | Markdown / TOML 对象读写与状态定义 |
| project_infra/store.py | 路径、写锁、版本冲突与事务恢复 |
| project_infra/validation.py | 对象、前序关系、证据与设计主干校验 |
| project_infra/service.py | CLI 和界面共用的业务入口与上下文 |
| project_infra/review.py | 低频独立审查的上下文交接、空 note 和导入校验；不启动模型 |
| project_infra/web.py | 仅监听本机的服务和文件投影 |
| project_infra/desktop.py | 项目选择、自动端口、最近项目和服务生命周期 |
| project_infra/static/graph-layout.js | 实验布局、文字避让与连接路由 |
| project_infra/static/app.js | 看板、结果查看与表单编辑 |

修改共享能力，不为示例数据手调节点坐标或另写一份实现。界面和 CLI 必须使用相同校验与存储入口。
被管理项目的长期知识在 knowledge/，真实共享实现位于 shared/ 或已有源码包；TOOLKIT 只做调用索引。示例中的两个实验实际导入 shared.documents，可在示例根目录运行 python -m experiments.exp_0002 和 python -m experiments.exp_0004。知识通过 project_docs_updated / artifacts_promoted 显式关联到上下文，不整库加载。

独立质疑者由宿主 Agent 环境创建并限制权限，本程序的 review --prepare/--record 只负责交接和记录一致性。可以验证 note 非空、目标匹配和准备后项目内容未变，不能仅凭文件证明审查者身份或实际独立性。不要把指引或内容指纹当成已实施的权限沙箱。

## 自动检查

```powershell
python -m unittest discover -s tests -q
node --test tests/test_graph.cjs tests/test_routing.cjs
```

Node 只用于前端开发检查，不是桌面用户的运行依赖。测试会创建临时项目、本机服务和锁文件，需要这些操作在当前执行环境中被允许；环境阻断不算通过，也不能直接据此断定产品缺陷。

可选浏览器检查需要 Playwright 和 Edge。如果 Playwright 不在默认模块位置，设置 INFRA_PLAYWRIGHT_MODULE 指向已有安装，不要求每台机器使用相同路径。部分旧 browser_* 脚本针对本地开发现场，公开示例的录制入口见下节。

## 功能展示重现

直接启动示例项目：

```powershell
python -m project_infra --root examples/document-qa serve --port 8768
node scripts/capture_demo.cjs
```

第二条命令需要上面的浏览器测试依赖；截图写入 docs/media，帧文件写入 .work/demo-frames。只隐藏机器绝对路径，其余来自实际运行页面。示例项目和指标均为构造的演示内容。
要生成另一份演示项目，使用 `python scripts/create_public_demo.py 一个不存在的新目录`，不会覆盖已有项目。

## 打包

- Python 离线包：已有 setuptools / wheel 的环境中运行 `python scripts/build_local.py`。
- Windows 便携版：在 Windows 构建环境安装 PyInstaller，再运行 `python scripts/build_portable.py`。
- Windows 安装版：先构建便携版，然后运行 `python scripts/build_installer.py --compiler 'Inno Setup目录/ISCC.exe'`。

构建结果在 dist/，不自动发布。运行时的第三方许可在 licenses/ 与 THIRD_PARTY_NOTICES.md；重新选择运行时版本时也应更新对应许可。

安装/迁移回归：

```powershell
python -X utf8 tests/smoke_portable.py dist/project-infra-1.0.0-windows-portable.zip
python -X utf8 tests/smoke_installer.py 'Inno Setup目录/ISCC.exe'
```

安装回归会用独立测试名称、卸载身份及安装器运行锁，在临时目录实际登记安装、创建快捷方式并卸载，不覆盖正式应用。测试安装器的独立锁只用于文件安装流程测试；正式安装器仍会阻止在正式应用运行时安装或卸载。结果和日志保留在 .work 中，不提交到 Git。

## 当前边界

当前桌面安装包针对 Windows x64 构建；尚未在所有干净机器上验证。源码日常服务无第三方 Python 包依赖，原生桌面入口需要 Tk。未实现云同步、多人远程协作、画布拖线编辑；审查接入与调用边界见 reviewer-integration.md。
