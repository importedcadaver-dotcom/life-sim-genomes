"""Verify sha256 manifest inside an extracted Accidental Biosphere release."""
from __future__ import annotations
import hashlib
from pathlib import Path


def verify(root: Path):
    mismatches = []
    lines = (root / 'MANIFEST_SHA256.txt').read_text(encoding='utf-8').splitlines()
    for line in lines:
        digest, relative = line.split('  ', 1)
        path = root / relative
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            mismatches.append(relative)
    return len(lines), mismatches


if __name__ == '__main__':
    count, errors = verify(Path(__file__).resolve().parents[1])
    print(f'{count} verified files' if not errors else f'FAIL {len(errors)}: {errors[:10]}')
    raise SystemExit(bool(errors))
