from pathlib import Path
from .documents import KINDS, template


AGENTS = '''# Agent 入口

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
| 目标与验收要求 | .project/plans/ |\n| 验证命令、指标图表与其他结果展示 | .project/experiments/ |
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
'''

REVIEWER = '''# 质疑者初始化

你是未参与本次方案制定与业务实现的独立审查会话。你可以使用与执行者相同的模型；不接续执行者对话，通过项目文件了解背景。
只审查，不提出替代实施方案，不修改业务代码。先读交接 context.md，再按需读取设计主干、知识、共享实现、资料、实验及证据。

质疑者仅在显式交付检查点介入，不在每个 Experiment 后调用。启动时的能力握手不是正式审查。
先看 Plan / Experiment 的 Review 和 .project/reviews/<ID>/ 中往期意见。新一轮说明复核了哪些旧问题、证据是什么、哪些仍未解决；不要用沉默表示问题已解决。

重点检查假设与证据、真实运行路径、数据泄露、评价污染、绕过测试或假完成，按适用情况执行端到端检查、负例、lint 或构建。检查全绿不自动证明方法成立。
问题应有证据，不要求凑数量；没有发现问题时可以明确说明未发现，并记录检查范围。没有检查的内容明确写出。

输出简短 note：Reviewer: 署名；随后使用二级标题“已核查”“主要疑点”“未覆盖与下一步”。前两节必须填写。
执行者负责处理意见。审查意见不等于通过，不自动关闭对象或采用设计。

接入方式不限 subagent 或独立进程，见 docs/reviewer-integration.md。宿主/适配器负责建立独立会话并配置读写权限；普通进程隔离不自动提供文件权限隔离。程序不证明审查者诚实或验证思考质量。
本轮临时目录在 .work/reviews/；成功导入后原始笔记长期保存在 .project/reviews/，并追加到对象 Review，不能用下一轮覆盖上一轮。
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
knowledge/ 保存跨实验可复用的结论与边界，并链接来源实验；shared/ 或已有源码包保存真实共享代码，experiments/ 只保留薄调用入口。两者都独立于某个 Experiment。
启动时先运行 reviewer status 并按 docs/reviewer-integration.md 完成当前环境能力自检。交付时运行 deliver <ID>；进程适配器会自动执行，宿主模式返回交接目录。未接入时明确记录未执行独立审查，不显示为通过。成功意见追加到 Review，原始各轮意见保存在 .project/reviews/；不会覆盖往期。程序不自带模型，权限由所选宿主或适配器落实。
验证入口见 docs/verification.md，质疑者指引见 docs/reviewer.md。
未完成工作的停点写在对象 Continuation 中；.work 只存临时现场。

重复 init 只补缺失文件，不覆盖现有项目文件。已有 AGENTS.md 会保留，需人工或 Agent 将必要导航合并进去。
更新安装包与初始化项目相互独立，不自动改写项目记录。
'''


REVIEWER_INTEGRATION = '''# 质疑者接入与启动自检（v0.3.0）

Project Infra 不包含 Agent。它管理能力握手、交付检查点、异常与多轮意见；实际会话由你已有的工具提供，不限定模型、厂商、subagent 或独立进程。

## 启动时：能力自检

执行者读 AGENTS.md 后先运行 `project-infra reviewer status`。便携/安装版的命令路径见项目 `.work/infra-runtime.md`；Python 安装版可使用 `python -m project_infra` 替代 `project-infra`。外部项目统一加 `--root 项目路径`。

未自检时默认关闭质疑功能，看板持续提示。不要因此自行安装另一个 Agent。可接入时选择下列任意一种方式；不能接入则运行 `project-infra reviewer disable --reason "当前工具无法创建独立会话"` 并告诉用户。

能力记录在 `.work/reviewer/runtime.json`，不作为可迁移的项目事实。工作台服务重新打开会重置能力；机器、用户、项目路径或程序入口变化时不复用旧结果。成功结果有效 8 小时，过期后重检。命令行操作自身不创建新工作台会话；请先启动工作台，再让执行者自检。

### 方式一：宿主 subagent / 自己管理的独立会话

```sh
project-infra reviewer probe --label "当前执行环境" --timeout 600
```

返回 `.work/reviewer/probes/<编号>/request.json` 以及建议的 response 路径。执行者使用宿主自身的能力，把 request 交给一个未参与本次方案和实现的独立会话。该会话只确认可接收上下文和返回意见，此时不要展开正式方案审查。响应为 UTF-8 JSON：

```json
{"nonce":"request 中的 nonce", "independent":true, "session":"新建会话的标识"}
```

将响应保存到 response.json 后执行：

```sh
project-infra reviewer accept --response .work/reviewer/probes/<编号>/response.json
```

程序检查请求对应关系、独立能力声明与超时，成功后开启质疑功能。这是接入能力握手，不是身份认证，也不证明审查质量或声明真实性。宿主应使用自己的工具实际创建独立会话，不应由执行者代替它返回响应。

### 方式二：独立进程适配器

在本机准备 JSON 文件，内容是适配器的参数数组，不能是 shell 命令字符串。例如：

```json
["D:/已有工具/reviewer-adapter.exe", "--profile", "review-only"]
```

然后运行：

```sh
project-infra reviewer check --label "本机审查工具" --command-file D:/本机配置/reviewer-command.json --timeout 600
```

程序实际启动适配器并进行能力握手。适配器负责调用你已有的 Agent 工具；它可以直接是支持协议的可执行文件，也可以是现有语言环境运行的包装脚本。不要求额外安装特定工具。HTTP 界面不能设置命令，只有本机命令行能配置。配置仅保留在当前项目的 .work 运行现场，不提交机器路径。

适配器协议：每次调用创建独立进程，工作目录为项目根目录；stdin 是一个 UTF-8 JSON 对象，stdout 只返回一个 JSON 对象，诊断写 stderr。程序保留 stdout.log / stderr.log。

自检输入：`{"action":"probe","nonce":"…","project":"项目绝对路径","instruction":"…"}`。输出与宿主模式相同：nonce、independent=true、session。

正式审查输入：`{"action":"review","id":"PLAN-0001","project":"…","context":"完整交接上下文","handoff":"本轮临时目录"}`。输出：`{"note":"Reviewer: …\\n\\n## 已核查\\n…\\n\\n## 主要疑点\\n…\\n\\n## 未覆盖与下一步\\n…"}`。

每次正式审查必须新建一个未参与方案制定与实现的会话，不能恢复执行者的对话。适配器可复用登录状态和模型。原进程只输出意见，由 Project Infra 保存；不要让模型直接修改项目记录。文件写权限由选定工具/宿主实际配置，普通独立进程不自动限制文件访问。

## 交付时：才启动正式审查

```sh
project-infra deliver PLAN-0001
```

也支持显式审查某个 Experiment。看板对象详情的“发起交付审查”调用同一个入口。兼容 `review <ID> --prepare`，该命令本身也表示显式交付审查请求；普通 context、run、verify、新建实验不会启动质疑者。

- 进程模式：程序启动已配置适配器，传入上下文，等待结果并导入。
- 宿主模式：返回 `.work/reviews/<ID>/<本轮>/`；宿主新建独立审查会话阅读 context.md，填写 NOTE.md，然后执行 `review <ID> --record <NOTE相对项目路径>`。程序不直接控制宿主 subagent 的生命周期，无法替宿主强行终止它，但会拒绝超时回传。
- 能力缺失：不调用审查者，Delivery 明确写“未执行独立审查：原因”；其他工作继续。界面仍显示功能关闭，不能将降级等同于通过。

同一对象不能重复并发发起待完成审查。需要取消时先 `reviewer disable --reason "取消本轮"`，重新接入后再发起。

## 异常与关闭

进程超时会终止本次启动的进程树；异常退出、无效输出、空白 note、错误目标、能力重置、超时回传或源码变化均不能导入为完成。错误时保留临时现场；执行失败关闭质疑功能，需重新自检。宿主模式超时由本地状态查询和导入检查发现，程序不声称能终止外部 subagent。

只有能力启用时，非放弃 Plan 的关闭才要求当前内容对应的本轮交接记录。先保存候选方案、发起审查，再按原有要求 verify、最后 close；关闭时不能同时修改候选内容。修改后需要重新审查。意见内容是否足够、方案是否采纳由用户/执行者判断，程序不评判思考质量，也不验证审查者诚实。

能力关闭时允许结束 Plan，但程序自动写入未执行独立审查的 Delivery。普通 Experiment 结束和放弃 Plan 不强制审查，避免每个实验都调用。已有关闭对象不会被升级自动重新审查；重新打开后按当前流程处理。

Agent 仍可以直接编辑文件；这里的硬性控制作用于程序的 CLI/Web 操作，不是针对本地文件写入的安全系统。validate 检查对象结构与结论记录，不证明记录真实。

## 往期意见

每轮成功意见追加到 Plan / Experiment 的 Review；原始 note 和时间、来源指纹、轮次元数据原子写入 `.project/reviews/<ID>/`，建议随项目 Git 提交。这是附属审查记录，不增加工作对象或状态。

reviewer 上下文包括相关对象的历轮意见与原始记录路径。新一轮注明复核哪条旧意见及结果，不自动让旧问题消失，不把多轮判断改写成一个“合并结论”。v0.2 的已有 Review 会保留，新轮次从其后追加。尚未导入的 .work note 只是现场，清理前先导入有效意见。

## 从 v0.2 升级

软件升级不覆盖项目。运行 init 会补齐缺失接入指南，但已有 AGENTS.md、README.md、reviewer.md 保留；将本指南的启动自检导航合并进去。无需新增模型账号或改变现有共享代码结构。schema_version 仍为 2；旧关闭记录仍兼容。

测试中的 tests/reviewer_fixture.py 只是协议夹具，不调用模型，不能用它代表真实质疑者或研究结论。
'''


def initialize(store):
    root = store.root
    root.mkdir(parents=True, exist_ok=True)
    for directory in ('.project', '.project/templates', '.work', 'library/files', 'docs', 'knowledge', 'shared', 'experiments'):
        store.path(directory).mkdir(parents=True, exist_ok=True)
    files = {'AGENTS.md': AGENTS, 'docs/reviewer.md': REVIEWER, 'docs/reviewer-integration.md': REVIEWER_INTEGRATION, 'README.md': STARTER_README,
             'knowledge/index.md': '# 项目知识\n\n在此链接经过提炼、值得跨实验复用的知识文档。每份知识写清结论、适用边界及来源实验/证据，按需提供重跑入口；有价值的负面结论同样可以沉淀。\n不保存全部实验流水账，不另设历史层或知识状态机。当前采用的设计仍由 PROJECT.md 维护，外部论文和手册放 library/。\n',
             'shared/README.md': '# 项目级共享实现\n\n此目录存放按能力命名的真实代码与工具文件，生命周期独立于 Experiment。若项目已有 src/ 或可安装包，优先在那里复用，不复制第二套实现。\nTOOLKIT.md 索引实际模块与调用方法；实验入口放 experiments/ 或现有实验目录，直接导入共享模块。不要让共享模块反向依赖某个实验目录。空项目没有业务实现，需要由项目按所用语言补入。\n',
             'experiments/README.md': '# 实验入口\n\n这里放输入、配置、共享调用与产物保存等薄入口；记录仍在 .project/experiments/。不要把整份项目实现复制到每次实验里。共享逻辑进入 shared/ 或现有源码包，再通过正常模块导入或项目构建调用。\n',
             'docs/verification.md': '# 验证入口\n\n在本项目填写现有运行环境、依赖定位、工作目录、验证命令和所需服务。机器专属路径不要当成其他机器的默认值。\n先定位已有依赖；默认导入失败不等于未安装，不自动安装或升级。\n区分断言失败、环境阻断与未执行；阻断不证明功能通过或没有缺陷。历史测试数量与验证方式不是新的验收要求，收口条件以当前对象为准。\n',
             'TOOLKIT.md': '# 共享代码与工具索引\n\n真实代码放在项目级 shared/ 或已有 src/包目录，本文件只记录模块路径和导入/调用方式。不要把共享实现留在某个 Experiment 下，也不要在这里用 Markdown 代替代码。\n写实验前先查已有的数据处理、评价、绘图和验证入口；实验只保留输入、参数、共享调用与产物保存。\n清理实验不能删除被其他实验或项目代码使用的共享能力。\n',
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
