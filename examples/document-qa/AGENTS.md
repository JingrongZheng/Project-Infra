# Agent 入口

先读 PROJECT.md、knowledge/index.md 和 TOOLKIT.md，再查看指定 Plan / Experiment 的脉络。看板只是这些项目文件的投影。

开始工作前必须运行 reviewer status 检查当前环境的质疑者能力。若不可用，按 docs/reviewer-integration.md 使用宿主 subagent、独立进程或其他方式完成能力握手；不得自动安装另一套 agent。无法接入时向用户说明质疑功能缺失，运行 reviewer disable 留下原因，继续其他工作。能力自检不等于正式审查；正式审查仅由 deliver <ID>（或兼容的 review --prepare）在交付点发起。

| 需要什么 | 去哪里 |
|---|---|
| 当前方案、边界及理由 | PROJECT.md |
| 已沉淀的长期知识、负面结论与适用边界 | knowledge/index.md 及其链接 |
| 共享代码、已有能力与复用边界（写实验前先查） | TOOLKIT.md |
| 实际共享实现 | shared/，或项目已有的 src/包目录；不属于任何 Experiment |
| 探索问题及综合判断 | .project/plans/ |
| 具体尝试及为什么继续或放弃 | .project/experiments/ |
| 目标与验收要求 | .project/plans/ |
| 验证命令、指标图表与其他结果展示 | .project/experiments/ |
| 论文、手册和网页 | library/index.toml |
| 质疑者初始化与往期意见 | docs/reviewer.md、Plan / Experiment Review、.project/reviews/ |
| 启动自检、接入协议与异常处理 | docs/reviewer-integration.md |
| 程序结构与操作 | README.md |
| 验证环境、依赖定位及可直接使用的命令 | docs/verification.md |
| 便携应用的当前命令行位置 | .work/infra-runtime.md（应用打开项目时更新） |
| 当前停点、等待对象及继续条件 | 对象的 Continuation 小节；临时现场补充见下项 |
| 尚未结束的现场 | .work/<对象类型>/<ID>/HANDOFF.md |

常用命令（在本工具目录运行，外部项目加 --root 路径）：

便携版不依赖系统 Python：先读 .work/infra-runtime.md，使用应用目录的 project-infra.exe 调用以下同名子命令。仅 Python 安装版可使用下面的 python -m 写法；找不到 Python 模块时不要重新安装，先确认使用的是哪种入口。

```sh
python -m project_infra reviewer status
python -m project_infra validate
python -m project_infra search "关键词"
python -m project_infra context PLAN-0001
python -m project_infra context PLAN-0001 --reviewer
python -m project_infra run EXP-0001
python -m project_infra verify EXP-0004
```

开始前检查 Git 工作区并保护用户改动，搜索已有工作。Agent 可以直接编辑文件，
编辑后运行 validate；创建对象推荐用 new，确保引用一致。
节点摘要用普通语言说明做了什么、观察到什么；详细说明留在正文。
Experiment 只保留输入、参数、共享调用与产物入口；可复用能力进入具名共享模块，不在每个实验复制实现。清理实验不删除共享能力。
Experiment 保存单次结论，Plan 综合结果。只有明确采用后才更新主干来源。
跨实验仍有价值的结论应提炼进 knowledge/，保留来源实验、证据或重跑入口与适用边界；不复制全部实验日志。当前设计写入 PROJECT.md 并引用相应知识。外部资料仍归 library/。
共享代码应从实验中抽出，放到项目级 shared/ 或已有源码包；Experiment 只导入调用。TOOLKIT.md 只索引这些真实模块，不是代码容器。
结论保留可核查的实际结果：单图、指标表、样例或文本均可，按需选择前后并排；不能编造检查、审查或实验结果。
审查者只在交付点介入，不参与方案提出或业务代码编写。
离开前把有效结论写回对象，未完成工作留下简短交接。不要依赖聊天记录。
未完成对象可用 Continuation 留一段短说明：已完成什么、还欠什么、等待谁、满足什么条件后继续或结束。有效停点保存在对象文件，.work 只补充临时现场，不复制长期结论。
历史实验的验证方式是参考，不自动成为新的验收要求。补测不能替代用户反馈或独立审查；先区分记录中的继续条件。
