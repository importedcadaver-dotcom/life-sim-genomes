"""Experiment 002: independent holdout, motor interventions and regrowth scarcity.

No intelligence or navigational strategy is inferred from harvesting alone. The
run is intentionally deterministic for a specified seed range and parameters.
The independent unit of replication is the evolutionary training seed.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any

import numpy as np

from .experiment import paired_ci, sample_genomes
from .simulation import Config, SENSORS, World

# Frozen before seeing new seed 101+ results. A low-regrowth environment has
# the same initial land/food capacity; food scarcity arises from depletion.
TRAINING_REGROWTH = (0.030, 0.012, 0.006, 0.003, 0.001)
PROBE_REGROWTH = (0.030, 0.006)
INTERVENTIONS = (
    "founder", "evolved", "founder_speed_fixed", "evolved_speed_fixed",
    "founder_no_steering", "evolved_no_steering", "evolved_food_blind",
    "evolved_mirror_food", "evolved_crowd_blind",
)


def cue_sensors(ahead: float, left: float, right: float, *,
                energy_fraction: float = 1.0, crowd: float = 0.0) -> np.ndarray:
    """Internally coherent synthetic 8-channel neural input."""
    return np.array([1.0, ahead, left, right, ahead - (left + right) / 2,
                     left - right, energy_fraction, crowd], dtype=float)


def motor_outputs(genomes: np.ndarray, senses: np.ndarray,
                  cfg: Config | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Calculate original controller physics without moving the organisms."""
    cfg = cfg or Config()
    raw = np.einsum("nij,j->ni", genomes, senses)
    turn = np.tanh(raw[:, 0]) * cfg.max_turn
    speed = (0.05 + 0.95 / (1 + np.exp(-np.clip(raw[:, 1], -20, 20)))) * cfg.max_speed
    return turn, speed


def stimulus_response(genomes: np.ndarray) -> dict[str, float]:
    """Positive directional score means turning toward the richer side.

    This is a controlled motor-output property, not proof of food navigation.
    A constant left-turn tendency cancels out of the left/right difference.
    """
    if not len(genomes):
        return {"directional_cue_response": float("nan"),
                "baseline_speed": float("nan"), "motor_speed_while_hungry": float("nan")}
    left = cue_sensors(.3, .85, .15)
    right = cue_sensors(.3, .15, .85)
    neutral = cue_sensors(.3, .5, .5)
    tl, _ = motor_outputs(genomes, left)
    tr, _ = motor_outputs(genomes, right)
    _, speeds = motor_outputs(genomes, neutral)
    _, hungry_speeds = motor_outputs(genomes, cue_sensors(.3, .5, .5, energy_fraction=.2))
    return {"directional_cue_response": float(np.mean((tl - tr) / 2)),
            "baseline_speed": float(np.mean(speeds)),
            "motor_speed_while_hungry": float(np.mean(hungry_speeds))}


def effective_gene_weights(genomes: np.ndarray) -> np.ndarray:
    """Eliminate redundant food contrasts to obtain effective raw cue weights.

    Input 4 = ahead - (left + right)/2; input 5 = left - right.
    Raw weights cannot be individually interpreted when inputs are redundant.
    Returns [motor, ahead/left/right, energy, crowd, bias] effective weights.
    """
    # [MOTOR, channels] effective genetic weights
    if not len(genomes):
        return np.empty((0, 2, 6))
    g = genomes
    return np.stack((g[:, :, 1] + g[:, :, 4],
                     g[:, :, 2] - .5 * g[:, :, 4] + g[:, :, 5],
                     g[:, :, 3] - .5 * g[:, :, 4] - g[:, :, 5],
                     g[:, :, 6], g[:, :, 7], g[:, :, 0]), axis=2)


def run_probe(genomes: np.ndarray, seed: int, ticks: int,
              regrowth: float, *, intervention: str = "normal", sample_count: int = 180,
              patchiness: float = 1.0) -> dict[str, float]:
    """Matched initial placement, terrain and initial energies for all treatments.

    A zero-genome group means the source population went extinct; do not silently
    resurrect it or call its zero score a measurement of its extinct controller.
    """
    if not len(genomes):
        return {"harvest": float("nan"), "survival": float("nan"),
                "mean_speed": float("nan"), "final_energy": float("nan")}
    config = Config(founders=len(genomes), max_population=max(len(genomes), sample_count),
                    initial_energy=55, lifespan=ticks + 50, allow_reproduction=False,
                    allow_mutation=False, growth_rate=regrowth,
                    resource_patchiness=patchiness)
    if intervention == "fixed_speed":
        config = replace(config, fixed_speed=0.60)
    elif intervention == "no_steering":
        config = replace(config, fixed_turn=0.0)
    elif intervention in ("food_blind", "mirror_food", "crowd_blind"):
        config = replace(config, sensor_mode=intervention)
    elif intervention != "normal":
        raise ValueError("Invalid intervention")
    world = World(config, seed=seed, founder_genomes=genomes)
    total_speed = 0.0
    for _ in range(ticks):
        world.step()
        total_speed += world.last_mean_speed
    return {"harvest": world.total_harvest / (len(genomes) * ticks),
            "survival": world.population / len(genomes),
            "mean_speed": total_speed / ticks,
            "final_energy": float(np.mean(world.energy)) if world.population else 0.0}


def append_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        w = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def paired_contrast(rows: list[dict[str, Any]], left: str, right: str,
                    *, metric: str = "harvest", ecology: float = 0.03) -> dict[str, Any]:
    by_seed = {}
    for r in rows:
        if r["probe_growth_rate"] == ecology and r["treatment"] in (left, right):
            by_seed.setdefault(r["seed"], {})[r["treatment"]] = float(r[metric])
    differences = np.array([v[left] - v[right] for v in by_seed.values()
                            if left in v and right in v and
                            np.isfinite(v[left]) and np.isfinite(v[right])])
    if len(differences) == 0:
        return {"mean": None, "bootstrap_95_percent_ci": None,
                "positive_seeds": 0, "paired_seeds": 0}
    return {"mean": float(np.mean(differences)),
            "bootstrap_95_percent_ci": list(paired_ci(differences)),
            "positive_seeds": int(np.sum(differences > 0)),
            "paired_seeds": len(differences)}


def run_investigation(*, seeds: list[int], steps: int, probe_ticks: int,
                      output: Path, regrowths: tuple[float, ...] = TRAINING_REGROWTH,
                      probe_regrowths: tuple[float, ...] = PROBE_REGROWTH,
                      count: int = 180, save_checkpoints: bool = True) -> dict[str, Any]:
    if not seeds or steps < 1 or probe_ticks < 1 or count < 1:
        raise ValueError("seeds, steps, probe_ticks and count must be nonempty/positive")
    output.mkdir(parents=True, exist_ok=True)
    if save_checkpoints:
        (output / "checkpoints").mkdir(exist_ok=True)
    evaluations: list[dict[str, Any]] = []
    training: list[dict[str, Any]] = []
    responses: list[dict[str, Any]] = []
    gene_rows: list[dict[str, Any]] = []

    for seed in seeds:
        founder = World(Config(), seed=seed)
        founder_genes = sample_genomes(founder.genomes, count, seed + 81000)
        sample_sets: dict[float, np.ndarray] = {}
        for rate in regrowths:
            cfg = Config(growth_rate=rate)
            world = World(cfg, seed=seed)
            for i in range(steps):
                world.step()
            training.append({"seed": seed, "growth_rate": rate, "tick": world.tick,
                             "population": world.population, "births": world.total_births,
                             "starvation_deaths": world.death_causes["starvation"],
                             "age_deaths": world.death_causes["age"],
                             "max_generation": world.stats(detailed=False)["max_generation"],
                             "mean_energy": world.stats(detailed=False)["mean_energy"]})
            sample_sets[rate] = sample_genomes(world.genomes, count, seed + 81000)
            if save_checkpoints and (rate == 0.03 or rate == 0.006):
                world.save(output / "checkpoints" / f"seed_{seed}_growth_{rate:.3f}.npz")

        baseline = sample_sets[0.03]
        genome_groups = {"founder": founder_genes, "evolved": baseline}
        for label, genomes in genome_groups.items():
            responses.append({"seed": seed, "source": label, **stimulus_response(genomes)})
            wg = effective_gene_weights(genomes)
            for mi, mname in enumerate(("turn", "speed")):
                for gi, gname in enumerate(("ahead", "left", "right", "energy", "crowd", "bias")):
                    gene_rows.append({"seed": seed, "source": label, "motor": mname,
                                      "cue": gname, "mean_effective_weight": float(np.mean(wg[:, mi, gi])),
                                      "mean_absolute_effective_weight": float(np.mean(np.abs(wg[:, mi, gi])))})

        # Same held-out landscape for all genotypes/ablation treatments within
        # one training seed, but new from training world. Seed + 31k is disjoint.
        tests = (
            ("founder", founder_genes, "normal"),
            ("evolved", baseline, "normal"),
            ("founder_speed_fixed", founder_genes, "fixed_speed"),
            ("evolved_speed_fixed", baseline, "fixed_speed"),
            ("founder_no_steering", founder_genes, "no_steering"),
            ("evolved_no_steering", baseline, "no_steering"),
            ("evolved_food_blind", baseline, "food_blind"),
            ("evolved_mirror_food", baseline, "mirror_food"),
            ("evolved_crowd_blind", baseline, "crowd_blind"),
        )
        for ecology in probe_regrowths:
            for label, genomes, intervention in tests:
                result = run_probe(genomes, seed + 31000, probe_ticks, ecology,
                                   intervention=intervention, sample_count=count)
                evaluations.append({"seed": seed, "probe_growth_rate": ecology,
                                    "treatment": label, "count": len(genomes), **result})
            # Compare adaptation to regrowth in the *same* food environment:
            # change only the source ecology, not the test world.
            for rate in regrowths:
                if rate == 0.03:
                    continue
                genomes = sample_sets[rate]
                measurement = run_probe(genomes, seed + 31000, probe_ticks, ecology,
                                        sample_count=count)
                evaluations.append({"seed": seed, "probe_growth_rate": ecology,
                                    "treatment": f"trained_regrowth_{rate:.3f}",
                                    "count": len(genomes), **measurement})
        print(f"seed {seed}: "+" ".join(f"g={r['growth_rate']:.3f}:N={r['population']}"
                         for r in training[-len(regrowths):]), flush=True)

    append_csv(output / "training_outcomes.csv", training)
    append_csv(output / "probe_trials.csv", evaluations)
    append_csv(output / "controller_responses.csv", responses)
    append_csv(output / "effective_genes.csv", gene_rows)

    def response_difference(key: str) -> dict[str, Any]:
        diffs = []
        for seed in seeds:
            pairs = {r["source"]: r[key] for r in responses if r["seed"] == seed}
            if np.isfinite(pairs["evolved"]) and np.isfinite(pairs["founder"]):
                diffs.append(pairs["evolved"] - pairs["founder"])
        d = np.array(diffs)
        return {"founder_mean": float(np.mean([r[key] for r in responses if r["source"] == "founder"])),
                "evolved_mean": float(np.mean([r[key] for r in responses if r["source"] == "evolved"])),
                "difference": float(np.mean(d)),
                "bootstrap_95_percent_ci": list(paired_ci(d)),
                "positive_seeds": int(np.sum(d > 0)), "paired_seeds": len(d)}

    summary: dict[str, Any] = {
        "experiment": "002: novel seeds, direct controller assays, sensor/motor ablations, scarcity",
        "design": "exploratory, no model retuning after selecting seeds; paired by independent training seed",
        "parameters": {"training_seeds": seeds, "steps": steps, "probe_ticks": probe_ticks,
                       "sample_count": count, "training_regrowth": regrowths,
                       "probe_regrowth": probe_regrowths, "fixed_speed": 0.60,
                       "default_config": asdict(Config())},
        "controller": {key: response_difference(key) for key in
                       ("directional_cue_response", "baseline_speed", "motor_speed_while_hungry")},
        "harvest_contrasts": {}, "training_scarcity": {},
    }
    for ecology in probe_regrowths:
        contrasts = {}
        for left, right in (
            ("evolved", "founder"),
            ("evolved_speed_fixed", "founder_speed_fixed"),
            ("evolved_no_steering", "founder_no_steering"),
            ("evolved", "evolved_food_blind"),
            ("evolved", "evolved_mirror_food"),
            ("evolved", "evolved_crowd_blind"),
            ("evolved", "evolved_speed_fixed"),
            ("evolved", "evolved_no_steering"),
        ):
            contrasts[f"{left}_minus_{right}"] = paired_contrast(evaluations, left, right, ecology=ecology)
        for rate in regrowths:
            if rate != 0.03:
                label = f"trained_regrowth_{rate:.3f}"
                contrasts[f"{label}_minus_abundant_trained"] = paired_contrast(
                    evaluations, label, "evolved", ecology=ecology)
        summary["harvest_contrasts"][f"growth_{ecology:.3f}"] = contrasts
    for rate in regrowths:
        t = [r for r in training if r["growth_rate"] == rate]
        summary["training_scarcity"][f"growth_{rate:.3f}"] = {
            "extinctions": sum(r["population"] == 0 for r in t),
            "replicates": len(t), "mean_final_population": float(np.mean([r["population"] for r in t])),
            "mean_births": float(np.mean([r["births"] for r in t])),
            "mean_starvation_deaths": float(np.mean([r["starvation_deaths"] for r in t]))}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    try:
        plot_results(output, training, evaluations, responses)
    except ImportError:
        pass
    return summary


def plot_results(output: Path, training: list[dict], trials: list[dict], responses: list[dict]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    seeds = sorted({r["seed"] for r in training})
    rates = sorted({r["growth_rate"] for r in training}, reverse=True)
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    for seed in seeds:
        ax.plot(rates, [next(r["population"] for r in training if r["seed"] == seed and r["growth_rate"] == rate)
                        for rate in rates], alpha=.24)
    ax.plot(rates, [np.mean([r["population"] for r in training if r["growth_rate"] == rate])
                    for rate in rates], linewidth=3, color="black", label="Mean across seeds")
    ax.set(xlabel="Food regrowth fraction / tick", ylabel="Final living population",
           title="Population viability when food regrows more slowly")
    ax.legend(); fig.savefig(output / "scarcity_population.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    treatments = ("founder", "evolved", "founder_speed_fixed", "evolved_speed_fixed",
                  "founder_no_steering", "evolved_no_steering", "evolved_food_blind", "evolved_mirror_food")
    ecology = 0.03
    for i, name in enumerate(treatments):
        v = [r["harvest"] for r in trials if r["treatment"] == name and r["probe_growth_rate"] == ecology]
        ax.scatter(np.full(len(v), i), v, alpha=.4, s=22)
        ax.plot([i-.22, i+.22], [np.nanmean(v)]*2, color="black", linewidth=2)
    ax.set_xticks(range(len(treatments)), ("Founder", "Evolved", "Founder fixed\nspeed", "Evolved fixed\nspeed",
                   "Founder zero\nturn", "Evolved zero\nturn", "Evolved food\nblind", "Evolved mirror\nfood"))
    ax.set_ylabel("Harvest / starting organism / tick")
    ax.set_title("Holdout ecology: separate speed, steering and sensing")
    fig.savefig(output / "causal_ablations.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5), layout="constrained")
    for seed in seeds:
        f = next(r for r in responses if r["seed"] == seed and r["source"] == "founder")
        e = next(r for r in responses if r["seed"] == seed and r["source"] == "evolved")
        ax.plot([0, 1], [f["directional_cue_response"], e["directional_cue_response"]], alpha=.25)
    for j, src in enumerate(("founder", "evolved")):
        vals = [r["directional_cue_response"] for r in responses if r["source"] == src]
        ax.scatter(np.full(len(vals),j), vals, alpha=.5)
        ax.plot([j-.1, j+.1], [np.mean(vals)]*2, color="black", linewidth=3)
    ax.axhline(0, linewidth=1, color="gray")
    ax.set_xticks([0,1], ["Founders", "Evolved"])
    ax.set_ylabel("Positive = turn toward richer lateral cue (radians/tick)")
    ax.set_title("Direct synthetic-cue steering assay (not natural navigation)")
    fig.savefig(output / "cue_steering.png", dpi=170); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    for ecology in (0.030, 0.006):
        if ecology not in {r["probe_growth_rate"] for r in trials}:
            continue
        names = ["founder", "evolved", "trained_regrowth_0.012", "trained_regrowth_0.006", "trained_regrowth_0.003"]
        averages = []
        for name in names:
            vals = [r["harvest"] for r in trials if r["probe_growth_rate"] == ecology
                    and r["treatment"] == name and np.isfinite(r["harvest"])]
            averages.append(float(np.mean(vals)) if vals else float('nan'))
        ax.plot(range(len(names)), averages, marker="o", label=f"probe regrowth={ecology:.3f}")
    ax.set_xticks(range(5), ["Founder", "Abundant", "0.012", "0.006", "0.003"])
    ax.set(xlabel="Source training condition", ylabel="Harvest / organism / tick",
           title="Scarcity transfer in fresh worlds (extinct training runs excluded)")
    ax.legend(); fig.savefig(output / "scarcity_transfer.png", dpi=170); plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-start", type=int, default=101)
    parser.add_argument("--seeds", type=int, default=18)
    parser.add_argument("--steps", type=int, default=1200)
    parser.add_argument("--probe-ticks", type=int, default=240)
    parser.add_argument("--output", type=Path, default=Path("results/experiment_002"))
    args = parser.parse_args()
    result = run_investigation(seeds=list(range(args.seed_start, args.seed_start + args.seeds)),
                               steps=args.steps, probe_ticks=args.probe_ticks,
                               output=args.output)
    print(json.dumps({"controller": result["controller"],
                      "scarcity": result["training_scarcity"],
                      "abundant_contrasts": result["harvest_contrasts"]["growth_0.030"]}, indent=2))


if __name__ == "__main__":
    main()
