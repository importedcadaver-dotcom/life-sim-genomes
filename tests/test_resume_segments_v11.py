"""Step 2: segmented headless continuations preserve their source files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from biosphere.simulation import World


def call(*args: str, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, '-m', 'biosphere', 'run', *map(str, args)],
                            text=True, capture_output=True)
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0, result.stdout
    return result


def original_files(root: Path) -> dict[str, bytes]:
    return {f.name: f.read_bytes() for f in root.iterdir() if f.is_file()}


def start(root: Path) -> None:
    call('--seed', '3', '--steps', '12', '--founders', '20', '--max-population', '50',
         '--sample-every', '1', '--events', '--output', str(root))


def test_root_unchanged_across_repeated_latest_resumes(tmp_path: Path):
    out = tmp_path / 'run'
    start(out)
    root_before = original_files(out)
    first = call('--resume', str(out / 'world.npz'), '--steps', '3',
                 '--sample-every', '1', '--events', '--output', str(out))
    segment1 = out / 'segments' / 'segment-000001'
    assert 'Latest checkpoint:' in first.stdout
    assert str(segment1 / 'world.npz') in first.stdout
    assert original_files(out) == root_before
    first_bytes = original_files(segment1)
    assert World.load(segment1 / 'world.npz').tick == 15
    second = call('--resume-latest', '--steps', '4', '--sample-every', '1',
                  '--events', '--output', str(out))
    segment2 = out / 'segments' / 'segment-000002'
    assert str(segment2 / 'world.npz') in second.stdout
    assert World.load(segment2 / 'world.npz').tick == 19
    assert original_files(out) == root_before
    assert original_files(segment1) == first_bytes
    a = json.loads((segment1 / 'segment.json').read_text())
    b = json.loads((segment2 / 'segment.json').read_text())
    assert (a['start_tick'], a['end_tick']) == (12, 15)
    assert (b['start_tick'], b['end_tick']) == (15, 19)
    assert b['source_sha256'] == a['checkpoint_sha256']


def test_stale_root_refused_without_touching_any_file(tmp_path: Path):
    out = tmp_path / 'run'
    start(out)
    call('--resume', str(out / 'world.npz'), '--steps', '3', '--output', str(out))
    root_before = original_files(out)
    segment1 = out / 'segments' / 'segment-000001'
    seg_before = original_files(segment1)
    rejected = call('--resume', str(out / 'world.npz'), '--steps', '2',
                    '--output', str(out), success=False)
    assert 'STALE CHECKPOINT / OVERLAPPING TICKS' in rejected.stderr
    assert 'latest recorded tick is 15' in rejected.stderr
    assert 'segment-000001/world.npz' in rejected.stderr
    assert original_files(out) == root_before
    assert original_files(segment1) == seg_before
    assert sorted(p.name for p in (out / 'segments').iterdir()) == ['segment-000001']


def test_explicit_overwrite_terminal_segment_and_refuse_nonterminal(tmp_path: Path):
    out = tmp_path / 'run'
    start(out)
    call('--resume', str(out / 'world.npz'), '--steps', '3', '--output', str(out))
    original = original_files(out)
    terminal = out / 'segments' / 'segment-000001'
    old = original_files(terminal)
    # An explicitly named terminal segment can be replaced, preserving source history.
    call('--resume', str(out / 'world.npz'), '--segment', 'segment-000001',
         '--overwrite', '--steps', '5', '--output', str(out))
    assert World.load(terminal / 'world.npz').tick == 17
    assert original_files(out) == original
    assert original_files(terminal) != old
    call('--resume-latest', '--steps', '2', '--output', str(out))
    terminal2 = out / 'segments' / 'segment-000002'
    unchanged = original_files(terminal)
    rejected = call('--resume', str(out / 'world.npz'), '--segment', 'segment-000001',
                    '--overwrite', '--steps', '1', '--output', str(out), success=False)
    assert 'terminal run segment' in rejected.stderr
    assert original_files(terminal) == unchanged
    assert terminal2.is_dir()


def test_overwrite_requires_explicit_target_and_valid_source(tmp_path: Path):
    out = tmp_path / 'run'
    start(out)
    call('--resume-latest', '--steps', '2', '--output', str(out))
    existing = original_files(out / 'segments' / 'segment-000001')
    for flags in [('--overwrite',), ('--segment', 'segment-000001')]:
        rejected = call('--resume-latest', '--steps', '2', '--output', str(out),
                        *flags, success=False)
        assert 'ValueError' in rejected.stderr
    wrong = call('--resume-latest', '--segment', 'segment-000001',
                 '--overwrite', '--steps', '2', '--output', str(out), success=False)
    assert 'source does not match' in wrong.stderr
    assert original_files(out / 'segments' / 'segment-000001') == existing


def test_no_resume_change_to_existing_fresh_run_output_policy(tmp_path: Path):
    out = tmp_path / 'run'
    start(out)
    original = World.load(out / 'world.npz').tick
    call('--steps', '2', '--seed', '5', '--founders', '10',
         '--max-population', '15', '--output', str(out))
    assert original == 12
    assert World.load(out / 'world.npz').tick == 2
    assert not (out / 'segments').exists()


def test_disk_archive_resume_isolated_from_original_sqlite(tmp_path: Path):
    out = tmp_path / 'run'
    call('--seed', '7', '--steps', '25', '--founders', '15', '--max-population', '40',
         '--disk-archive', '--output', str(out))
    previous = original_files(out)
    call('--resume', str(out / 'world.npz'), '--steps', '3', '--disk-archive', '--output', str(out))
    assert original_files(out) == previous
    path = out / 'segments' / 'segment-000001' / 'world.npz'
    resumed = World.load(path)
    assert resumed.tick == 28
    assert hasattr(resumed.life_archive, 'snapshot_bytes')


def test_failed_resume_does_not_publish_partial_segment(tmp_path: Path, monkeypatch):
    out = tmp_path / 'run'
    start(out)
    old = original_files(out)
    # Fail deliberately AFTER the staged metrics/lineage files have been opened
    # and one simulation step has completed. No simulation source is modified.
    from biosphere.cli import main
    original_step = World.step
    calls = 0

    def fail_after_one_step(world):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError('INJECTED MID-RUN FAILURE')
        return original_step(world)

    monkeypatch.setattr(World, 'step', fail_after_one_step)
    monkeypatch.setattr(sys, 'argv', [
        'biosphere', 'run', '--resume-latest', '--steps', '3',
        '--sample-every', '1', '--output', str(out),
    ])
    with pytest.raises(RuntimeError, match='INJECTED MID-RUN FAILURE'):
        main()
    assert calls == 2
    assert original_files(out) == old
    assert not list((out / 'segments').glob('segment-*'))
    assert not list((out / 'segments').glob('.pending-*'))


def test_unrelated_existing_output_history_refuses_external_resume(tmp_path: Path):
    out = tmp_path / 'run'
    other = tmp_path / 'other'
    start(out)
    call('--seed', '17', '--steps', '12', '--founders', '20',
         '--max-population', '50', '--output', str(other))
    original = original_files(out)
    rejected = call('--resume', str(other / 'world.npz'), '--steps', '2',
                    '--output', str(out), success=False)
    assert 'STALE CHECKPOINT / OVERLAPPING TICKS' in rejected.stderr
    assert original_files(out) == original
