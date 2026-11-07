"""Actual Pygame/SDL screenshot and interaction smoke tests.

Unlike tools/pygame_preview_stub.py, this invokes the installed Pygame viewer.
Run via run_graphical_qa_windows.bat. The generated report is not evidence of
manual window interaction or physical Windows compatibility unless executed there.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run_checks(output: Path, *, python: str = sys.executable) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    legacy = ROOT / 'results/lineage_demo/world.npz'
    cases = [
        ('startup_small', 1020, 685, None, None, [1020, 685], None),
        ('startup_standard', 1400, 880, None, None, [1400, 880], None),
        ('startup_large', 1920, 1080, None, None, [1920, 1080], None),
        ('microscope', 1020, 685, 'microscope', None, [1020, 685], 'microscope'),
        ('sandbox', 1020, 685, 'sandbox', None, [1020, 685], None),
        ('resize', 1400, 880, 'resize', None, [1020, 685], None),
        ('toolbar_click', 1020, 685, 'toolbar_click', None, [1020, 685], 'tree'),
        ('pause', 1020, 685, 'pause', None, [1020, 685], None),
        ('restart_confirmation', 1020, 685, 'restart_confirmation', None, [1020, 685], None),
        ('v09_cheats', 1020, 685, 'v09_cheats', None, [1020, 685], 'cheats'),
        ('v10_dna', 1020, 685, 'v10_dna', None, [1020, 685], 'dna'),
        ('v11_regulatory_genes', 1020, 685, 'v11_regulatory_genes', None, [1020, 685], 'dna'),
        ('v10_gene_spark', 1020, 685, 'v10_gene_spark', None, [1020, 685], 'cheats'),
        ('v09_games', 1020, 685, 'v09_games', None, [1020, 685], 'games'),
        ('v09_chronicle', 1020, 685, 'v09_chronicle', None, [1020, 685], 'chronicle'),
        ('v09_lab', 1020, 685, 'v09_lab', None, [1020, 685], 'lab'),
        ('v09_cheat_refill', 1020, 685, 'v09_cheat_refill', None, [1020, 685], 'cheats'),
        ('v09_game_answer', 1020, 685, 'v09_game_answer', None, [1020, 685], 'games'),
        ('v09_chronicle_bookmark', 1020, 685, 'v09_chronicle_bookmark', None, [1020, 685], 'chronicle'),
    ]
    if legacy.exists():
        cases.append(('legacy_tree', 1020, 685, 'legacy_tree', legacy, [1020, 685], 'tree'))
    results = []
    for name, width, height, script, resume, expected_size, expected_overlay in cases:
        screenshot, report = output / f'{name}.png', output / f'{name}.json'
        cmd = [python, '-m', 'biosphere', 'view', '--seed', '701',
               '--window-width', str(width), '--window-height', str(height),
               '--smoke-frames', '12', '--screenshot', str(screenshot),
               '--qa-report', str(report)]
        if script:
            cmd += ['--qa-script', str(ROOT / 'tools/qa_scripts' / f'{script}.json')]
        if resume:
            cmd += ['--resume', str(resume)]
        try:
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=35)
            if run.returncode:
                raise RuntimeError((run.stdout + '\n' + run.stderr)[-2500:])
            data = json.loads(report.read_text(encoding='utf-8'))
            if not screenshot.is_file() or screenshot.stat().st_size < 1000:
                raise AssertionError('Screenshot missing/empty')
            if data['window_size'] != expected_size:
                raise AssertionError(f'Window {data["window_size"]}, expected {expected_size}')
            if data['ui']['selected_id'] is None:
                raise AssertionError('No specimen selected on initial viewer launch')
            if data['ui']['active_overlay'] != expected_overlay:
                raise AssertionError(f'Wrong overlay: {data["ui"]["active_overlay"]}')
            if name == 'sandbox' and data['ui']['interventions'] != 1:
                raise AssertionError('Sandbox click did not log an intervention')
            if name == 'pause' and not data['ui']['paused']:
                raise AssertionError('Pause shortcut did not pause')
            if name == 'v10_gene_spark' and data['ui']['interventions'] != 1:
                raise AssertionError('DNA Spark did not log an intervention')
            if name == 'v09_cheat_refill' and data['ui']['interventions'] != 1:
                raise AssertionError('Cheat action did not mark experimental intervention')
            if name == 'v09_game_answer' and data['ui']['mini_attempts'] != 1:
                raise AssertionError('Mini-game click did not submit answer')
            if name == 'v09_chronicle_bookmark' and data['ui']['bookmarks'] != 1:
                raise AssertionError('Chronicle bookmark failed')
            results.append({'case': name, 'status': 'PASS', 'screenshot': str(screenshot),
                            'mean_frame_ms': data['render_mean_ms'],
                            'p95_frame_ms': data['render_p95_ms']})
            print(f'PASS {name}: {data["window_size"]}')
        except Exception as exc:
            results.append({'case': name, 'status': 'FAIL', 'reason': str(exc)})
            print(f'FAIL {name}: {exc}')
    summary = {'engine': 'real Pygame/SDL' if importlib.util.find_spec('pygame') else 'unavailable',
               'platform': sys.platform, 'all_passed': all(r['status'] == 'PASS' for r in results),
               'cases': results,
               'limitations': 'Automated SDL rendering and synthetic input are not the same as a human UX test.'}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, default=ROOT / 'results/qa_windows')
    a = p.parse_args()
    if not importlib.util.find_spec('pygame'):
        raise SystemExit('Pygame missing. Install: python -m pip install pygame-ce')
    summary = run_checks(a.output)
    print('\nReport:', a.output / 'summary.json')
    raise SystemExit(0 if summary['all_passed'] else 1)
