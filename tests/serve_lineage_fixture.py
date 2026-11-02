"""Disposable UI fixture, clearly separate from real project records."""
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_infra.bootstrap import initialize
from project_infra.store import Store
from project_infra.service import Service
from project_infra.web import serve

scratch = Path(__file__).resolve().parents[1] / '.work' / 'tests'
scratch.mkdir(parents=True, exist_ok=True)
store = Store(tempfile.mkdtemp(prefix='lineage-ui-', dir=scratch))
initialize(store)
service = Service(store)
project = store.read('PROJECT.md')
service.update('PROJECT.md', project.revision, raw='''+++
[[mainline]]
id = "design"
section = "design"
after = []
sources = []
+++

# 测试夹具 · 探索分叉与汇合

以下节点为交互测试样例，不代表真实研究结论。

<a id="design"></a>
## 当前设计

从主干展开探索，允许接续、分叉和多路汇合，不要求产生 Task。
''')
plan = service.create('plan', '示例：验证一个抽象思路的不同方面', anchor='PROJECT.md#design')
a = service.create('experiment', 'A · 验证数据是否可用', plan)
b = service.create('experiment', 'B · 并行检查评价方式', plan)
c = service.create('experiment', 'C · 根据 A 继续验证', plan, predecessors=[a])
d = service.create('experiment', 'D · 从 A 分出另一项验证', plan, predecessors=[a])
e = service.create('experiment', 'E · 汇合 B、C、D 的信息', plan, predecessors=[b, c, d])
f = service.create('experiment', 'F · 综合结果后继续验证', plan, predecessors=[e])
doc = service.checked()[0][f]
service.update(doc.path, doc.revision, fields={'status': 'active'})
print('Fixture root: ' + str(store.root), flush=True)
serve(service, int(sys.argv[1]) if len(sys.argv) > 1 else 8767)
