"""Pre-specified experiment 008, evolving matched controllers with/without food cues.

Only calls the unmodified World.step ecological machinery. No UI or cheats.
"""
from __future__ import annotations

import csv
from dataclasses import asdict, replace
from io import BytesIO
import json
from pathlib import Path

import numpy as np

from .simulation import Config, World


def clone(source: World) -> World:
    buf = BytesIO()
    source.save(buf)
    buf.seek(0)
    return World.load(buf)


def training_pair(seed: int, *, steps: int, config: Config) -> dict[str, World]:
    base = World(config, seed=seed)
    normal, blind = clone(base), clone(base)
    blind.config = replace(blind.config, sensor_mode="food_blind")
    for _ in range(steps):
        normal.step()
        blind.step()
    return {"normal": normal, "blind": blind}


def common_garden(train: World, seed: int, *, count: int = 60,
                  eval_ticks: int = 280, mode: str = "normal") -> dict | None:
    if not train.population:
        return None
    picker = np.random.default_rng([seed, 447, 5 if train.config.sensor_mode == "normal" else 7])
    sampled = picker.choice(train.population, size=count, replace=True)
    genomes = train.genomes[sampled].copy()
    cfg = replace(train.config, founders=count, max_population=300,
                  sensor_mode=mode, allow_mutation=False)
    w = World(cfg, seed=seed, founder_genomes=genomes)
    for _ in range(eval_ticks):
        w.step()
    return {"births_per_founder": w.total_births / count,
            "births": w.total_births, "deaths": w.total_deaths,
            "population": w.population, "extinct": w.population == 0,
            "mean_harvest": w.total_harvest / count / max(1, w.tick)}


def run(*, seeds=range(1101, 1113), train_ticks=550, eval_ticks=280,
        output: str | Path = "results/experiment_008") -> dict:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    cfg = Config(founders=96, max_population=300, growth_rate=0.012,
                 resource_layout="islands", island_count=7, island_sigma=3.0,
                 resource_background=0.01, move_cost=0.45)
    rows: list[dict] = []
    for seed in seeds:
        pair = training_pair(int(seed), steps=train_ticks, config=cfg)
        for train_condition, trained in pair.items():
            for evaluation in ("normal", "food_blind"):
                result = common_garden(trained, int(seed) + 90000,
                                       eval_ticks=eval_ticks, mode=evaluation)
                rows.append({"seed": int(seed), "training": train_condition,
                             "evaluation": evaluation,
                             "training_survivors": trained.population,
                             "training_births": trained.total_births,
                             **(result or {"births_per_founder": "", "births": "",
                                          "deaths": "", "population": "", "extinct": "",
                                          "mean_harvest": ""})})
    with (out / "trials.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    matched = []
    for seed in seeds:
        a = next(r for r in rows if r['seed'] == seed and r['training'] == 'normal'
                 and r['evaluation'] == 'normal')
        b = next(r for r in rows if r['seed'] == seed and r['training'] == 'blind'
                 and r['evaluation'] == 'normal')
        if a['births_per_founder'] != "" and b['births_per_founder'] != "":
            matched.append({"seed": int(seed), "sensor_trained": a['births_per_founder'],
                            "blind_trained": b['births_per_founder'],
                            "paired_difference": a['births_per_founder'] - b['births_per_founder']})
    diffs = np.array([r['paired_difference'] for r in matched], dtype=float)
    summary = {"preregistered_plan": "docs/EXPERIMENT_008_PLAN.md",
               "train_ticks": train_ticks, "eval_ticks": eval_ticks,
               "training_config": asdict(cfg), "seeds": [int(x) for x in seeds],
               "trials": len(rows), "matched_pairs_survived": len(matched),
               "primary_paired": matched,
               "mean_difference": float(np.mean(diffs)) if len(diffs) else None,
               "positive_pairs": int(np.count_nonzero(diffs > 0)),
               "negative_pairs": int(np.count_nonzero(diffs < 0)),
               "note": "Descriptive result of sensor-training selection on reproduction; not a test of consciousness."}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed-start', type=int, default=1101)
    parser.add_argument('--seeds', type=int, default=12)
    parser.add_argument('--train-ticks', type=int, default=550)
    parser.add_argument('--eval-ticks', type=int, default=280)
    parser.add_argument('--output', type=Path, default=Path('results/experiment_008'))
    args = parser.parse_args()
    print(json.dumps(run(seeds=range(args.seed_start, args.seed_start + args.seeds),
                         train_ticks=args.train_ticks, eval_ticks=args.eval_ticks,
                         output=args.output), indent=2))
