"""Render a REAL saved simulation state, not an artist's depiction.
Usage: python experiments/plot_snapshot.py results/experiment_6seed/evolved_seed_1.npz results/ecosystem_snapshot.png
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from biosphere import World


def render(source: str, target: str) -> None:
    world = World.load(source)
    fig, (ax, side) = plt.subplots(1, 2, figsize=(13.2, 7.8),
                                    gridspec_kw={'width_ratios': [4.7, 1.8]},
                                    layout='constrained')
    fig.patch.set_facecolor('#0f1b20')
    ax.set_facecolor('#0f1b20')
    side.set_facecolor('#0f1b20')
    im = ax.imshow(world.food, cmap='YlGn', vmin=0, vmax=7, origin='lower',
                   interpolation='nearest', extent=(0, world.config.width, 0, world.config.height))
    generation = world.generation
    ax.scatter(world.x, world.y, s=13, c=generation, cmap='cool',
               vmin=0, vmax=max(5, int(generation.max()) if len(generation) else 5),
               edgecolors='#102821', linewidths=0.2)
    # A subset of headings, to avoid obscuring resource patches.
    idx = np.arange(0, len(world.x), 8)
    ax.quiver(world.x[idx], world.y[idx], np.cos(world.angle[idx]), np.sin(world.angle[idx]),
              color='#f2e4af', pivot='middle', scale=85, width=0.003)
    ax.set_xlim(0, world.config.width); ax.set_ylim(0, world.config.height)
    ax.set_title(f'Accidental Biosphere  /  World seed {world.seed}', color='#ebefdc',
                 fontsize=17, loc='left', pad=15)
    ax.set_xlabel(f'World x ({world.config.boundary_mode})', color='#aebcaa')
    ax.set_ylabel(f'World y ({world.config.boundary_mode})', color='#aebcaa')
    ax.tick_params(colors='#aebcaa')
    for spine in ax.spines.values(): spine.set_color('#526c62')
    side.set_xlim(0, 1); side.set_ylim(0, 1); side.axis('off')
    stats = world.stats()
    notes = [
        ('SIMULATION TICK', f'{world.tick:,}'),
        ('LIVING ORGANISMS', f'{world.population:,}'),
        ('TOTAL BIRTHS', f'{world.total_births:,}'),
        ('TOTAL DEATHS', f'{world.total_deaths:,}'),
        ('MAX GENERATION', str(stats['max_generation'])),
        ('MEAN ENERGY', f"{stats['mean_energy']:.1f}"),
        ('STOCKED FOOD', f"{stats['resource_stock']:,.0f}"),
    ]
    for i, (heading, value) in enumerate(notes):
        y = .91 - i * .12
        side.text(.04, y, heading, fontsize=9, color='#abc1ad', fontfamily='DejaVu Sans')
        side.text(.04, y-.054, value, fontsize=20, color='#e8eadb', fontfamily='DejaVu Sans')
    side.text(.04, .025, 'Dots: organisms   •   Land: food stock\nColors: lineage generation   •   Arrows: headings',
              fontsize=8, color='#aec1b5')
    dest = Path(target); dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=175, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Snapshot created: {dest.resolve()}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: python experiments/plot_snapshot.py INPUT.npz OUTPUT.png')
    render(sys.argv[1], sys.argv[2])
