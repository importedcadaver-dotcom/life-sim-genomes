"""Regression tests for Experiment 005 and the interactive viewer's data layer."""
from dataclasses import replace
import csv
import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.viewer import terrain_rgb, layout_for
from biosphere.residency import (probe_residency, paired_differences, run_residency,
                                 STARTS, MODES)


def test_observatory_layout_fits_typical_windows():
    for w, h in ((1020, 685), (1200, 760), (1400, 880), (1920, 1080)):
        l = layout_for(w, h)
        x, y, pw, ph = l.map_rect
        sx, sy, sw, sh = l.side_rect
        assert x >= 0 and y >= 96
        assert x + pw <= sx - 8
        assert y + ph < l.toolbar_y
        assert l.toolbar_y + 35 < h
        assert sx + sw <= w
        assert abs(pw / ph - 72 / 54) < 0.02


def test_terrain_palette_matches_array_dimensions():
    f = np.array([[0, 0.1], [5, 11]])
    c = np.array([[3, 6], [8, 12]])
    rgb = terrain_rgb(f, c)
    assert rgb.shape == (2, 2, 3)
    assert rgb.dtype == np.uint8
    assert not np.array_equal(rgb[0, 0], rgb[1, 1])
    assert not np.array_equal(rgb, terrain_rgb(f, c, show_food=False))


def test_fertilizer_is_bounded_deterministic_and_recorded():
    cfg = Config(width=22, height=18, founders=5)
    a, b = World(cfg, 20), World(cfg, 20)
    previous = a.food.copy()
    n = a.fertilize(7.5, 11.0)
    assert n > 0
    assert n == pytest.approx(b.fertilize(7.5, 11.0))
    assert np.array_equal(a.food, b.food)
    assert np.all(a.food >= previous)
    assert np.all(a.food <= a.capacity + 1e-12)
    assert a.manual_interventions[0]['kind'] == 'fertilize'
    for _ in range(20):
        a.step(); b.step()
    assert np.array_equal(a.x, b.x)
    assert np.array_equal(a.food, b.food)


def test_fertilizer_rejects_invalid_values():
    w = World(Config(founders=0), 3)
    for bad in (dict(radius=0), dict(strength=-1), dict(radius=float('nan'))):
        with pytest.raises(ValueError):
            w.fertilize(3.0, 4.0, **bad)


def test_sandbox_intervention_survives_exact_checkpoint(tmp_path):
    a = World(Config(founders=30, max_population=60), 23)
    for _ in range(20):
        a.step()
    a.fertilize(5, 7)
    path = tmp_path / 'with_brush.npz'
    a.save(path)
    b = World.load(path)
    assert b.manual_interventions == a.manual_interventions
    assert np.array_equal(b.last_intake, a.last_intake)
    for _ in range(35):
        assert a.step() == b.step()
    assert np.array_equal(a.genomes, b.genomes)


def test_last_intake_aligned_through_born_and_dead():
    w = World(Config(width=22, height=18, founders=25, max_population=70), 4)
    w.age[:] = 100
    w.energy[:] = 80
    w.step()
    assert len(w.last_intake) == w.population
    assert np.all(w.last_intake[-w.total_births:] == 0.0)
    w.config = replace(w.config, allow_reproduction=False, metabolism=1000)
    w.step()
    assert w.population == 0
    assert len(w.last_intake) == 0


def test_reproduced_birth_and_death_events_have_locations():
    w = World(Config(width=22, height=18, founders=15, max_population=30), 7)
    w.age[:] = 99
    w.energy[:] = 75
    w.step()
    assert any(ev['kind'] == 'birth' for ev in w.last_events)
    for ev in w.last_events:
        assert 0 <= ev['x'] < w.config.width and 0 <= ev['y'] < w.config.height
    w.config = replace(w.config, metabolism=1000, allow_reproduction=False)
    w.step()
    assert any(ev['kind'] == 'death' for ev in w.last_events)
    assert all('x' in ev and 'y' in ev for ev in w.last_events)


def test_residency_probe_deterministic_and_sensible():
    genome = World(Config(founders=45), seed=1).genomes
    a = probe_residency(genome, seed=2, start='search', ticks=16)
    b = probe_residency(genome, seed=2, start='search', ticks=16)
    c = probe_residency(genome, seed=2, start='residence', ticks=16)
    assert a.keys() == b.keys()
    np.testing.assert_allclose(list(a.values()), list(b.values()), equal_nan=True)
    assert 0 <= a['hit_fraction'] <= 1
    assert c['hit_fraction'] == 1
    for item in (a, b, c):
        assert 0 <= item['occupancy_fraction'] <= 1
        assert item['harvest_per_agent_tick'] >= 0
        assert item['post_contact_dwell'] <= 1
        assert item['first_hit_penalized'] >= 0
    for kw in (dict(start='wrong'), dict(start='search', mode='bad'),
               dict(start='search', ticks=0)):
        with pytest.raises(ValueError):
            probe_residency(genome, seed=2, **kw)


def test_speed_clamp_and_zero_turn_baselines_identical_across_genotypes():
    a = World(Config(founders=40), 1).genomes
    b = World(Config(founders=40), 2).genomes
    x = probe_residency(a, seed=101, start='search', mode='fixed_zero_turn', ticks=20)
    y = probe_residency(b, seed=101, start='search', mode='fixed_zero_turn', ticks=20)
    assert x.keys() == y.keys()
    np.testing.assert_allclose(list(x.values()), list(y.values()), equal_nan=True)
    # Turn and speed clamped; genotype cannot affect movement


def test_paired_seed_comparisons_not_individuals():
    rows = []
    for seed in (1, 2):
        for mode, val in (('speed_fixed', seed * .2), ('fixed_zero_turn', .1)):
            rows.append({'seed': seed, 'group': 'founder', 'start': 'search',
                         'mode': mode, 'hit_fraction': val})
    result = paired_differences(rows, group='founder', start='search',
                                metric='hit_fraction')
    assert result['paired_seeds'] == 2
    assert result['positive_seeds'] == 2


def test_residency_experiment_csv_and_summary(tmp_path):
    source = tmp_path / 'old'
    (source / 'checkpoints').mkdir(parents=True)
    for group in ('dense', 'islands', 'islands_costly'):
        World(Config(founders=12), seed=13).save(source / 'checkpoints' / f'seed_13_{group}.npz')
    output = tmp_path / 'new'
    result = run_residency(seeds=[13], trained_results=source, output=output,
                           ticks=5)
    assert result['trial_count'] == 4 * len(STARTS) * len(MODES)
    with (output / 'trials.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == result['trial_count']
    assert result['contrasts']['islands/residence/occupancy_fraction']['paired_seeds'] == 1
    assert (output / 'summary.json').exists()


def test_missing_checkpoint_fails_cleanly(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_residency(seeds=[4], trained_results=tmp_path,
                      output=tmp_path / 'out', ticks=3)


def test_headless_event_export_accepts_new_event_coordinates(tmp_path):
    from argparse import Namespace
    from biosphere.cli import simulate
    args = Namespace(founders=12, max_population=40, sensor_mode='normal',
                     no_mutation=False, mutation_strength=.28, growth_rate=.03,
                     patchiness=1., resource_background=None, resource_layout='hills',
                     island_count=8, island_sigma=2.8, island_peak=10.,
                     boundary_mode='wrap', patch_shift_interval=0, move_cost=.065,
                     resume=None, seed=3, steps=22, sample_every=5,
                     events=True, output=str(tmp_path))
    simulate(args)
    with (tmp_path / 'lineage.csv').open(newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    assert {'x', 'y', 'id', 'parent_id', 'generation', 'cause'} <= set(reader.fieldnames)
    assert rows
    assert all(row['x'] and row['y'] for row in rows)


def test_original_v04_checkpoint_without_inspector_array_loads():
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / 'results/experiment_004/checkpoints/seed_701_islands.npz'
    if not path.exists():
        pytest.skip('Archived checkpoint not included in stripped source checkout')
    w = World.load(path)
    assert len(w.last_intake) == w.population
    assert w.manual_interventions == []
    w.step()
    assert len(w.last_intake) == w.population
