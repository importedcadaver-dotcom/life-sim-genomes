"""Rebuild Experiment 007 figures from recorded CSV/JSON evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'results' / 'experiment_007'


def main(source: Path = DATA) -> None:
    with (source / 'trials.csv').open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    summary = json.loads((source / 'summary.json').read_text(encoding='utf-8'))
    groups = ('founder', 'islands_costly')
    conditions = ('normal', 'food_blind', 'mirror_food')
    x = np.arange(len(conditions))
    width = .33
    fig, ax = plt.subplots(figsize=(9, 5.2))
    for i, group in enumerate(groups):
        means = [summary['means'][f'{group}/natural/{cond}']['founder_direct_offspring'] for cond in conditions]
        ax.bar(x + (i - .5) * width, means, width,
               label='Original founders' if group == 'founder' else 'Evolved in costly islands')
    ax.set_xticks(x, ('Accurate food inputs', 'Food inputs removed', 'Left/right cues mirrored'))
    ax.set_ylabel('Direct offspring per original founder (350 ticks)')
    ax.set_title('Complete-life ecology: reproduction changes when food senses are intervened upon')
    ax.legend()
    ax.set_ylim(bottom=0)
    fig.text(.12, .015, 'Each mean: 8 independently trained populations; fixed genomes, reproduction and death enabled', fontsize=9)
    fig.tight_layout(rect=(0, .04, 1, 1))
    fig.savefig(source / 'offspring_sensory_controls.png', dpi=165)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 4.9))
    for i, speed in enumerate(('natural', 'fixed_060')):
        per_seed = summary['difference_in_differences'][speed]['founder_direct_offspring']['seed_differences']
        ax.plot(summary['seeds'], per_seed, marker='o', label='Natural speed' if speed == 'natural' else 'Speed fixed at 0.60')
    ax.axhline(0, linestyle='--', linewidth=1)
    ax.set_ylabel('Extra cue benefit in evolved group (offspring per founder)')
    ax.set_xlabel('Independent training seed')
    ax.set_title('Differential sensory benefit: evolved vs original founder controllers')
    ax.legend()
    fig.tight_layout()
    fig.savefig(source / 'evolved_vs_founder_cue_advantage.png', dpi=165)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    for group in groups:
        vals = [summary['means'][f'{group}/natural/{cond}']['final_population_per_founder'] for cond in conditions]
        ax.plot(conditions, vals, marker='o', label='Original founders' if group == 'founder' else 'Costly-island evolved')
    ax.set_ylabel('Final population per starting organism')
    ax.set_xlabel('Food sensory intervention')
    ax.set_title('End population advantage is smaller and less consistent than reproduction')
    ax.legend()
    fig.tight_layout()
    fig.savefig(source / 'final_population_caveat.png', dpi=165)
    plt.close(fig)
    print(f'Written figures to {source}')


if __name__ == '__main__':
    main()
