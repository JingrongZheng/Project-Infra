"""Protocol fixture only; not a model, independent review, or production adapter."""
import json
from pathlib import Path
import subprocess
import sys
import time

request = json.loads(sys.stdin.buffer.read().decode('utf-8'))
mode = sys.argv[1] if len(sys.argv) > 1 else 'ok'
if mode == 'timeout':
    time.sleep(30)
if mode == 'review-timeout' and request['action'] == 'review':
    time.sleep(30)
if mode == 'failure':
    print('fixture exit failure', file=sys.stderr)
    sys.exit(7)
if mode == 'invalid':
    print('not JSON')
    sys.exit(0)
if mode == 'mutate' and request['action'] == 'review':
    Path('mutation.txt').write_text('fixture source mutation')
if request['action'] == 'probe':
    print(json.dumps({'nonce': request['nonce'], 'independent': True, 'session': 'fixture-only'}))
else:
    print(json.dumps({'note': 'Reviewer: protocol fixture, not actual independent review\n\n## 已核查\nFixture protocol exchange only.\n\n## 主要疑点\nThis result does not establish production correctness.\n\n## 未覆盖与下一步\nNo actual model review performed.'}))
