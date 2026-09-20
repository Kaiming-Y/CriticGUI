"""Record a reviewed plan one atomic instruction at a time; resume by variant."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from human_demo.plan.parse_plan import validate_plan


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--task-id', required=True)
    p.add_argument('--software', required=True)
    p.add_argument('--variant', default='positive', help='Separate output run, e.g. negative-wrong-target')
    p.add_argument('--step', help='Record one atomic ID (restore its initial state manually)')
    a = p.parse_args()
    for value in (a.task_id, a.variant):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
            p.error('task-id and variant must use letters, digits, underscores or hyphens')
    raw = a.plan.read_bytes()
    rows = validate_plan(json.loads(raw))
    if a.step and a.step not in {r['id'] for r in rows}:
        p.error('Unknown --step ID')
    root = a.output / a.task_id / a.variant
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()
    manifest = root / 'session.json'
    meta = {'plan_sha256': digest, 'task_id': a.task_id, 'software': a.software, 'variant': a.variant}
    if manifest.exists() and json.loads(manifest.read_text()) != meta:
        p.error('Session metadata changed. Choose a new output or variant.')
    manifest.write_text(json.dumps(meta, indent=2), encoding='utf-8')
    (root / 'plan.json').write_bytes(raw)
    from pynput import keyboard
    from human_demo.recorder.action_monitor import start_listening
    from human_demo.recorder.action_parser import preprocess_actions
    start, skip = threading.Event(), threading.Event()
    listener = keyboard.GlobalHotKeys({'<ctrl>+<shift>+<f12>': start.set,
                                      '<ctrl>+<shift>+<f10>': skip.set})
    listener.start()
    try:
        for row in rows:
            if a.step and row['id'] != a.step:
                continue
            folder = root / row['id']
            if (folder / 'complete.json').exists():
                continue
            folder.mkdir(exist_ok=True)
            start.clear(); skip.clear()
            print('\n' + '\n'.join(f'{k}: {row[k]}' for k in ('id','high-level','low-level','atomic-level')))
            print('Restore the intended starting state. Ctrl+Shift+F12: start; F10 with Ctrl+Shift: skip.')
            while not start.is_set() and not skip.is_set():
                if not listener.is_alive():
                    raise RuntimeError('Global hotkey listener stopped')
                time.sleep(.1)
            if skip.is_set():
                continue
            log = Path(start_listening(folder))
            parsed = preprocess_actions(str(log))
            (log.parent / 'actions.json').write_text(json.dumps(parsed, indent=2), encoding='utf-8')
            sample = {'uid': f'{a.task_id}_{a.variant}_{row["id"]}', 'meta': meta | {'inst_id': row['id'], 'step_id': row['step_id']},
                      'instructions': {k:row[k] for k in ('high-level','low-level','atomic-level')},
                      'capture': str(log.parent.relative_to(folder)), 'review_status': 'pending'}
            (folder / 'sample.json').write_text(json.dumps(sample, indent=2), encoding='utf-8')
            (folder / 'complete.json').write_text('{}', encoding='utf-8')
    finally:
        listener.stop()
        listener.join(timeout=2)

if __name__ == '__main__':
    main()
