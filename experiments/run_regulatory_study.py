"""Experiment 010: matched initial worlds, regulation presence/food-cue controls.

Pre-specified endpoints: cumulative births and survival after 420 ticks;
secondary: novel-gene counts and average regulatory program length.
Treatment comparisons are exploratory and are not proof of open-ended evolution.
"""
from __future__ import annotations
import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path
from statistics import mean
import numpy as np
from biosphere.simulation import Config, World


def study(*, seeds: list[int], steps: int, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    progress = []
    for seed in seeds:
        base = dict(width=28, height=24, founders=40, max_population=120,
                    genetics_enabled=True, growth_rate=.008, move_cost=.11,
                    reproduction_mode='mixed', regulatory_structure_rate=.12,
                    regulatory_point_rate=.10)
        # All conditions share the same initial ecology, neural brains and 12 loci.
        # Regulatory founders draw extra random numbers, so their subsequent RNG
        # sequences are not perfectly paired after reproduction diverges.
        for name, flags in [('none', dict(regulation_enabled=False)),
                            ('regulated', dict(regulation_enabled=True)),
                            ('regulated_blind', dict(regulation_enabled=True,
                                                     sensor_mode='food_blind'))]:
            world = World(Config(**base, **flags), seed=seed)
            # Founder state is seed-matched before the extra regulatory draws.
            for tick in range(steps):
                world.step()
                if (tick + 1) % 70 == 0:
                    progress.append(dict(seed=seed, condition=name, tick=world.tick,
                                         population=world.population,
                                         births=world.total_births,
                                         mean_genes=float(np.mean(world.regulatory_lengths))
                                         if world.population else 0.))
                if world.population == 0:
                    break
            rows.append(dict(seed=seed, condition=name, steps=world.tick,
                             population=world.population, births=world.total_births,
                             deaths=world.total_deaths,
                             innovations=world.regulatory_new_genes,
                             structural_changes=world.regulatory_new_chromosomes,
                             regulatory_mutations=world.regulatory_mutations,
                             mean_genes=float(np.mean(world.regulatory_lengths))
                             if world.population else 0.0))
    with (output/'trials.csv').open('w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    with (output/'timelines.csv').open('w',newline='') as f:
        w=csv.DictWriter(f, fieldnames=progress[0].keys());w.writeheader();w.writerows(progress)
    summaries = {}
    for name in ('none','regulated','regulated_blind'):
        data=[r for r in rows if r['condition']==name]
        summaries[name] = {k: round(mean(r[k] for r in data), 4)
                           for k in ('population','births','deaths','innovations','mean_genes')}
    comparisons = {}
    for a,b in [('regulated','none'),('regulated','regulated_blind')]:
        pa={r['seed']:r for r in rows if r['condition']==a}
        pb={r['seed']:r for r in rows if r['condition']==b}
        comparisons[f'{a}_minus_{b}']={
            'mean_birth_difference': round(mean(pa[s]['births']-pb[s]['births'] for s in seeds),4),
            'positive_birth_pairs': sum(pa[s]['births']>pb[s]['births'] for s in seeds),
            'paired_seeds': len(seeds)}
    summary={'seeds':seeds,'steps':steps,'conditions':summaries,'comparisons':comparisons,
             'interpretation': 'Exploratory ecology test. No proof of advantageous regulation or new physical laws.'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8,4.8))
        xs=np.arange(3)
        conditions=['none','regulated','regulated_blind']
        ax.bar(xs,[summaries[k]['births'] for k in conditions])
        ax.set_xticks(xs, ['Old biology', 'Evolvable regulation', 'Regulation, food-blind'])
        ax.set_ylabel('Mean offspring per world')
        ax.set_title(f'Experiment 010 · {len(seeds)} matched founder seeds · {steps} ticks')
        ax.spines[['right','top']].set_visible(False)
        fig.tight_layout();fig.savefig(output/'births.png',dpi=160);plt.close(fig)
    except ImportError:
        pass
    return summary


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--seeds',type=int,default=8)
    ap.add_argument('--steps',type=int,default=420)
    ap.add_argument('--seed-start',type=int,default=2401)
    ap.add_argument('--output',type=Path,default=Path('results/experiment_010'))
    args=ap.parse_args()
    print(json.dumps(study(seeds=list(range(args.seed_start,args.seed_start+args.seeds)),
                           steps=args.steps, output=args.output),indent=2))
if __name__ == '__main__':main()
