"""Low-frequency review handoff; this module does not launch or impersonate a model."""
import json
import re
import uuid

from .documents import Document
from .store import Conflict
from .validation import kind_of

NOTE = '''# Review note

Reviewer:

## 已核查

## 主要疑点

## 未覆盖与下一步
'''


def prepare(service, ident):
    docs, errors = service.checked()
    if errors:
        raise ValueError('\n'.join(errors))
    if ident not in docs or kind_of(docs[ident]) not in ('plan', 'experiment'):
        raise ValueError('Review requires a Plan or Experiment')
    folder = service.store.path(f'.work/reviews/{ident}/{uuid.uuid4().hex[:12]}')
    fingerprint = service.store.fingerprint()
    context = service.context(ident, reviewer=True)
    folder.mkdir(parents=True)
    (folder / 'context.md').write_text(context + '\n\n# 执行边界\n'
        '交给未参与本次方案与实现的独立 subagent；只审查，不提出替代实施方案或修改业务代码。\n'
        '宿主应将项目源码、知识和记录设为只读，只允许写本交接目录的 NOTE.md 和 checks/ 临时检查产物；这是宿主权限要求，本工具不声称已建立沙箱。\n'
        '核查适用的真实运行路径、端到端检查、数据泄露与投机完成，短 note 写实际证据及未覆盖范围。\n'
        '自动测试不冒充独立审查，导入 note 不自动关闭对象或采纳设计。\n', encoding='utf-8')
    (folder / 'NOTE.md').write_text(NOTE, encoding='utf-8')
    (folder / 'manifest.json').write_text(json.dumps({'id': ident, 'root': str(service.store.root),
        'fingerprint': fingerprint, 'allowed_write': ['NOTE.md', 'checks/']}, ensure_ascii=False, indent=2), encoding='utf-8')
    return folder.relative_to(service.store.root).as_posix()


def record(service, ident, relative_note):
    note_path = service.store.path(relative_note)
    reviews = service.store.path('.work/reviews')
    if not note_path.is_relative_to(reviews) or note_path.name != 'NOTE.md':
        raise ValueError('Use the NOTE.md created by review --prepare')
    manifest = json.loads(note_path.with_name('manifest.json').read_text(encoding='utf-8'))
    if manifest.get('id') != ident or manifest.get('root') != str(service.store.root):
        raise ValueError('Review handoff belongs to a different project or object')
    if manifest.get('fingerprint') != service.store.fingerprint():
        raise Conflict('Project content changed during review; prepare a fresh review handoff')
    text = note_path.read_text(encoding='utf-8').strip()
    reviewer = re.search(r'^Reviewer:\s*([^\r\n]+)', text, re.M)
    note = Document('NOTE.md', text, '')
    if not reviewer or reviewer.group(1).strip().startswith('#') or not note.section('已核查').strip() or not note.section('主要疑点').strip():
        raise ValueError('Fill Reviewer, 已核查 and 主要疑点 with actual review evidence; an empty template is not a review')
    docs, errors = service.checked()
    if errors or ident not in docs:
        raise ValueError('\n'.join(errors) or 'Unknown review target')
    target = docs[ident]
    # Keep note subheadings inside the object's Review, not as new top-level sections.
    embedded = re.sub(r'^#{1,2} ', '### ', text, flags=re.M)
    embedded += '\n\n审查依据指纹：' + manifest['fingerprint']
    service.update(target.path, target.revision, sections={'Review': embedded})
    return ident
