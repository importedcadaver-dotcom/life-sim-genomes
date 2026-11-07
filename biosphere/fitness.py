"""Experiment 007: ecological reproduction/survival with paired sensory interventions.

This is a *full ecological* follow-up to Experiment 006, not a motor-only assay.
Archived evolved genomes and matched founding genomes are run in new sparse
worlds; food can be depleted, energy falls, organisms reproduce and die.

Every intervention starts with identical positions/headings, map, genome sample,
seed and initial energy within its (seed, group, speed) matched block.
Mutations are switched off to isolate already-inherited behavior.
Results measure colony-level fitness proxies, not subjective intelligence.
"""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from .experiment import paired_ci
from .simulation import Config, World

GROUPS = ('founder', 'islands_costly')
SENSORY_CONDITIONS = ('normal', 'food_blind', 'mirror_food')
SPEED_CONDITIONS = ('natural', 'fixed_060')


def genotypes_for(seed: int, group: str, trained_results: Path, count: int) -> np.ndarray:
    """Stable genome subsamples, identical across sensory interventions."""
    if group not in GROUPS or count < 1:
        raise ValueError('Invalid genome group or population size')
    if group == 'founder':
        return World(Config(founders=count, max_population=max(900, count)), seed=seed).genomes.copy()
    filename = trained_results / 'checkpoints' / f'seed_{seed}_islands_costly.npz'
    if not filename.exists():
        raise FileNotFoundError(f'Missing archived training world: {filename}')
    source = World.load(filename).genomes
    if not len(source):
        raise ValueError(f'Training world has no survivors: {filename}')
    rng = np.random.default_rng(seed + 104_907)
    indices = rng.choice(len(source), count, replace=len(source) < count)
    return source[indices].copy()


def fitness_probe(genomes: np.ndarray, *, seed: int, sensory: str,
                  speed_mode: str, ticks: int = 350, growth_rate: float = .012) -> dict:
    if (sensory not in SENSORY_CONDITIONS or speed_mode not in SPEED_CONDITIONS
            or ticks < 1 or not (0 <= growth_rate <= 1)):
        raise ValueError('Invalid fitness assay parameters')
    genes = np.asarray(genomes, dtype=np.float64)
    if genes.ndim != 3 or genes.shape[1:] != (2, 8) or not len(genes):
        raise ValueError('Expected a non-empty batch of (2, 8) genomes')
    n = len(genes)
    cfg = Config(founders=n, max_population=max(n, 450), resource_layout='islands',
                 resource_background=.01, move_cost=.75, growth_rate=growth_rate,
                 sensor_mode=sensory, allow_mutation=False,
                 fixed_speed=.60 if speed_mode == 'fixed_060' else None)
    w = World(cfg, seed=seed + 130_000, founder_genomes=genes)
    agent_ticks = 0
    founder_survival_100: float | None = None
    peak_population = w.population
    for tick in range(ticks):
        agent_ticks += w.population
        w.step()
        peak_population = max(peak_population, w.population)
        if tick + 1 == min(100, ticks):
            founder_survival_100 = float(np.count_nonzero(w.ids < n) / n)
    # Founders only, because later descendants are not independent replicate units.
    founder_offspring = sum(w.specimen(id_)['offspring'] for id_ in range(n))
    return {
        'births_per_founder': float(w.total_births / n),
        'founder_direct_offspring': float(founder_offspring / n),
        'final_population': int(w.population),
        'final_population_per_founder': float(w.population / n),
        'peak_population': int(peak_population),
        'original_founder_survival_100': float(founder_survival_100),
        'starvation_deaths_per_founder': float(w.death_causes['starvation'] / n),
        'harvest_per_organism_tick': float(w.total_harvest / max(agent_ticks, 1)),
        'agent_ticks': int(agent_ticks),
        'total_births': int(w.total_births),
        'total_starvation_deaths': int(w.death_causes['starvation']),
    }


def paired_contrast(rows: list[dict], *, group: str, speed_mode: str,
                    metric: str, against: str = 'food_blind') -> dict:
    if group not in GROUPS or speed_mode not in SPEED_CONDITIONS or against not in SENSORY_CONDITIONS:
        raise ValueError('Unrecognized comparison')
    differences = []
    for seed in sorted({int(row['seed']) for row in rows}):
        trials = [r for r in rows if int(r['seed']) == seed and r['group'] == group
                  and r['speed_mode'] == speed_mode]
        normal = next((float(r[metric]) for r in trials if r['sensory'] == 'normal'), None)
        altered = next((float(r[metric]) for r in trials if r['sensory'] == against), None)
        if normal is not None and altered is not None:
            differences.append(normal - altered)
    arr = np.asarray(differences)
    return {
        'paired_seeds': len(arr),
        'mean_normal_minus_intervention': float(np.mean(arr)) if len(arr) else None,
        'positive_seeds': int(np.count_nonzero(arr > 0)),
        'seed_differences': differences,
        'exploratory_bootstrap_95_ci': list(paired_ci(arr)) if len(arr) else None,
    }


def difference_in_cue_benefit(rows: list[dict], *, speed_mode: str,
                              metric: str = 'founder_direct_offspring') -> dict:
    """Within-seed difference of (normal - blind) between evolved and founders."""
    differences = []
    for seed in sorted({int(row['seed']) for row in rows}):
        def outcome(group: str, sensory: str) -> float:
            return float(next(row[metric] for row in rows if int(row['seed']) == seed
                              and row['group'] == group and row['speed_mode'] == speed_mode
                              and row['sensory'] == sensory))
        evolved = outcome('islands_costly', 'normal') - outcome('islands_costly', 'food_blind')
        founder = outcome('founder', 'normal') - outcome('founder', 'food_blind')
        differences.append(evolved - founder)
    arr = np.asarray(differences)
    return {'mean_difference_in_cue_benefit': float(np.mean(arr)),
            'paired_seeds': len(arr), 'positive_seeds': int(np.count_nonzero(arr > 0)),
            'seed_differences': differences,
            'exploratory_bootstrap_95_ci': list(paired_ci(arr))}


def run_fitness(*, seeds: list[int], trained_results: Path, output: Path,
                ticks: int = 350, count: int = 80, growth_rate: float = .012,
                progress: bool = False) -> dict:
    if not seeds or len(set(seeds)) != len(seeds) or ticks < 1 or count < 1:
        raise ValueError('Provide unique seeds, positive ticks and count')
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for seed in seeds:
        for group in GROUPS:
            genomes = genotypes_for(seed, group, trained_results, count)
            for speed_mode in SPEED_CONDITIONS:
                for sensory in SENSORY_CONDITIONS:
                    result = fitness_probe(genomes, seed=seed, sensory=sensory,
                                           speed_mode=speed_mode, ticks=ticks,
                                           growth_rate=growth_rate)
                    rows.append({'seed': seed, 'group': group, 'speed_mode': speed_mode,
                                 'sensory': sensory, **result})
        if progress:
            print(f'Finished ecological fitness seed {seed} ({len(rows)} trial rows)', flush=True)
    with (output / 'trials.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    contrasts = {}
    for group in GROUPS:
        for speed_mode in SPEED_CONDITIONS:
            for metric in ('births_per_founder', 'founder_direct_offspring',
                           'final_population_per_founder', 'harvest_per_organism_tick',
                           'original_founder_survival_100'):
                for against in SENSORY_CONDITIONS[1:]:
                    key = f'{group}/{speed_mode}/{metric}/normal_vs_{against}'
                    contrasts[key] = paired_contrast(rows, group=group, speed_mode=speed_mode,
                                                       metric=metric, against=against)
    means = {}
    for group in GROUPS:
        for speed_mode in SPEED_CONDITIONS:
            for sensory in SENSORY_CONDITIONS:
                subset = [r for r in rows if r['group'] == group and r['speed_mode'] == speed_mode
                          and r['sensory'] == sensory]
                means[f'{group}/{speed_mode}/{sensory}'] = {
                    key: float(np.mean([r[key] for r in subset])) for key in
                    ('births_per_founder', 'founder_direct_offspring', 'final_population_per_founder',
                     'harvest_per_organism_tick', 'original_founder_survival_100')
                }
    difference_in_differences = {
        speed: {metric: difference_in_cue_benefit(rows, speed_mode=speed, metric=metric)
                for metric in ('births_per_founder', 'founder_direct_offspring',
                               'original_founder_survival_100')}
        for speed in SPEED_CONDITIONS}
    summary = {'seeds': seeds, 'count_per_trial': count, 'ticks_per_trial': ticks,
               'growth_rate': growth_rate, 'trial_count': len(rows),
               'design': 'Matched colony experiments; mutations disabled; births/deaths enabled',
               'contrasts': contrasts, 'means': means,
               'difference_in_differences': difference_in_differences}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary
