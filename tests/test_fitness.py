"""Full-life ecological assays and matched sensory counterfactuals."""
import csv

import numpy as np
import pytest

from biosphere.fitness import (fitness_probe, genotypes_for, paired_contrast, difference_in_cue_benefit,
                               run_fitness, GROUPS, SENSORY_CONDITIONS, SPEED_CONDITIONS)
from biosphere.simulation import Config, World


def test_fitness_probe_has_survival_and_reproduction_and_is_deterministic():
    genes = World(Config(founders=12), seed=12).genomes
    a = fitness_probe(genes, seed=64, sensory='normal', speed_mode='natural', ticks=105)
    b = fitness_probe(genes, seed=64, sensory='normal', speed_mode='natural', ticks=105)
    assert a == b
    assert a['agent_ticks'] >= 12
    assert 0 <= a['original_founder_survival_100'] <= 1
    assert a['total_births'] >= 0
    assert a['harvest_per_organism_tick'] >= 0
    short = fitness_probe(genes, seed=64, sensory='food_blind', speed_mode='fixed_060', ticks=6)
    assert 0 <= short['original_founder_survival_100'] <= 1


def test_fitness_validation():
    genes = np.zeros((8, 2, 8))
    with pytest.raises(ValueError):
        fitness_probe(genes, seed=2, sensory='false', speed_mode='natural')
    with pytest.raises(ValueError):
        fitness_probe(genes, seed=2, sensory='normal', speed_mode='false')
    with pytest.raises(ValueError):
        fitness_probe(np.zeros((2, 6)), seed=2, sensory='normal', speed_mode='natural')


def test_fitness_study_outputs_complete_matched_blocks(tmp_path):
    source = tmp_path / 'training'
    (source / 'checkpoints').mkdir(parents=True)
    World(Config(founders=14), seed=7).save(source / 'checkpoints' / 'seed_7_islands_costly.npz')
    output = tmp_path / 'output'
    summary = run_fitness(seeds=[7], trained_results=source, output=output,
                          count=9, ticks=9)
    expected = len(GROUPS) * len(SENSORY_CONDITIONS) * len(SPEED_CONDITIONS)
    assert summary['trial_count'] == expected
    with (output / 'trials.csv').open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == expected
    assert summary['contrasts']['founder/natural/births_per_founder/normal_vs_food_blind']['paired_seeds'] == 1
    assert (output / 'summary.json').exists()


def test_contrasts_use_training_seed_not_individual_agents():
    rows = []
    for seed, normal, blind in ((1, .7, .4), (2, .8, .2)):
        for sensory, value in (('normal', normal), ('food_blind', blind)):
            rows.append({'seed': seed, 'group': 'islands_costly', 'speed_mode': 'natural',
                         'sensory': sensory, 'births_per_founder': value})
    result = paired_contrast(rows, group='islands_costly', speed_mode='natural',
                             metric='births_per_founder')
    assert result['paired_seeds'] == 2
    assert result['positive_seeds'] == 2
    assert result['mean_normal_minus_intervention'] == pytest.approx(.45)


def test_evolved_vs_founder_difference_of_differences():
    rows = []
    for seed in (1, 2):
        for group, cue_advantage in (("founder", .1), ("islands_costly", .5)):
            for sensory, value in (("normal", cue_advantage), ("food_blind", 0.)):
                rows.append({"seed": seed, "group": group, "speed_mode": "natural",
                             "sensory": sensory, "founder_direct_offspring": value})
    result = difference_in_cue_benefit(rows, speed_mode="natural")
    assert result["paired_seeds"] == 2
    assert result["positive_seeds"] == 2
    assert result["mean_difference_in_cue_benefit"] == pytest.approx(.4)
