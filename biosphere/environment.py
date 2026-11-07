"""Experiment 003: environment topology and selection-pressure transfer.

Design locked before executing seeds 401+: four training ecologies, four matched
holdout ecologies, zero-turn ablations, and paired seed-level uncertainty.
The result is exploratory and must not be treated as proof of intelligence.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from .experiment import paired_ci, sample_genomes
from .investigation import stimulus_response
from .simulation import Config, World

# Changing only named, orthogonal features across environments. The shifting
# ecology relocates both capacity and remaining food every 35 ticks.
ECOLOGIES: dict[str, dict[str, Any]] = {
    "wrap": {},
    "reflect": {"boundary_mode": "reflect"},
    "shifting": {"patch_shift_interval": 35},
    "costly": {"move_cost": 0.75},
}
GROUPS = ("founder", *ECOLOGIES)


def _finite_mean(values: list[float]) -> float | None:
    """Never serialize an extinct genotype as a numeric zero or invalid NaN."""
    arr = np.asarray(values, dtype=float)
    available = arr[np.isfinite(arr)]
    return float(np.mean(available)) if len(available) else None


def _write_csv(filename: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with filename.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate(genomes: np.ndarray, *, seed: int, ticks: int, environment: str,
             intervention: str = "normal") -> dict[str, float | int]:
    """Hold out new terrain/placement, match within-seed comparisons exactly.

    A zero-population training result is missing, NOT zero performance.
    A dead probe organism contributes zero harvest for the remaining duration.
    """
    if environment not in ECOLOGIES:
        raise ValueError("unknown environment")
    if intervention not in ("normal", "zero_turn", "speed_fixed", "food_blind"):
        raise ValueError("unknown intervention")
    if not len(genomes):
        return {"harvest": float("nan"), "survival": float("nan"),
                "mean_speed": float("nan"), "mean_wall_hits": float("nan"),
                "energy_yield": float("nan"), "patch_moves": 0}
    cfg = Config(founders=len(genomes), max_population=len(genomes),
                 initial_energy=55.0, lifespan=ticks + 50,
                 allow_reproduction=False, allow_mutation=False,
                 **ECOLOGIES[environment])
    if intervention == "zero_turn":
        cfg = replace(cfg, fixed_turn=0.0)
    elif intervention == "speed_fixed":
        cfg = replace(cfg, fixed_speed=0.60)
    elif intervention == "food_blind":
        cfg = replace(cfg, sensor_mode="food_blind")
    world = World(cfg, seed=seed, founder_genomes=genomes)
    cumulative_speed, wall_hits = 0.0, 0
    for _ in range(ticks):
        world.step()
        cumulative_speed += world.last_mean_speed  # 0 after extinction
        wall_hits += world.last_wall_hits
    return {"harvest": world.total_harvest / (len(genomes) * ticks),
            "survival": world.population / len(genomes),
            "mean_speed": cumulative_speed / ticks,
            "mean_wall_hits": wall_hits / (len(genomes) * ticks),
            "energy_yield": (float(np.sum(world.energy)) - len(genomes) * cfg.initial_energy) /
                            (len(genomes) * ticks),
            "patch_moves": world.patch_moves}


def contrast(rows: list[dict[str, Any]], *, environment: str,
             left_group: str, right_group: str,
             metric: str = "harvest", left_intervention: str = "normal",
             right_intervention: str = "normal") -> dict[str, Any]:
    matched: dict[int, dict[tuple[str, str], float]] = {}
    for row in rows:
        if row["environment"] == environment:
            matched.setdefault(row["seed"], {})[(row["group"], row["intervention"])] = row[metric]
    differences = []
    for vals in matched.values():
        l = vals.get((left_group, left_intervention), float("nan"))
        r = vals.get((right_group, right_intervention), float("nan"))
        if np.isfinite(l) and np.isfinite(r):
            differences.append(float(l - r))
    a = np.asarray(differences)
    return {"mean": float(np.mean(a)) if len(a) else None,
            "bootstrap_95_percent_ci": list(paired_ci(a)) if len(a) else None,
            "positive_seeds": int(np.count_nonzero(a > 0)), "paired_seeds": int(len(a)),
            "per_seed_differences": a.tolist()}


def run_environment_experiment(*, seeds: list[int], steps: int, probe_ticks: int,
                               count: int, output: Path, save_checkpoints: bool = True,
                               progress: bool = True) -> dict[str, Any]:
    if not seeds or steps < 1 or probe_ticks < 1 or count < 1:
        raise ValueError("nonempty seeds, positive steps, probe_ticks, count required")
    output.mkdir(parents=True, exist_ok=True)
    if save_checkpoints:
        (output / "checkpoints").mkdir(exist_ok=True)
    training: list[dict[str, Any]] = []
    evaluations: list[dict[str, Any]] = []
    response: list[dict[str, Any]] = []
    for seed in seeds:
        # Each training condition begins with precisely the same initial
        # genome population, landscape, location and random generator seed.
        founder = World(Config(), seed=seed)
        populations = {"founder": sample_genomes(founder.genomes, count, seed + 123_000)}
        for env, overrides in ECOLOGIES.items():
            world = World(Config(**overrides), seed=seed)
            for _ in range(steps):
                world.step()
            stats = world.stats(detailed=False)
            training.append({"seed": seed, "environment": env,
                             "population": world.population, "births": world.total_births,
                             "starvation_deaths": world.death_causes["starvation"],
                             "mean_generation": stats["mean_generation"],
                             "mean_energy": stats["mean_energy"],
                             "patch_moves": world.patch_moves,
                             "wall_hits": world.cumulative_wall_hits})
            populations[env] = sample_genomes(world.genomes, count, seed + 123_000)
            if save_checkpoints:
                world.save(output / "checkpoints" / f"seed_{seed}_{env}.npz")
        for group, genomes in populations.items():
            response.append({"seed": seed, "group": group,
                             "n": int(len(genomes)), **stimulus_response(genomes)})
        for evaluation_env in ECOLOGIES:
            # Use novel common-garden seed, not training landscape.
            trial_seed = seed + 54_000
            for group, genomes in populations.items():
                result = evaluate(genomes, seed=trial_seed,
                                  ticks=probe_ticks, environment=evaluation_env)
                evaluations.append({"seed": seed, "environment": evaluation_env,
                                    "group": group, "intervention": "normal",
                                    "count": len(genomes), **result})
            # Agent movement/sensing controls on the *same* evolved genomes.
            for intervention in ("zero_turn", "speed_fixed", "food_blind"):
                genomes = populations["wrap"]
                result = evaluate(genomes, seed=trial_seed,
                                  ticks=probe_ticks, environment=evaluation_env,
                                  intervention=intervention)
                evaluations.append({"seed": seed, "environment": evaluation_env,
                                    "group": "wrap", "intervention": intervention,
                                    "count": len(genomes), **result})
        if progress:
            print(f"seed {seed}: " + " ".join(f"{r['environment']}={r['population']}"
                                            for r in training[-len(ECOLOGIES):]), flush=True)

    _write_csv(output / "training.csv", training)
    _write_csv(output / "holdout.csv", evaluations)
    _write_csv(output / "controller.csv", response)
    planned = [
        ("wrap_evolution", "wrap", "wrap", "founder", "harvest", "normal", "normal"),
        ("reflect_evolution", "reflect", "reflect", "founder", "harvest", "normal", "normal"),
        ("shifting_evolution", "shifting", "shifting", "founder", "harvest", "normal", "normal"),
        ("costly_evolution", "costly", "costly", "founder", "harvest", "normal", "normal"),
        ("reflect_local_adaptation", "reflect", "reflect", "wrap", "harvest", "normal", "normal"),
        ("shifting_local_adaptation", "shifting", "shifting", "wrap", "harvest", "normal", "normal"),
        ("costly_local_adaptation", "costly", "costly", "wrap", "energy_yield", "normal", "normal"),
        ("reflect_generalist_cost", "wrap", "reflect", "wrap", "harvest", "normal", "normal"),
        ("zero_turn_wrap", "wrap", "wrap", "wrap", "harvest", "zero_turn", "normal"),
        ("zero_turn_reflect", "reflect", "wrap", "wrap", "harvest", "zero_turn", "normal"),
        ("zero_turn_shifting", "shifting", "wrap", "wrap", "harvest", "zero_turn", "normal"),
        ("zero_turn_costly", "costly", "wrap", "wrap", "harvest", "zero_turn", "normal"),
        ("fixed_speed_wrap", "wrap", "wrap", "wrap", "harvest", "speed_fixed", "normal"),
        ("fixed_speed_reflect", "reflect", "wrap", "wrap", "harvest", "speed_fixed", "normal"),
    ]
    contrasts = {key: contrast(evaluations, environment=env, left_group=left, right_group=right,
                                metric=metric, left_intervention=left_int,
                                right_intervention=right_int)
                 for key, env, left, right, metric, left_int, right_int in planned}
    summary = {"experiment": "003: boundary conditions, shifting habitats, movement-energy costs",
               "design": "exploratory; independent training seeds; novel matched holdout environments; same founders across training worlds; unmodified 16-gene controllers",
               "settings": {"seeds": seeds, "training_steps": steps, "probe_ticks": probe_ticks,
                            "genome_sample": count, "ecologies": ECOLOGIES,
                            "default_config": asdict(Config())},
               "training": {env: {"mean_population": float(np.mean([r["population"] for r in training if r["environment"] == env])),
                                  "extinctions": sum(r["population"] == 0 for r in training if r["environment"] == env),
                                  "replicates": len(seeds)} for env in ECOLOGIES},
               "contrasts": contrasts,
               "holdout_means": {env: {group: _finite_mean([r["harvest"] for r in evaluations if r["environment"] == env and r["group"] == group and r["intervention"] == "normal"])
                                       for group in GROUPS} for env in ECOLOGIES},
               "response_means": {group: {metric: _finite_mean([r[metric] for r in response if r["group"] == group])
                                          for metric in ("baseline_speed", "directional_cue_response")}
                                  for group in GROUPS}}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    try:
        plot_results(output, evaluations, response)
    except ImportError:
        pass
    return summary


def plot_results(output: Path, rows: list[dict], controller: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(ECOLOGIES)
    means = np.array([[np.mean([r["harvest"] for r in rows if r["environment"] == env and
                                    r["group"] == group and r["intervention"] == "normal"])
                       for env in names] for group in GROUPS])
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    img = ax.imshow(means, aspect="auto", cmap="viridis")
    ax.set_xticks(range(4), ["Wrap", "Reflect", "Moving patches", "Expensive motion"])
    ax.set_yticks(range(5), ["Founders", "Evolved: wrap", "Evolved: reflect", "Evolved: moving", "Evolved: costly"])
    for i in range(5):
        for j in range(4):
            ax.text(j, i, f"{means[i, j]:.3f}", ha="center", va="center",
                    color="white" if means[i, j] < np.mean(means) else "black")
    fig.colorbar(img, ax=ax, label="Harvest per initial organism per step")
    ax.set_title("Transfer of evolved genomes across novel ecosystems")
    fig.savefig(output / "transfer_matrix.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    for j, env in enumerate(names):
        normal = {r["seed"]: r["harvest"] for r in rows if r["environment"] == env and r["group"] == "wrap" and r["intervention"] == "normal"}
        zero = {r["seed"]: r["harvest"] for r in rows if r["environment"] == env and r["group"] == "wrap" and r["intervention"] == "zero_turn"}
        diff = [zero[k] - normal[k] for k in normal if k in zero]
        ax.scatter(np.full(len(diff), j), diff, alpha=.5)
        ax.plot([j-.18,j+.18], [np.mean(diff)]*2, color="black", linewidth=3)
    ax.set_xticks(range(4), ["Wrap", "Reflect", "Moving patches", "Expensive motion"])
    ax.axhline(0, color="gray", linewidth=1)
    ax.set(ylabel="No-turn minus learned-turn harvest", title="Is steering beneficial after changing the environment?")
    fig.savefig(output / "zero_turn_by_ecology.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.6), layout="constrained")
    for i, group in enumerate(GROUPS):
        values = [r["baseline_speed"] for r in controller if r["group"] == group]
        ax.scatter(np.full(len(values), i), values, alpha=.5)
        ax.plot([i-.20, i+.20], [np.mean(values)]*2, color="black", linewidth=3)
    ax.set_xticks(range(5), ["Founders", "Wrap", "Reflect", "Moving", "Costly"])
    ax.set(ylabel="Synthetic neutral-cue speed", title="Inherited motor outputs after selection")
    fig.savefig(output / "controller_speed.png", dpi=160); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=401)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--steps", type=int, default=900)
    parser.add_argument("--probe-ticks", type=int, default=160)
    parser.add_argument("--count", type=int, default=160)
    parser.add_argument("--output", type=Path, default=Path("results/experiment_003"))
    parser.add_argument("--no-checkpoints", action="store_true")
    args = parser.parse_args()
    summary = run_environment_experiment(
        seeds=list(range(args.seed_start, args.seed_start + args.seeds)),
        steps=args.steps, probe_ticks=args.probe_ticks, count=args.count,
        output=args.output, save_checkpoints=not args.no_checkpoints)
    print(json.dumps({"training": summary["training"], "contrasts": summary["contrasts"]}, indent=2))


if __name__ == "__main__":
    main()
