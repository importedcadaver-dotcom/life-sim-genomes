"""Render published Experiment 006 figures from saved CSV/JSON (no simulation)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[1] / 'results' / 'experiment_006'
NAME = {'founder': 'Founders', 'dense': 'Dense evolved',
        'islands': 'Island evolved', 'islands_costly': 'Costly-island evolved'}
GROUPS = list(NAME)


def save():
    summary = json.loads((ROOT / 'summary.json').read_text(encoding='utf-8'))
    mean = summary['means']
    names = list(NAME.values())
    x = np.arange(len(GROUPS))
    fig, ax = plt.subplots(figsize=(10.2, 5.3))
    conditions = [('rich', 'Accurate cues'), ('barren', 'No cues'),
                  ('decoy', 'Misleading cues'), ('straight', 'Straight motion')]
    for j, (code, label) in enumerate(conditions):
        vals = [mean[f'{g}/search/{code}']['core_arrival'] * 100 for g in GROUPS]
        ax.bar(x + (j - 1.5) * 0.20, vals, width=.19, label=label)
    ax.set_xticks(x, names)
    ax.set_ylabel('Reached any food core (%)')
    ax.set_ylim(0, 100)
    ax.set_title('Near-field search: accurate vs absent or misleading food cues')
    ax.legend(ncol=2, loc='upper left')
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(ROOT / 'search_cues.png', dpi=170)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10.2, 5.2))
    conditions2 = [('rich', 'Accurate cues'), ('barren', 'No cues'),
                   ('decoy', 'Misleading cues'), ('straight', 'Straight motion')]
    for j, (code, label) in enumerate(conditions2):
        vals = [mean[f'{g}/residence/{code}']['core_occupancy'] * 100 for g in GROUPS]
        ax.bar(x + (j - 1.5) * .20, vals, width=.19, label=label)
    ax.set_xticks(x, names)
    ax.set_ylabel('Time inside resource cores (%)')
    ax.set_ylim(0, 100)
    ax.set_title('Core residence: turning retains agents even without any food cues')
    ax.grid(axis='y', alpha=.2)
    ax.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / 'barren_residence.png', dpi=170)
    plt.close(fig)

    d = summary['evolved_minus_founder_cue_benefit']
    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    for j, group in enumerate(GROUPS[1:]):
        k = f'{group}/search/core_arrival'
        data = d[k]
        arr = np.array(data['seed_values']) * 100
        ax.scatter(np.full(len(arr), j) + np.linspace(-.12, .12, len(arr)), arr,
                   alpha=.65, s=34)
        lo, hi = np.array(data['descriptive_bootstrap_95_ci']) * 100
        ax.errorbar(j, data['mean'] * 100,
                    yerr=[[data['mean']*100-lo], [hi-data['mean']*100]],
                    fmt='D', color='black', capsize=5, markersize=6)
    ax.axhline(0, color='black', linewidth=.8, alpha=.55)
    ax.set_xticks(range(3), [NAME[g] for g in GROUPS[1:]])
    ax.set_ylabel('Additional cue benefit vs founders (percentage points)')
    ax.set_title('Exploratory difference-in-differences over eight training seeds')
    ax.grid(axis='y', alpha=.2)
    fig.tight_layout()
    fig.savefig(ROOT / 'selection_cue_response.png', dpi=170)
    plt.close(fig)

    traces = list(csv.DictReader((ROOT / 'sample_trajectories.csv').open(encoding='utf-8', newline='')))
    fig, ax = plt.subplots(figsize=(7.3, 7.3))
    for code, label in [('rich', 'Accurate'), ('barren', 'Barren'),
                        ('decoy', 'Misleading'), ('straight', 'Straight')]:
        rows = [r for r in traces if r['condition'] == code and r['agent'] == '2' and r['initial_start'] == 'search']
        xs = [float(r['x']) for r in rows]
        ys = [float(r['y']) for r in rows]
        ax.plot(xs, ys, linewidth=1.8, label=label)
        ax.scatter(xs[0], ys[0], s=16)
    ax.add_patch(Circle((40.4, 10), 3., fill=False, linestyle=':',
                        linewidth=2.2, color='black', label='Scored core'))
    ax.set_xlim(25, 65)
    ax.set_ylim(0, 40)
    ax.set_aspect('equal')
    ax.grid(alpha=.18)
    ax.set_xlabel('World X')
    ax.set_ylabel('World Y')
    ax.set_title('One search trajectory: identical starts, changed cues\n(single illustrative organism, not population evidence)')
    ax.legend(loc='upper right')
    fig.tight_layout()
    fig.savefig(ROOT / 'single_controller_paths.png', dpi=170)
    plt.close(fig)


if __name__ == '__main__':
    save()
    print('Saved four Experiment 006 figures in', ROOT)
