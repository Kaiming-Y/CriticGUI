"""Attach a human-reviewed critic label and explanation to one captured step."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('sample_folder', type=Path)
    p.add_argument('--label', choices=['success', 'failure'], required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--perturbation', default='', help='What was deliberately changed, if anything')
    p.add_argument('--parent-uid', default='', help='Reference demonstration for a perturbed example')
    p.add_argument('--reviewer', required=True, help='A non-sensitive reviewer ID')
    p.add_argument('--overwrite', action='store_true')
    a = p.parse_args()
    if not (a.sample_folder/'complete.json').exists() or not (a.sample_folder/'sample.json').exists():
        p.error('Only completed recordings can be reviewed')
    if not a.reason.strip() or not a.reviewer.strip():
        p.error('Reason and reviewer must be nonempty')
    sample = json.loads((a.sample_folder/'sample.json').read_text(encoding='utf-8'))
    if sample['meta']['variant'].startswith('negative') and (not a.perturbation.strip() or not a.parent_uid.strip()):
        p.error('A negative variant needs --perturbation and --parent-uid')
    target = a.sample_folder/'annotation.json'
    if target.exists() and not a.overwrite:
        p.error('Annotation exists; use --overwrite to revise it')
    target.write_text(json.dumps({'label':a.label, 'reason':a.reason.strip(),
        'perturbation':a.perturbation, 'parent_uid':a.parent_uid, 'reviewer':a.reviewer}, indent=2), encoding='utf-8')
    print(target)

if __name__ == '__main__':
    main()
