"""Export reviewed human demonstrations as portable critic examples (JSONL)."""
import argparse
import json
from pathlib import Path
import shutil
from human_demo.action.action_normalizer import split_ctrl_scroll, normalize_logs, process_hotkey_actions
from human_demo.action.action_translater import translate_actions


def export_samples(root, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    seen = set()
    for path in sorted(root.rglob('sample.json')):
        folder = path.parent
        if not (folder / 'complete.json').exists():
            continue
        sample = json.loads(path.read_text(encoding='utf-8'))
        annotation = folder / 'annotation.json'
        if not annotation.exists():
            continue
        review = json.loads(annotation.read_text(encoding='utf-8'))
        if review.get('label') not in ('success', 'failure') or not review.get('reason', '').strip():
            raise ValueError(f'Invalid review: {annotation}')
        capture = folder / sample['capture']
        if not capture.resolve().is_relative_to(folder.resolve()):
            raise ValueError(f'Capture escapes sample folder: {path}')
        uid = sample['uid']
        if not uid or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in uid) or uid in seen:
            raise ValueError(f'Invalid or duplicate UID: {uid}')
        seen.add(uid)
        parsed = json.loads((capture / 'actions.json').read_text(encoding='utf-8'))
        actions = process_hotkey_actions(normalize_logs(split_ctrl_scroll(parsed)))
        code = '\n'.join(translate_actions(actions, click_threshold=10))
        # Syntax check only: action code is a representation and is never executed here.
        compile(code, '<action-code>', 'exec')
        videos = list(capture.glob('video.*'))
        if len(videos) != 1:
            raise ValueError(f'Expected one action video in {capture}')
        media = output / 'media' / uid
        media.mkdir(parents=True, exist_ok=True)
        files = {'before':capture/'before.png', 'after':capture/'after.png', 'video':videos[0]}
        links = {}
        for key, source in files.items():
            target = media / source.name
            shutil.copy2(source, target)
            links[key] = target.relative_to(output).as_posix()
        records.append({'uid': uid, 'source': 'human_demonstration', 'meta': sample['meta'],
                        'instructions': sample['instructions'], 'actions': actions, 'action_code': code,
                        'media': links, 'review': review})
    (output / 'samples.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in records), encoding='utf-8')
    return len(records)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if not a.input.is_dir():
        p.error('Input directory does not exist')
    if a.output.resolve().is_relative_to(a.input.resolve()):
        p.error('Keep export outside the recording directory')
    if a.output.exists() and any(a.output.iterdir()):
        p.error('Use a new/empty export directory to avoid stale samples')
    print(f'Exported {export_samples(a.input, a.output)} reviewed examples')

if __name__ == '__main__':
    main()
