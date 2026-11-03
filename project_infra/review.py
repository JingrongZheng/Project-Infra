"""Low-frequency review handoff; this module does not launch or impersonate a model."""
import json
import re
import uuid
import time
from datetime import datetime, timezone

from .documents import Document
from .store import Conflict
from .validation import kind_of
from .documents import digest
from . import reviewer_runtime as runtime

NOTE = '''# Review note

Reviewer:

## 已核查

## 主要疑点

## 未覆盖与下一步
'''


def prepare(service, ident):
    capability = runtime.status(service.store)
    if not capability.get('enabled'):
        raise ValueError('质疑功能已关闭：' + capability['reason'] + '；先运行 reviewer 自检')
    docs, errors = service.checked()
    if errors:
        raise ValueError('\n'.join(errors))
    if ident not in docs or kind_of(docs[ident]) not in ('plan', 'experiment'):
        raise ValueError('Review requires a Plan or Experiment')
    if docs[ident].meta.get('status') == 'closed':
        raise ValueError('Reopen the object before starting another delivery review')
    folder = service.store.path(f'.work/reviews/{ident}/{uuid.uuid4().hex[:12]}')
    deadline = time.time() + runtime.read(service.store)['timeout']
    active_path = f'.work/reviewer/active/{ident}.json'
    with service.store.locked():
        active_file = service.store.path(active_path)
        previous = json.loads(active_file.read_text(encoding='utf-8')) if active_file.exists() else {}
        if (previous.get('runtime_id') == capability['runtime_id'] and previous.get('deadline', 0) > time.time()
                and not service.store.path(previous['archive']).exists()):
            raise Conflict('This delivery already has a pending review; finish it or disable/recheck the reviewer')
        service.store.commit_locked({active_path: json.dumps({'runtime_id': capability['runtime_id'],
            'deadline': deadline, 'archive': f'.project/reviews/{ident}/{folder.name}.md'})},
            {active_path: digest(active_file.read_bytes()) if active_file.exists() else None})
    fingerprint = service.store.fingerprint()
    context = service.context(ident, reviewer=True)
    folder.mkdir(parents=True)
    (folder / 'context.md').write_text(context + '\n\n# 执行边界\n'
        '这是显式交付检查点。交给未参与本次方案与实现的独立会话（subagent、进程或其他接入方式）；只审查，不提出替代实施方案或修改业务代码。\n'
        '宿主应将项目源码、知识和记录设为只读，只允许写本交接目录的 NOTE.md 和 checks/ 临时检查产物；这是宿主权限要求，本工具不声称已建立沙箱。\n'
        '核查适用的真实运行路径、端到端检查、数据泄露与投机完成，短 note 写实际证据及未覆盖范围。\n'
        '自动测试不冒充独立审查，导入 note 不自动关闭对象或采纳设计。\n', encoding='utf-8')
    (folder / 'NOTE.md').write_text(NOTE, encoding='utf-8')
    (folder / 'manifest.json').write_text(json.dumps({'id': ident, 'root': str(service.store.root),
        'fingerprint': fingerprint, 'allowed_write': ['NOTE.md', 'checks/'],
        'runtime_id': capability['runtime_id'], 'deadline': deadline,
        'round': folder.name}, ensure_ascii=False, indent=2), encoding='utf-8')
    return folder.relative_to(service.store.root).as_posix()


def record(service, ident, relative_note):
    note_path = service.store.path(relative_note)
    reviews = service.store.path('.work/reviews')
    if not note_path.is_relative_to(reviews) or note_path.name != 'NOTE.md':
        raise ValueError('Use the NOTE.md created by review --prepare')
    manifest = json.loads(note_path.with_name('manifest.json').read_text(encoding='utf-8'))
    if manifest.get('id') != ident or manifest.get('root') != str(service.store.root):
        raise ValueError('Review handoff belongs to a different project or object')
    capability = runtime.status(service.store)
    if not capability.get('enabled') or manifest.get('runtime_id') != capability.get('runtime_id'):
        raise ValueError('Review capability is unavailable or changed; prepare a fresh handoff')
    if manifest.get('deadline', 0) <= time.time():
        runtime.disable(service.store, '本轮审查超时，未记为完成')
        raise ValueError('Review deadline exceeded; no review was recorded')
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
    stamp = datetime.now(timezone.utc).isoformat()
    archive = f'.project/reviews/{ident}/{manifest["round"]}.md'
    metadata = archive[:-3] + '.json'
    embedded = f'### 审查轮次 {manifest["round"]} · {stamp}\n\n' + embedded
    embedded += '\n\n审查依据指纹：' + manifest['fingerprint'] + '\n原始意见：' + archive
    previous = target.section('Review').strip()
    text = target.patch(sections={'Review': (previous + '\n\n' if previous else '') + embedded})
    with service.store.locked():
        if manifest['fingerprint'] != service.store.fingerprint():
            raise Conflict('Project content changed during review; prepare a fresh handoff')
        service.require_valid({target.path: text})
        service.store.commit_locked({target.path: text, archive: note_path.read_text(encoding='utf-8'),
            metadata: json.dumps({'id': ident, 'round': manifest['round'], 'time': stamp,
                                  'fingerprint': manifest['fingerprint'], 'note': archive}, ensure_ascii=False)},
            {target.path: target.revision, archive: None, metadata: None})
        receipt = f'.work/reviewer/deliveries/{ident}.json'
        p = service.store.path(receipt)
        service.store.commit_locked({receipt: json.dumps({'fingerprint': service.store.fingerprint(),
            'runtime_id': capability['runtime_id'], 'round': manifest['round']})},
            {receipt: digest(p.read_bytes()) if p.exists() else None})
    return ident


def history(store, ident):
    rows = []
    for p in store.path(f'.project/reviews/{ident}').glob('*.json'):
        row = json.loads(p.read_text(encoding='utf-8'))
        row['text'] = store.path(row['note']).read_text(encoding='utf-8')
        rows.append(row)
    return sorted(rows, key=lambda r: (r['time'], r['round']))


def require_delivery(service, ident):
    capability = runtime.status(service.store)
    if not capability.get('enabled'):
        return '未执行独立审查：' + capability['reason']
    p = service.store.path(f'.work/reviewer/deliveries/{ident}.json')
    receipt = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    if (receipt.get('fingerprint') != service.store.fingerprint() or
            receipt.get('runtime_id') != capability.get('runtime_id')):
        raise ValueError('交付前需要本轮独立审查；先保存内容，再运行 deliver ' + ident)
    return '已完成独立审查交接；意见见 Review。此标记不代表方案通过或已被采纳。'


def deliver(service, ident):
    docs, errors = service.checked()
    if errors or ident not in docs or kind_of(docs[ident]) not in ('plan', 'experiment'):
        raise ValueError('\n'.join(errors) or 'Delivery requires a Plan or Experiment')
    if docs[ident].meta.get('status') == 'closed':
        raise ValueError('Reopen the object before starting another delivery review')
    capability = runtime.status(service.store)
    if not capability.get('enabled'):
        message = '未执行独立审查：' + capability['reason']
        target = docs[ident]
        service.update(target.path, target.revision, sections={'Delivery': message})
        return {'reviewed': False, 'reason': message}
    folder = prepare(service, ident)
    data = runtime.read(service.store)
    if data['mode'] == 'host':
        return {'reviewed': False, 'pending': True, 'handoff': folder,
                'reason': '请宿主在独立会话中审查，随后使用 review --record 导入；关闭前必须完成本轮交接'}
    try:
        response = runtime.invoke(service.store, data, {'action': 'review', 'id': ident,
            'project': str(service.store.root), 'context': service.store.path(folder + '/context.md').read_text(encoding='utf-8'),
            'handoff': folder}, folder)
        if not isinstance(response.get('note'), str):
            raise ValueError('Reviewer response requires a note string')
        service.store.path(folder + '/NOTE.md').write_text(response['note'], encoding='utf-8')
        record(service, ident, folder + '/NOTE.md')
        return {'reviewed': True, 'handoff': folder}
    except (ValueError, OSError) as exc:
        runtime.disable(service.store, f'审查执行失败，质疑功能已关闭：{exc}')
        raise
