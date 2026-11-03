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
if mode == 'hold-tree' and request['action'] == 'review':
    import os
    child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
    (Path(os.environ['TMP']) / 'worker-pid.txt').write_text(str(child.pid))
    time.sleep(30)
if mode in ('orphan', 'orphan-quiet') and request['action'] == 'review':
    import os
    child = subprocess.Popen([sys.executable, '-c',
        'import time;from pathlib import Path;time.sleep(5);Path("orphan-write.txt").write_text("bad")'],
        stdout=subprocess.DEVNULL if mode == 'orphan-quiet' else None,
        stderr=subprocess.DEVNULL if mode == 'orphan-quiet' else None)
    (Path(os.environ['TMP']) / 'orphan-pid.txt').write_text(str(child.pid))
    if mode == 'orphan':
        sys.exit(0)
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
