"""Validate a reviewed HLI → LLI → ALI plan and flatten it for recording."""
import argparse
import json
import re
from pathlib import Path


def parse_plan_to_triplets(text):
    high = low = None
    seen_high, seen_low, seen_atomic = set(), set(), set()
    rows = []
    pending = None
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('```'):
            continue
        match = re.fullmatch(r'([hla]\d+):\s*(\S.*)', line)
        if not match:
            raise ValueError(f'Line {number}: expected h0:, l0:, or a0: and nonempty text')
        key, value = match.groups()
        if key.startswith('h'):
            if pending in ('h', 'l'):
                raise ValueError(f'Line {number}: previous group has no atomic steps')
            if key in seen_high:
                raise ValueError(f'Line {number}: duplicate high-level ID {key}')
            seen_high.add(key)
            high, low, pending = (key, value), None, 'h'
        elif key.startswith('l'):
            if high is None or pending == 'l':
                raise ValueError(f'Line {number}: missing high-level or empty previous low-level group')
            scoped = high[0] + key
            if scoped in seen_low:
                raise ValueError(f'Line {number}: duplicate low-level ID {scoped}')
            seen_low.add(scoped)
            low, pending = (key, value), 'l'
        else:
            if high is None or low is None:
                raise ValueError(f'Line {number}: atomic instruction needs both parent levels')
            uid = high[0] + low[0] + key
            if uid in seen_atomic:
                raise ValueError(f'Line {number}: duplicate atomic ID {uid}')
            seen_atomic.add(uid)
            rows.append({'id': uid, 'step_id': len(rows), 'high-level': high[1],
                         'low-level': low[1], 'atomic-level': value})
            pending = 'a'
    if not rows or pending != 'a':
        raise ValueError('Plan must contain complete three-level instructions')
    return rows


def validate_plan(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Plan must be a nonempty list')
    seen = set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError('Each plan entry must be an object')
        for field in ('id', 'high-level', 'low-level', 'atomic-level'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f'Step {i}: missing {field}')
        if not re.fullmatch(r'h\d+l\d+a\d+', row['id']) or row['id'] in seen:
            raise ValueError(f'Step {i}: invalid or duplicate ID')
        if row.get('step_id') != i:
            raise ValueError('step_id must be consecutive from zero')
        seen.add(row['id'])
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    rows = validate_plan(parse_plan_to_triplets(args.input.read_text(encoding='utf-8')))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Validated {len(rows)} atomic instructions → {args.output}')

if __name__ == '__main__':
    main()
