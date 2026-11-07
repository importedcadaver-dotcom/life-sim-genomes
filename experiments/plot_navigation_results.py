"""Rebuild Experiment 004's fixed-speed summary charts from recorded JSON.

Usage: python -m experiments.plot_navigation_results
No training is run by this script; measurements remain in CSV and JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main(folder: Path = Path('results/experiment_004')) -> None:
    summary = json.loads((folder / 'motor_isolation_summary.json').read_text(encoding='utf8'))
    modes = ['speed_fixed', 'fixed_zero_turn', 'fixed_food_blind', 'fixed_mirror_food']
    labels = ['Normal turn', 'No turn', 'Food blind', 'Mirrored food']
    case_names = [('islands', 'islands', 'Sparse-trained / sparse'),
                  ('islands_costly', 'islands_costly', 'Costly-trained / costly sparse')]
    x = np.arange(len(modes))
    fig, ax = plt.subplots(figsize=(9.8, 5.6))
    bar_width = .35
    for j, (train, holdout, title) in enumerate(case_names):
        measurements = summary['means'][holdout][train]
        heights = [measurements[m] for m in modes]
        ax.bar(x+(j-.5)*bar_width, heights, bar_width, label=title)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, .52)
    ax.set_ylabel('Harvest per starting organism per evaluation tick')
    ax.set_title('Experiment 004B: fixed-speed interventions (0.60 for every agent)')
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(folder / 'fixed_speed_harvest.png', dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.6, 5.5))
    for j, (train, _, title) in enumerate(case_names):
        heights = [summary['target_means'][train][m]['hit_fraction'] for m in modes]
        ax.bar(x+(j-.5)*bar_width, heights, bar_width, label=title)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, .8)
    ax.set_ylabel('Fraction reaching any food-rich target core within 55 ticks')
    ax.set_title('Experiment 004B: reaching a target is not the same as harvesting')
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(folder / 'fixed_speed_target_hits.png', dpi=170)
    plt.close(fig)
    print('Saved fixed_speed_harvest.png and fixed_speed_target_hits.png')


if __name__ == '__main__':
    main()
