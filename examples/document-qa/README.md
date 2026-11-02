# 项目工作台

本目录保存项目自己的设计与探索记录，Project Infra 程序安装在项目之外。
便携版日常使用：双击应用目录中的 ProjectInfra.exe，选择本目录，自动打开看板。无需执行以下终端命令，也不需要系统 Python。Agent 命令入口见 .work/infra-runtime.md，由应用启动时更新。
先让 Agent 阅读 AGENTS.md，结合你的实际目标填写 PROJECT.md，再按需要建立 Proposal、Plan 和 Experiment。
方向尚未决定开展时保留 Proposal；创建 Plan 即开始探索。空项目没有演示数据或预设实验。

在本目录运行（未激活安装环境时使用安装目录内 project-infra.cmd 的完整路径）：

```sh
project-infra validate
project-infra serve --port 8765
```

在浏览器打开 http://127.0.0.1:8765/。端口被占用时换一个端口，不要终止未知服务。
从项目子目录运行会向上寻找最近的 .project/config.toml；也可显式指定 project-infra --root 项目目录 serve。
每个看板对应一个项目，多个项目使用不同端口。

创建记录示例（编号以命令实际输出为准，不要求预先有这些记录）：

```sh
project-infra new proposal --title "待考虑的方向"
project-infra new plan --title "开始探索一个问题"
project-infra new experiment --plan PLAN-0001 --title "一次具体尝试"
project-infra context PLAN-0001
```

PROJECT.md 保存正式采用的设计主干；TOOLKIT.md 索引本项目实际共享代码，不复制工具自身源码。
knowledge/ 保存跨实验可复用的结论与边界，并链接来源实验；shared/ 或已有源码包保存真实共享代码，experiments/ 只保留薄调用入口。两者都独立于某个 Experiment。
需要收口审查时，使用 review <ID> --prepare 生成交接目录，由宿主启动独立 subagent 审查；填好 NOTE 后用 review <ID> --record <NOTE路径> 导入。程序不会自动运行模型或替宿主建立只读沙箱。
验证入口见 docs/verification.md，质疑者指引见 docs/reviewer.md。
未完成工作的停点写在对象 Continuation 中；.work 只存临时现场。

重复 init 只补缺失文件，不覆盖现有项目文件。已有 AGENTS.md 会保留，需人工或 Agent 将必要导航合并进去。
更新安装包与初始化项目相互独立，不自动改写项目记录。
