from pathlib import Path
from .documents import KINDS, template


AGENTS = '''# Agent 入口

先读 PROJECT.md、knowledge/index.md 和 TOOLKIT.md，再查看指定 Plan / Experiment 的脉络。看板只是这些项目文件的投影。

| 需要什么 | 去哪里 |
|---|---|
| 当前方案、边界及理由 | PROJECT.md |
| 已沉淀的长期知识、负面结论与适用边界 | knowledge/index.md 及其链接 |
| 共享代码、已有能力与复用边界（写实验前先查） | TOOLKIT.md |
| 实际共享实现 | shared/，或项目已有的 src/包目录；不属于任何 Experiment |
| 探索问题及综合判断 | .project/plans/ |
| 具体尝试及为什么继续或放弃 | .project/experiments/ |
| 目标与验收要求 | .project/plans/ |\n| 验证命令、指标图表与其他结果展示 | .project/experiments/ |
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
跨实验仍有价值的结论应提炼进 knowledge/，保留来源实验、证据或重跑入口与适用边界；不复制全部实验日志。当前设计写入 PROJECT.md 并引用相应知识。外部资料仍归 library/。
共享代码应从实验中抽出，放到项目级 shared/ 或已有源码包；Experiment 只导入调用。TOOLKIT.md 只索引这些真实模块，不是代码容器。
结论保留可核查的实际结果：单图、指标表、样例或文本均可，按需选择前后并排；不能编造检查、审查或实验结果。
审查者只在交付点介入，不参与方案提出或业务代码编写。
离开前把有效结论写回对象，未完成工作留下简短交接。不要依赖聊天记录。
未完成对象可用 Continuation 留一段短说明：已完成什么、还欠什么、等待谁、满足什么条件后继续或结束。有效停点保存在对象文件，.work 只补充临时现场，不复制长期结论。
历史实验的验证方式是参考，不自动成为新的验收要求。补测不能替代用户反馈或独立审查；先区分记录中的继续条件。
'''

REVIEWER = '''# 质疑者初始化

你负责理解并审查候选方案及实际实现，不提出替代实施方案，不修改业务代码。
允许读取主干、Plan、Experiment、Library、代码和证据，执行检查并更新审查记录。
只有到交付检查点才调用你，不在每个实验后介入。
可以读取 knowledge/、shared/ 或项目已有源码包。你只审查，不参与本次方案提出或业务实现。

先运行 `python -m project_infra context <ID> --reviewer`，浏览主干与实验脉络，
读取 Plan Review 或 Experiment Review 中上次 note，然后按需展开文件。
需要完整引用正文时使用 context --full；不要重复加载全部资料。

重点检查：假设与证据是否相符、真实路径是否运行、测试是否被绕过、
数据划分和预处理是否泄露、评价是否污染、前后展示是否可比。
选择适用的端到端测试、负例、lint 或构建。检查全绿不自动证明方法成立。
未检查的内容明确写出；问题必须有代码、实验或执行结果支持，不凑问题数量。

记录直接写在 Plan Review 或 Experiment Review，不另建系统。
Review 只记录实际独立审查，普通自检写在 Verification，不自动显示审查标记。

- 已看到：本次覆盖的节点和改动。
- 当前理解：候选方案与关键前提。
- 已核查：实际证据及结果。
- 主要疑点：对结论或验收的影响。
- 下次关注：尚未覆盖、需要定向复核的部分。

先记录实质问题，再停止本轮工作。执行者负责修改；下次只复核相关变化。
这份文件与 note 支持会话恢复，不意味着工具已自动调用任何模型。
具体交接：执行者运行 review <ID> --prepare，得到上下文与空白 NOTE；宿主在独立 subagent 中使用该上下文，并将业务目录设为只读、只允许写 NOTE。审查者填好简短 note 后，执行者用 review <ID> --record <NOTE路径> 写回对象。
本工具提供交接与导入校验，不是模型调度器；独立会话和操作系统级读写隔离必须由宿主 Agent 环境实施，单靠提示词不构成强制权限隔离。
'''

STARTER_README = '''# 项目工作台

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
验证入口见 docs/verification.md，质疑者指引见 docs/reviewer.md。
未完成工作的停点写在对象 Continuation 中；.work 只存临时现场。

重复 init 只补缺失文件，不覆盖现有项目文件。已有 AGENTS.md 会保留，需人工或 Agent 将必要导航合并进去。
更新安装包与初始化项目相互独立，不自动改写项目记录。
'''


def initialize(store):
    root = store.root
    root.mkdir(parents=True, exist_ok=True)
    for directory in ('.project', '.project/templates', '.work', 'library/files', 'docs', 'knowledge', 'shared', 'experiments'):
        store.path(directory).mkdir(parents=True, exist_ok=True)
    files = {'AGENTS.md': AGENTS, 'docs/reviewer.md': REVIEWER, 'README.md': STARTER_README,
             'knowledge/index.md': '# 项目知识\n\n在此链接经过提炼、值得跨实验复用的知识文档。每份知识写清结论、适用边界及来源实验/证据，按需提供重跑入口；有价值的负面结论同样可以沉淀。\n不保存全部实验流水账，不另设历史层或知识状态机。当前采用的设计仍由 PROJECT.md 维护，外部论文和手册放 library/。\n',
             'shared/README.md': '# 项目级共享实现\n\n此目录存放按能力命名的真实代码与工具文件，生命周期独立于 Experiment。若项目已有 src/ 或可安装包，优先在那里复用，不复制第二套实现。\nTOOLKIT.md 索引实际模块与调用方法；实验入口放 experiments/ 或现有实验目录，直接导入共享模块。不要让共享模块反向依赖某个实验目录。空项目没有业务实现，需要由项目按所用语言补入。\n',
             'experiments/README.md': '# 实验入口\n\n这里放输入、配置、共享调用与产物保存等薄入口；记录仍在 .project/experiments/。不要把整份项目实现复制到每次实验里。共享逻辑进入 shared/ 或现有源码包，再通过正常模块导入或项目构建调用。\n',
             'docs/verification.md': '# 验证入口\n\n在本项目填写现有运行环境、依赖定位、工作目录、验证命令和所需服务。机器专属路径不要当成其他机器的默认值。\n先定位已有依赖；默认导入失败不等于未安装，不自动安装或升级。\n区分断言失败、环境阻断与未执行；阻断不证明功能通过或没有缺陷。历史测试数量与验证方式不是新的验收要求，收口条件以当前对象为准。\n',
             'TOOLKIT.md': '# 共享工具包\n\n写实验前先搜索并复用已有共享实现，在这里列出项目包、数据处理、评价、绘图及验证入口。\nExperiment 只保留输入、参数、共享调用与产物保存。通用逻辑进入按能力命名的共享模块，不在每个实验复制一份。\n清理实验不能删除被其他实验或项目代码使用的共享能力。\n',
             'PROJECT.md': '+++\nmainline = []\n+++\n\n# 项目设计主干\n\n填写项目目标、当前总体方案、选择理由和未解决问题。\n',
             '.project/config.toml': 'schema_version = 2\n', 'library/index.toml': 'entry = []\n'}
    for kind, (prefix, folder) in KINDS.items():
        store.path(f'.project/{folder}').mkdir(exist_ok=True)
        files[f'.project/templates/{kind}.md'] = template(kind, prefix + '-0000', '填写标题')
    created = []
    for path, text in files.items():
        p = store.path(path)
        if not p.exists():
            p.write_text(text, encoding='utf-8')
            created.append(path)
    ignore = store.path('.gitignore')
    original = ignore.read_text(encoding='utf-8') if ignore.exists() else ''
    entries = ['.work/', '__pycache__/', '*.pyc', '.project/.write.lock', '.project/transaction.json', '*.infra-tmp']
    missing = [e for e in entries if e not in original.splitlines()]
    if missing:
        ignore.write_text(original.rstrip() + '\n' + '\n'.join(missing) + '\n', encoding='utf-8')
    return created
