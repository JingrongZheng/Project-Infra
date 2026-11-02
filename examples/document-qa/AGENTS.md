# Agent 入口

先读 PROJECT.md 的设计主干和 TOOLKIT.md 的共享入口，再查看指定 Plan / Experiment 的脉络。

| 需要什么 | 去哪里 |
|---|---|
| 当前方案、边界及理由 | PROJECT.md |
| 共享代码、已有能力与复用边界（写实验前先查） | TOOLKIT.md |
| 探索问题及综合判断 | .project/plans/ |
| 具体尝试及为什么继续或放弃 | .project/experiments/ |
| 目标与验收要求 | .project/plans/ |
| 验证命令、指标图表与其他结果展示 | .project/experiments/ |
| 论文、手册和网页 | library/index.toml |
| 质疑者初始化与 note | docs/reviewer.md，以及 Plan Review / Experiment Review |
| 程序结构与操作 | README.md |
| 验证环境、依赖定位及可直接使用的命令 | docs/verification.md |
| 便携应用的当前命令行位置 | .work/infra-runtime.md（应用打开项目时更新） |
| 当前停点、等待对象及继续条件 | 对象的 Continuation 小节；临时现场补充见下项 |
| 尚未结束的现场 | .work/<对象类型>/<ID>/HANDOFF.md |

常用命令（在本工具目录运行，外部项目加 --root 路径）：

便携版不依赖系统 Python：先读 .work/infra-runtime.md，使用应用目录的 project-infra.exe 调用以下同名子命令。仅 Python 安装版可使用下面的 python -m 写法；找不到 Python 模块时不要重新安装，先确认使用的是哪种入口。

```sh
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
结论保留可核查的实际结果：单图、指标表、样例或文本均可，按需选择前后并排；不能编造检查、审查或实验结果。
审查者只在交付点介入，不参与方案提出或业务代码编写。
离开前把有效结论写回对象，未完成工作留下简短交接。不要依赖聊天记录。
未完成对象可用 Continuation 留一段短说明：已完成什么、还欠什么、等待谁、满足什么条件后继续或结束。有效停点保存在对象文件，.work 只补充临时现场，不复制长期结论。
历史实验的验证方式是参考，不自动成为新的验收要求。补测不能替代用户反馈或独立审查；先区分记录中的继续条件。
