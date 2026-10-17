"""Normalize a downloaded snapshot into the data bundled with the apps."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from model_compare.snapshots import load_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    args = parser.parse_args()
    snapshot = load_snapshot(args.snapshot.read_bytes(), args.snapshot.name)
    if snapshot['is_demo']:
        parser.error('Choose a real snapshot; the fictional demo is already bundled separately.')
    destination = ROOT / 'model_compare/data/aa_snapshot.json'
    destination.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')
    print(f'Bundled {len(snapshot["models"])} model records in {destination.relative_to(ROOT)}')
    print(f'Source: {snapshot["source"]}; retrieved: {snapshot["retrieved_at"]}')


if __name__ == '__main__':
    main()
