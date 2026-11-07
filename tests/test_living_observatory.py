"""v0.7: persistent individual lives, simulated time, layout, old saves."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.viewer import SimulationClock, layout_for, toolbar_grid


def test_pacing_measures_real_seconds_not_render_frames():
    a, b = SimulationClock(), SimulationClock()
    assert sum(a.steps(.05) for _ in range(40)) == 20
    assert sum(b.steps(.1) for _ in range(20)) == 20
    assert a.steps(.2, paused=True) == 0
    assert a.carry == 0
    a.change(100)
    assert a.rate == 600
    a.change(-100)
    assert a.rate == .5


def test_toolbar_two_rows_no_overlap_and_habitat_fits():
    for width, height in ((1020, 685), (1200, 760), (1400, 880), (1920, 1080)):
        l = layout_for(width, height)
        x, y, w, h = l.map_rect
        assert y + h < l.toolbar_y - 2
        assert l.toolbar_y + 71 < height
        rects = toolbar_grid(x, l.toolbar_y, w)
        assert len(rects) == 14
        for i, (rx, ry, rw, rh) in enumerate(rects):
            assert x <= rx and rx + rw <= x + w
            assert l.toolbar_y <= ry and ry + rh < height - 15
            for other in rects[:i]:
                ox, oy, ow, oh = other
                assert not (rx < ox + ow and ox < rx + rw and ry < oy + oh and oy < ry + rh)


def test_birth_life_archive_and_lineage_persist(tmp_path):
    cfg = Config(founders=6, max_population=15)
    world = World(cfg, seed=231)
    world.age[:] = 30
    world.energy[:] = 80
    assert world.watch(0)
    world.step()
    assert world.total_births == 6
    assert world.specimen(0)['offspring'] == 1
    assert any(item['tag'] == 'first_birth' for item in world.notable_events)
    assert world.specimen(0)['first_offspring_tick'] == 1
    children = world.relatives(0)
    assert len(children) == 1
    assert world.specimen(children[0])['parent_id'] == 0
    world.config = replace(world.config, allow_reproduction=False, metabolism=3000)
    world.step()
    assert world.population == 0
    assert world.specimen(0)['alive'] is False
    assert world.specimen(0)['cause'] == 'starvation'
    assert world.specimen(0)['offspring'] == 1
    assert any(item['tag'] == 'first_birth' for item in world.notable_events)
    assert world.specimen(children[0])['born_tick'] == 1
    assert len(world.life_archive) == 12
    assert len(world.observation_log) == 18
    assert any(item['tag'] == 'starvation' for item in world.notable_events)
    assert any(item['tag'] == 'extinction' for item in world.notable_events)
    saved = tmp_path / 'lineages.npz'
    world.save(saved)
    loaded = World.load(saved)
    assert loaded.life_archive == world.life_archive
    assert loaded.observation_log == world.observation_log
    assert loaded.notable_events == world.notable_events
    assert loaded.watch_traces == world.watch_traces
    assert loaded.relatives(0) == children
    assert loaded.specimen(0) == world.specimen(0)


def test_observability_stays_deterministic_and_watch_does_not_change_evolution(tmp_path):
    cfg = Config(founders=25, max_population=90)
    observed, control = World(cfg, 18), World(cfg, 18)
    assert not observed.watch(99999)
    assert observed.watch(0)
    for _ in range(55):
        assert observed.step() == control.step()
    assert np.array_equal(observed.genomes, control.genomes)
    assert np.array_equal(observed.food, control.food)
    assert len(observed.watch_traces[0]) > 1
    assert len(observed.population_history) > 1
    observed.save(tmp_path / 'observed.npz')
    restored = World.load(tmp_path / 'observed.npz')
    for _ in range(30):
        assert restored.step() == observed.step()
    assert restored.watch_traces == observed.watch_traces
    assert restored.population_history == observed.population_history


def test_backward_compatible_v06_checkpoint():
    path = (Path(__file__).resolve().parents[1] / 'results' / 'experiment_004'
            / 'checkpoints' / 'seed_701_islands_costly.npz')
    if not path.exists():
        pytest.skip('Optional historical checkpoint not bundled with this test installation')
    w = World.load(path)
    assert w.tick == 1000
    assert len(w.life_harvest) == w.population
    assert len(w.life_archive) == 0
    assert w.specimen(int(w.ids[0]))['alive']
    w.watch(int(w.ids[0]))
    w.step()
    assert len(w.life_harvest) == w.population
