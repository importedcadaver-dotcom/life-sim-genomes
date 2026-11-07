"""Plot the real carrying-capacity and depleted-food maps of an evolved world.

Usage: python experiments/plot_island_maps.py checkpoints/seed_701_islands.npz output.png
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from biosphere.simulation import World  # noqa: E402


def render(source: str, target: str) -> None:
    w = World.load(source)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True, sharey=True,
                             layout='constrained')
    for ax, (title, surface) in zip(axes, (("Capacity (where food can grow)", w.capacity),
                                           ("Remaining food at saved tick", w.food))):
        image = ax.imshow(surface, cmap='YlGn', vmin=0, vmax=12,
                          origin='lower', extent=(0, w.config.width, 0, w.config.height))
        ax.scatter(w.x, w.y, s=5, color='#58459c', alpha=0.55)
        ax.set_title(title)
        ax.set_xlabel('World x')
        ax.set_ylabel('World y')
    fig.colorbar(image, ax=axes, label='Food units per grid cell', shrink=0.8)
    fig.suptitle(f'Actual evolved sparse world — seed {w.seed}, tick {w.tick}, '
                 f'{w.population} living agents', fontsize=12)
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print(path)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('Usage: plot_island_maps.py INPUT.npz OUTPUT.png')
    render(sys.argv[1], sys.argv[2])
