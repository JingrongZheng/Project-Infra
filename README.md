<p align="center"><img src="project_infra/assets/pi-monogram.svg" width="96" alt="PI 黑金圆形图标"></p>

# Project Infra

**把设计主线、探索分支和实验依据留在项目里，让人与没有聊天背景的 Agent 都能接手工作。**

Project Infra 是一个面向探索型开发、研究项目和 Vibe Coding 的本地项目工作台。Markdown / TOML 文件保存项目记录，界面从文件自动生成可编辑看板。Agent 主要编辑项目文件，人可以通过图形查看脉络、修改内容和状态，两边维护同一份信息。

[下载安装包](https://github.com/JingrongZheng/Project-Infra/releases/latest) · [安装说明](docs/install-wizard.md) · [开发与构建](docs/development.md) · [MIT 许可](LICENSE)

## 功能演示

下面的截图和动图来自实际运行的 [示例项目](examples/document-qa)。项目内容、指标和结论均为构造的演示数据，不代表真实实验或模型性能。

![Project Infra 功能演示：项目图、入线高亮、实验结果、状态看板与编号搜索](docs/media/demo.gif)

### 看清探索是如何推进的

设计主干向下展开，Plan 从对应设计分支出发。Experiment 可以串行、并行、分叉、多路汇合，再继续探索。节点仅展示名称与状态，详细过程、结论和证据点击后查看。

画布支持拖动、缩放、定位进行中的节点；悬停只高亮流入当前节点的线路。下图是示例图中一个分叉汇合区域的局部视图。

![实验分叉与汇合局部视图](docs/media/project-graph.png)

### 查看结果，不把所有实验塞进同一种模板

结果可以是单张对比图、多张图片、CSV 表格、样例、文本、视频或链接；需要时也可以采用修改前 / 修改后并排展示。结论属于具体 Experiment，Plan 综合多个实验的结果。

![实验详情与明确标注为演示数据的结果表格](docs/media/experiment-results.png)

### 用状态看板管理探索

Plan 只有进行中、暂停、已结束三个状态，各列独立滚动。尚未决定开展的想法放在方向收件箱，创建 Plan 就开始探索。搜索只匹配记录自己的编号，输入 `1` 即可找到编号 1，不会因为正文引用而匹配其他记录。

![三个状态的探索看板](docs/media/plan-board.png)

### 资料有入口，Agent 有接手路径

论文、实验手册和参考文档可放在 `library/files/`，在线资源可以只登记链接。`library/index.toml` 维护索引，放入文件后仍需由人或 Agent 登记，不自动扫描收录。

![参考资料索引](docs/media/reference-library.png)

## 下载与开始使用

### Windows 安装版

1. 在 [Releases](https://github.com/JingrongZheng/Project-Infra/releases/latest) 下载 `ProjectInfra-0.1.0-Setup.exe`。
2. 按中文向导选择安装位置，保留“创建桌面快捷方式”。
3. 双击桌面的 Project Infra，选择已有项目或一个空文件夹。
4. 空目录经确认后生成项目骨架，看板自动在系统默认浏览器中打开。

**安装包自带 Python 运行环境，使用者无需安装 Python、Node 或其他开发工具。** 当前安装包针对 Windows x64 构建，并需要可用的浏览器。软件安装位置和项目数据位置可以在不同磁盘。

下次启动会打开最近使用的有效项目。应用窗口管理本地服务，关闭它会停止服务；只关浏览器不会停止服务。服务仅监听本机，并自动选择空闲端口。

当前版本没有代码签名，Windows 可能显示未知发布者或安全提示。可用同次 Release 的 SHA-256 文件核对下载完整性；校验值不等同于发布者签名。已在开发机器测试安装、重装、卸载和目录迁移，尚未在所有全新电脑上验证。

### Windows 便携版

下载 `project-infra-0.1.0-windows-portable.zip`，解压后双击 `ProjectInfra.exe`。移动时携带整个文件夹，包括 `_internal`。见 [便携说明](docs/portable-use.md)。

## 项目内容放在哪里？

```text
你的项目/
├── AGENTS.md                    Agent 导航和接手入口
├── PROJECT.md                   当前设计与设计主干
├── TOOLKIT.md                   本项目共享代码和工具索引
├── .project/
│   ├── plans/                   探索问题、范围、验收与综合判断
│   └── experiments/             具体尝试、前序、结果与结论
├── library/
│   ├── index.toml               资料索引
│   └── files/                   论文、手册等本地资料
├── docs/                        审查和验证指引
└── .work/                       临时现场与运行入口，不作为长期知识
```

代码、数据集与共享实现由项目自行组织。Experiment 的代码应保持输入、参数、共享调用和产物入口的薄层，可复用能力进入项目现有共享模块；TOOLKIT 只是文件索引，不是额外看板。

项目记录留在项目目录，卸载软件不会删除它们。安装包不包含作者的开发现场或你的个人项目。

## 零背景 Agent 如何接手？

把项目目录和实际工作目标交给 Agent，让它先读 `AGENTS.md`，再沿设计主干、Plan 和 Experiment 按需深入。命令行 `context` 可汇集相关脉络和接续说明；未完成对象可用简短 `Continuation` 写清已完成内容、等待对象及继续条件。

便携或安装版会在打开项目时更新 `.work/infra-runtime.md`，供 Agent 定位配套命令行入口。程序不自动调用模型；独立质疑者只在收口检查点按需介入，自动测试、用户验收与独立审查分开记录。

文件编辑和界面编辑共享校验，陈旧写入会被拒绝，错误文件会显示诊断。验证入口可以保留可重跑命令，但历史实验的验证方法不自动变成后来实验的新验收要求。

## 从源码运行、测试与构建

需要 Python 3.11+：

```powershell
python -m pip install -e .
project-infra --root '你的项目目录' init
project-infra --root '你的项目目录' serve --port 8765
```

示例项目可以直接运行：

```powershell
python -m project_infra --root examples/document-qa serve --port 8768
```

开发检查、演示重现、便携包和安装包构建见 [开发文档](docs/development.md)。日常服务没有第三方 Python 包依赖；Node / Playwright 是可选的前端开发测试工具。

## 当前边界

- 本地文件工作台；没有云同步或多人远程协作服务。
- 界面和文件可以编辑关系，尚不支持在画布上拖线编辑。
- 不自动执行 Agent、安排模型任务或代替独立审查。
- 图片、资料、验证命令与接续说明需要实际维护，系统不会自动补全研究结论。

## 许可

本项目代码与 PI 字标采用 [MIT License](LICENSE)。第三方组件保留各自许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
