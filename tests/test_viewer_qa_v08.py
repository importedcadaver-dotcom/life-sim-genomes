"""v0.8 viewer UX and scripted QA evidence, Pygame-independent tests."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from biosphere.viewer import clamp_window_size, layout_for, load_qa_actions, toolbar_grid

ROOT = Path(__file__).resolve().parents[1]


def test_window_clamping_at_minimum_and_large():
    assert clamp_window_size(50, 20) == (1020, 685)
    assert clamp_window_size(1400, 880) == (1400, 880)
    assert clamp_window_size(1920, 1080) == (1920, 1080)


@pytest.mark.parametrize('width,height', [(1020, 685), (1400, 880), (1920, 1080)])
def test_toolbar_contained_at_supported_dimensions(width, height):
    layout = layout_for(width, height)
    ox, oy, pw, ph = layout.map_rect
    assert ox >= 15 and oy >= 100
    assert oy + ph < layout.toolbar_y
    for x, y, w, h in toolbar_grid(ox, layout.toolbar_y, pw):
        assert ox <= x and x + w <= ox + pw
        assert y >= layout.toolbar_y and y + h < height - 12


def test_qa_input_validation(tmp_path):
    assert load_qa_actions(None) == {}
    path = tmp_path / 'actions.json'
    path.write_text(json.dumps([{'frame': 2, 'action': 'key', 'key': 'o'},
                                {'frame': 3, 'action': 'click', 'x': 55, 'y': 200}]))
    assert len(load_qa_actions(path)[2]) == 1
    assert len(load_qa_actions(path)[3]) == 1
    for invalid in ([{'frame': -1, 'action': 'key', 'key': 'o'}],
                    [{'frame': 1, 'action': 'key', 'key': 'F8'}],
                    [{'frame': 1, 'action': 'click', 'x': 'bad', 'y': 4}],
                    [{'frame': 1, 'action': 'hacked'}],
                    {'not': 'a list'}):
        path.write_text(json.dumps(invalid))
        with pytest.raises(ValueError):
            load_qa_actions(path)


def _preview(tmp_path, scenario, *, resume=None, size='1020x685'):
    pytest.importorskip('PIL')
    output = tmp_path / f'{scenario}.png'
    report = tmp_path / f'{scenario}.json'
    cmd = [sys.executable, 'tools/pygame_preview_stub.py', '--size', size,
           '--qa-script', f'tools/qa_scripts/{scenario}.json',
           '--out', str(output), '--qa-report', str(report)]
    if resume:
        cmd.extend(['--resume', str(resume)])
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
    from PIL import Image
    with Image.open(output) as im:
        assert im.size == tuple(json.loads(report.read_text())['window_size'])
        assert im.getpixel((100, 100)) != (0, 0, 0)
    return json.loads(report.read_text())


def test_microscope_from_selected_founder(tmp_path):
    result = _preview(tmp_path, 'microscope')
    assert result['ui']['selected_id'] == 0
    assert result['ui']['active_overlay'] == 'microscope'
    assert result['qa_actions_executed'] == 1


def test_legacy_checkpoint_tree_does_not_crash_with_missing_ancestors(tmp_path):
    legacy = ROOT / 'results/lineage_demo/world.npz'
    if not legacy.is_file():
        pytest.skip('legacy QA fixture not included')
    result = _preview(tmp_path, 'legacy_tree', resume=legacy)
    assert result['ui']['active_overlay'] == 'tree'
    assert result['ui']['selected_id'] is not None


def test_sandbox_click_is_logged_as_intervention(tmp_path):
    result = _preview(tmp_path, 'sandbox')
    assert result['ui']['interventions'] == 1


def test_resize_rebuilds_the_viewport(tmp_path):
    result = _preview(tmp_path, 'resize', size='1400x880')
    assert result['window_size'] == [1020, 685]


def test_clickable_toolbar_works_without_hotkeys(tmp_path):
    result = _preview(tmp_path, 'toolbar_click')
    assert result['ui']['active_overlay'] == 'tree'
