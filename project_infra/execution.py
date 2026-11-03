"""One required Plan checklist step, without an independent step scheduler."""
import re

SHARED_STEP = '共享实现整理'
SHARED_STEP_TEMPLATE = (
    '- [ ] **共享实现整理**：检查本 Plan 产生或依赖的实现，复用或抽出适合共享的代码；'
    '按实际改动更新 TOOLKIT.md 并重跑相关入口。完成后在本步骤写“结果：”及具体处理；'
    '无需抽取时也记录原因。此步骤可随探索调整位置和范围。'
)


def shared_step_error(doc):
    """Require a real checked item and a result, ignoring fenced examples.

    The executing agent performs the work. This validates its workflow record,
    not the semantic quality or truthfulness of a refactoring claim.
    """
    items, current, fence = [], None, None
    for line in doc.section('Execution plan').splitlines():
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            symbol, length = marker[1][0], len(marker[1])
            if fence is None:
                fence = (symbol, length)
            elif symbol == fence[0] and length >= fence[1]:
                fence = None
            continue
        if fence:
            continue
        item = re.match(r'^\s*(?:[-+*]|\d+[.)])\s+\[([ xX])\]\s+(.*)', line)
        if item:
            current = None
            title = item[2].replace('**', '').replace('__', '')
            if re.match(r'^' + SHARED_STEP + r'(?:\s|[：:]|$)', title):
                current = {'done': item[1].lower() == 'x', 'text': title}
                items.append(current)
        elif re.match(r'^\s*(?:#{1,6}\s|[-+*]\s|\d+[.)]\s)', line):
            current = None
        elif current is not None:
            current['text'] += '\n' + line
    if len(items) != 1:
        return 'Plan 的 Execution plan 必须包含一项实际的“共享实现整理”复选步骤'
    if not items[0]['done']:
        return '先执行 Plan 的“共享实现整理”步骤，再发起交付或结束 Plan'
    # Result must be a deliberate field, rather than the template mentioning the word.
    text = items[0]['text']
    inline = re.match(r'^' + SHARED_STEP + r'\s*[：:]\s*结果\s*[：:]\s*(\S.*)', text)
    separate = re.search(r'^\s*结果\s*[：:]\s*(\S.*)', text, re.M)
    result = (inline or separate)
    if not result or result[1].strip() in ('待填写', '待补充', '...', '…'):
        return '“共享实现整理”已勾选，但缺少“结果：”记录；写明实际处理或无需抽取的原因'
    return None


def require_shared_step(doc):
    error = shared_step_error(doc)
    if error:
        raise ValueError(error)
