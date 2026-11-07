"""Experiment 006 motor-cue counterfactual and reproducibility tests."""
from __future__ import annotations

import csv
import hashlib
import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.trajectory import (
    CONDITIONS, STARTS, cue_landscapes, sample_controllers,
    trajectory_probe, run_trajectory_experiment, CORE_RADIUS,
)


def _genes(seed=1, n=55):
    return World(Config(founders=n), seed=seed).genomes


def _probe(condition='rich', start='residence', ticks=33, record=3):
    return trajectory_probe(sample_controllers(_genes(), seed=91), seed=413,
                            start=start, condition=condition, ticks=ticks,
                            record=record)


def test_input_condition_labels_and_static_maps():
    assert len(CONDITIONS) == 6
    assert len(STARTS) == 2
    rich, barren, decoy = cue_landscapes()
    assert rich.shape == (96, 96)
    assert not rich.flags.writeable
    assert barren.max() == 0
    assert np.max(rich) > 10
    assert not np.array_equal(rich, decoy)
    assert CORE_RADIUS == 3.0


def test_deterministic_trajectories_same_genomes_and_start():
    a, b = _probe(), _probe()
    assert a.summary == b.summary
    assert a.trace == b.trace
    np.testing.assert_array_equal(a.initial_turn, b.initial_turn)


def test_reward_removed_without_removing_cues_preserves_movement():
    rich, ghost = _probe('rich'), _probe('ghost')
    assert rich.trace == [dict(p, condition='rich') for p in ghost.trace]
    assert rich.summary['core_occupancy'] == ghost.summary['core_occupancy']
    assert rich.summary['mean_abs_turn'] == ghost.summary['mean_abs_turn']
    assert rich.summary['potential_resource_exposure'] > 0
    assert ghost.summary['potential_resource_exposure'] == 0


def test_barren_and_blind_are_exact_sensory_negative_controls():
    barren, blind = _probe('barren'), _probe('food_blind')
    assert barren.trace == [dict(p, condition='barren') for p in blind.trace]
    assert barren.summary['core_occupancy'] == blind.summary['core_occupancy']
    np.testing.assert_array_equal(barren.initial_turn, blind.initial_turn)
    assert barren.summary['initial_food_signal'] == 0
    assert blind.summary['initial_food_signal'] == 0


def test_cue_response_without_predefined_foraging_rule():
    rich = _probe('rich')
    barren = _probe('barren')
    assert rich.summary['initial_food_signal'] > 0
    assert np.max(np.abs(rich.initial_turn - barren.initial_turn)) > 0.00001
    assert rich.summary['mean_abs_turn'] > 0
    assert 0 <= rich.summary['core_occupancy'] <= 1
    assert 0 <= rich.summary['path_efficiency'] <= 1.01


def test_clamping_turn_to_zero_produces_straight_movement():
    straight = _probe('straight', ticks=10)
    assert np.all(straight.initial_turn == 0)
    assert straight.summary['mean_abs_turn'] == 0
    assert straight.summary['path_efficiency'] == pytest.approx(1, abs=1e-9)
    assert all(row['turn'] == 0 for row in straight.trace)


def test_decoy_cue_changes_response_at_same_initial_geometry():
    rich, decoy = _probe('rich'), _probe('decoy')
    assert np.max(np.abs(rich.initial_turn - decoy.initial_turn)) > 0.00001
    assert rich.trace != [dict(p, condition='rich') for p in decoy.trace]


def test_both_start_types_record_observables():
    for start in STARTS:
        p = _probe('rich', start=start)
        assert 0 <= p.summary['core_arrival'] <= 1
        assert 0 <= p.summary['core_occupancy'] <= 1
        assert p.summary['potential_resource_exposure'] >= 0
        if start == 'residence':
            assert p.summary['core_arrival'] == 1
            assert np.isfinite(p.summary['core_exit'])
        else:
            assert np.isnan(p.summary['core_exit'])


def test_invalid_conditions_rejected_without_pseudovalues():
    genome = _genes()
    for kwargs in ({'start':'oops', 'condition':'rich'},
                   {'start':'search','condition':'oops'},
                   {'start':'search','condition':'rich','ticks':0},
                   {'start':'search','condition':'rich','record':-2}):
        with pytest.raises(ValueError):
            trajectory_probe(genome, seed=1, **kwargs)
    with pytest.raises(ValueError):
        sample_controllers(np.zeros((0, 2, 8)), seed=0)


def test_run_generates_valid_csv_replay_and_preserves_checkpoints(tmp_path):
    source = tmp_path / 'old'
    (source / 'checkpoints').mkdir(parents=True)
    for group in ('dense', 'islands', 'islands_costly'):
        World(Config(founders=17), seed=3).save(source / 'checkpoints' / f'seed_3_{group}.npz')
    paths = sorted((source / 'checkpoints').glob('*.npz'))
    before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
    first = tmp_path / 'new'
    result = run_trajectory_experiment(seeds=[3], trained_results=source, output=first, ticks=7)
    assert result['trial_count'] == 4 * 2 * 6
    with (first / 'trials.csv').open(newline='') as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 48
    assert all(0 <= float(row['core_occupancy']) <= 1 for row in rows)
    assert (first / 'sample_trajectories.csv').stat().st_size > 100
    assert result['paired_seed_comparisons']['islands/residence/core_occupancy/rich_minus_barren']['n_training_seeds'] == 1
    second = tmp_path / 'replay'
    run_trajectory_experiment(seeds=[3], trained_results=source, output=second, ticks=7)
    assert (first / 'trials.csv').read_bytes() == (second / 'trials.csv').read_bytes()
    assert before == [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]


def test_missing_training_checkpoint_fails_cleanly(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_trajectory_experiment(seeds=[99], trained_results=tmp_path,
                                  output=tmp_path / 'out', ticks=2)
    with pytest.raises(ValueError):
        run_trajectory_experiment(seeds=[1, 1], trained_results=tmp_path,
                                  output=tmp_path / 'out', ticks=2)
