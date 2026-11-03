"""Read Markdown/TOML and patch only the requested fields or sections."""
from dataclasses import dataclass
import hashlib
import json
import re
import tomllib


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scalar(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return '[' + ', '.join(scalar(v) for v in value) + ']'
    raise ValueError('Unsupported editable TOML value')


@dataclass
class Document:
    path: str
    raw: str
    revision: str

    def __post_init__(self):
        self.newline = '\r\n' if '\r\n' in self.raw else '\n'
        text = self.raw.replace('\r\n', '\n')
        self.header = ''
        self.body = text
        self.has_frontmatter = text.startswith('+++\n')
        if self.has_frontmatter:
            end = text.find('\n+++', 4)
            if end < 0 or text[end + 4:end + 5] not in ('', '\n'):
                raise ValueError('Unterminated TOML front matter')
            self.header = text[4:end]
            self.body = text[end + 4:].lstrip('\n')
        self.meta = tomllib.loads(self.header)

    @classmethod
    def from_bytes(cls, path, data):
        return cls(path, data.decode('utf-8-sig'), digest(data))

    def section(self, name):
        # Headings inside fenced code must not split a document.
        spans = self.section_spans()
        for title, start, content, end in spans:
            if title == name:
                return self.body[content:end].strip()
        return ''

    def section_spans(self):
        offsets = []
        pos = 0
        fence = None
        for line in self.body.splitlines(keepends=True):
            stripped = line.lstrip()
            marker = re.match(r'(`{3,}|~{3,})', stripped)
            if marker:
                symbol = marker[1][0]
                if fence is None:
                    fence = (symbol, len(marker[1]))
                elif symbol == fence[0] and len(marker[1]) >= fence[1]:
                    fence = None
            elif fence is None and line.startswith('## '):
                offsets.append((line[3:].strip(), pos, pos + len(line)))
            pos += len(line)
        return [(name, start, content, offsets[i + 1][1] if i + 1 < len(offsets) else len(self.body))
                for i, (name, start, content) in enumerate(offsets)]

    def patch(self, fields=None, sections=None):
        header, body = self.header, self.body
        # Patch only top-level scalar fields; preserve comments, ordering and tables.
        for key, value in (fields or {}).items():
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', key):
                raise ValueError('Invalid field name')
            lines = [line if line.endswith('\n') else line + '\n' for line in header.splitlines(keepends=True)]
            table_start = next((i for i, line in enumerate(lines) if line.lstrip().startswith('[')), len(lines))
            idx = next((i for i, line in enumerate(lines[:table_start])
                        if re.match(r'^\s*' + re.escape(key) + r'\s*=', line)), None)
            replacement = '' if value is None else f'{key} = {scalar(value)}\n'
            if idx is None:
                lines.insert(table_start, replacement)
            else:
                # Multiline/array values cannot be safely patched line by line.
                rhs = lines[idx].split('=', 1)[1]
                try:
                    tomllib.loads(key + '=' + rhs)
                except tomllib.TOMLDecodeError as exc:
                    raise ValueError(f'{key}: use the raw editor for multiline TOML') from exc
                lines[idx] = replacement
            header = ''.join(lines)
            if header and not header.endswith('\n'):
                header += '\n'
        for name, content in (sections or {}).items():
            temp = Document(self.path, body, '')
            span = next((s for s in temp.section_spans() if s[0] == name), None)
            block = f'## {name}\n\n{content.strip()}\n\n'
            if span:
                body = body[:span[1]] + block + body[span[3]:]
            else:
                body = body.rstrip() + '\n\n' + block
        text = ('+++\n' + header.rstrip() + '\n+++\n\n' if header or self.has_frontmatter else '') + body
        return text.replace('\n', self.newline)


KINDS = {'proposal': ('PROP', 'proposals'), 'plan': ('PLAN', 'plans'),
         'experiment': ('EXP', 'experiments')}
STATES = {'proposal': [], 'plan': ['active', 'paused', 'closed'],
          'experiment': ['draft', 'active', 'closed']}
RESOLUTIONS = ['supported', 'refuted', 'inconclusive', 'abandoned']
SECTIONS = {'proposal': ['Direction'],
            'plan': ['Question', 'Scope', 'Stop conditions', 'Acceptance criteria', 'Execution plan', 'Synthesis', 'Review'],
            'experiment': ['Approach', 'Notes', 'Results', 'Verification', 'Conclusion', 'Review']}


def template(kind, ident, title):
    meta = {'id': ident, 'title': title, 'summary': ''}
    if kind != 'proposal':
        meta['status'] = 'active' if kind == 'plan' else 'draft'
    if kind == 'plan':
        meta.update(experiments=[], follow_up_plans=[], project_docs_updated=[])
    if kind == 'experiment':
        meta.update(predecessors=[], verify=[], evidence=[])
    text = '+++\n' + '\n'.join(f'{k} = {scalar(v)}' for k, v in meta.items()) + '\n+++\n\n' + \
        '\n\n'.join(f'## {s}\n' for s in SECTIONS[kind]) + '\n'
    if kind == 'plan':
        from .execution import SHARED_STEP_TEMPLATE
        text = Document('', text, '').patch(sections={'Execution plan':
            '围绕本次目标、边界与验收要求组织当前已知的 steps；随 Experiment 的发现补充、调整或删除，不要求一开始列全。\n\n'
            '在下面的必要整理步骤前后补入本次探索的具体工作；不要把整个计划写成代码整理清单。\n\n'
            + SHARED_STEP_TEMPLATE})
    return text
