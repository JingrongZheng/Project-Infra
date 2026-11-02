"""Create a clearly fictional demonstration project; never modify an existing project."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_infra.bootstrap import initialize
from project_infra.service import Service
from project_infra.store import Store

parser = argparse.ArgumentParser()
parser.add_argument('directory', type=Path)
args = parser.parse_args()
store = Store(args.directory)
if store.path('.project/config.toml').exists():
    raise SystemExit('Choose a fresh directory; an existing project will not be overwritten.')
initialize(store)
store.path('PROJECT.md').write_text('''+++
[[mainline]]
id = "goal"
section = "goal"
after = []
sources = []
[[mainline]]
id = "retrieval"
section = "retrieval"
after = ["goal"]
sources = []
[[mainline]]
id = "verification"
section = "verification"
after = ["retrieval"]
sources = []
+++

# 示例项目 · 文档问答探索

此项目用于功能展示，记录与数字均为构造的演示内容，不代表真实研究结论。

<a id="goal"></a>
## 回答必须有可核查的出处

让用户能够沿引用检查回答依据。

<a id="retrieval"></a>
## 先限定文档范围，再检查相关性

围绕检索和引用展开探索。本图中的设计与实验均是演示。

<a id="verification"></a>
## 保留可重跑的问答验证入口

让后续接手者找到验证命令、结果和未完成停点。
''', encoding='utf-8')
service = Service(store)

def update(ident, fields=None, sections=None):
    doc = service.checked()[0][ident]
    service.update(doc.path, doc.revision, fields, sections)

plan = service.create('plan', '让回答只引用当前项目的文档', anchor='PROJECT.md#retrieval')
update(plan, {'summary': '示例：先发现引用越界，再限定检索范围，并行检查漏检与引用是否准确。'},
       {'Question': '怎样在保留相关资料的同时，避免引用其他项目的文档？',
        'Scope': '演示串行、并行、分叉、汇合与结果展示，不进行真实模型评测。',
        'Acceptance criteria': '- [x] 检查文档范围\n- [x] 检查引用内容\n- [ ] 项目所有者确认候选结果',
        'Synthesis': '范围过滤与引用核查的两个分支已汇合，结果仍待确认。此为界面演示。',
        'Continuation': '演示数据已准备；等待所有者反馈。界面自检不能替代真实实验或用户验收。'})
titles = [
    '发现回答引用了其他项目的资料',
    '按项目编号限定检索文档',
    '检查过滤是否漏掉相关内容',
    '并行检查引用是否支持回答',
    '汇合漏检与引用检查的结果',
    '用完整问答流程验证候选方案',
]
created = []
for i, title in enumerate(titles):
    predecessors = [] if i == 0 else [created[0]] if i == 1 else [created[1]] if i in (2, 3) else created[2:4] if i == 4 else [created[4]]
    ident = service.create('experiment', title, plan, predecessors=predecessors)
    created.append(ident)
    update(ident, {'summary': '功能演示记录；不是实际测量或已经采纳的研究结论。', 'status': 'active'},
           {'Approach': '本节点演示一次具体尝试，复用项目已有的数据读取与核查入口。',
            'Conclusion': '演示阶段记录完成，不将构造的数据当作真实结论。'})
    if i < 5:
        update(ident, {'status': 'closed'})
assets = store.path('.project/experiments/EXP-0006.assets')
assets.mkdir()
(assets / 'demo-comparison.csv').write_text('演示数据（非实测）,基线示例,候选示例\n文档范围正确率,70%,95%\n引用支持率,65%,90%\n', encoding='utf-8')
update(created[-1], {'evidence': ['.project/experiments/EXP-0006.assets/demo-comparison.csv']},
       {'Results': '以下数字仅用于演示结果表格，不是模型实测。\n\n| 示例指标 | 基线 | 候选 |\n|---|---:|---:|\n| 文档范围正确率 | 70% | 95% |\n| 引用支持率 | 65% | 90% |',
        'Verification': '这是公开示例项目，不运行真实模型；演示数字不可用于方法比较。',
        'Continuation': '等待示例中的所有者确认，不通过补一次自检自动收口。'})
paused = service.create('plan', '比较两种长文切分方式', anchor='PROJECT.md#retrieval')
update(paused, {'status': 'paused', 'summary': '示例：先等待文档集整理完成，再继续比较。'}, {'Continuation': '等待文档输入准备好后再开展。'})
closed = service.create('plan', '尝试仅靠增加提示词限制引用', anchor='PROJECT.md#goal')
update(closed, {'status': 'closed', 'resolution': 'abandoned', 'summary': '示例：停止这条尝试，回到检索范围与引用核查。'}, {'Synthesis': '示例状态：不再投入此方向，不代表真实实验评价。'})
service.create('proposal', '后续考虑跨语言资料检索')
store.path('library/files/demo-guide.md').write_text('# 示例资料说明\n\n本文件用于展示资料索引，内容不是外部论文或真实研究依据。\n', encoding='utf-8')
store.path('library/index.toml').write_text('[[entry]]\nid = "REF-0001"\ntitle = "示例项目方法说明"\nkind = "manual"\nlocation = "files/demo-guide.md"\ntags = ["演示", "问答"]\n', encoding='utf-8')
errors = service.checked()[1]
if errors:
    raise SystemExit('\n'.join(errors))
print('Created fictional demo:', store.root)
