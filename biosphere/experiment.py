"""Controlled common-garden experiments, with paired replicated trials.

IMPORTANT: Successful population growth is not automatically proof of novel
behavior. Interventions isolate response to resource sensing from plain selection.
"""
from __future__ import annotations
from dataclasses import replace
import csv
import json
from pathlib import Path
import numpy as np
from .simulation import Config, World, SENSORS


def sample_genomes(genomes: np.ndarray, count: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    if not len(genomes):
        return np.empty((0, 2, len(SENSORS)))
    return genomes[rng.choice(len(genomes), count, replace=len(genomes) < count)].copy()


def probe(genomes: np.ndarray, seed: int, ticks: int, *, blind: bool = False) -> dict[str, float]:
    """Novel environment, matched starting coordinates across all treatments.

    No births or mutations; mean harvest per starting organism/tick is the response.
    Individuals that die contribute zero to the remaining interval.
    """
    cfg = Config(founders=len(genomes), max_population=len(genomes),
                 initial_energy=55.0, lifespan=ticks + 15,
                 allow_reproduction=False, allow_mutation=False,
                 sensor_mode="blind" if blind else "normal")
    w = World(cfg, seed=seed, founder_genomes=genomes)
    total = 0.0
    total_directional = 0.0
    total_speed = 0.0
    for _ in range(ticks):
        w.step()
        total += w.last_total_intake
        total_directional += w.last_directionality
        total_speed += w.last_mean_speed
    return {"harvest": total / (len(genomes) * ticks) if len(genomes) else 0.0,
            "survival": w.population / len(genomes) if len(genomes) else 0.0,
            "final_energy": float(np.mean(w.energy)) if w.population else 0.0,
            "directionality": total_directional / ticks,
            "mean_speed": total_speed / ticks}


def paired_ci(values: np.ndarray, seed: int = 781) -> tuple[float, float]:
    if len(values) == 0:
        return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, (4000, len(values)), replace=True).mean(axis=1)
    return tuple(map(float, np.quantile(samples, [0.025, 0.975])))


def run_experiment(args) -> None:
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    all_rows = []
    history = []
    for seed in range(1, args.seeds + 1):
        train = World(Config(), seed=seed)
        ancestor = train.genomes.copy()
        control = World(Config(allow_mutation=False), seed=seed)
        for t in range(args.steps):
            train.step()
            control.step()
            if (t + 1) % 100 == 0 or t == 0:
                for mode, world in (("mutating", train), ("nonmutating", control)):
                    history.append({"seed": seed, "condition": mode, **world.stats()})
            if train.population == 0 and control.population == 0:
                break
        # Reproduce valid negative results: don't quietly replace extinction.
        count = 220
        ancestor_genes = sample_genomes(ancestor, count, seed + 200)
        evolved_genes = sample_genomes(train.genomes, count, seed + 200)
        no_mutation_genes = sample_genomes(control.genomes, count, seed + 200)
        choices = {"ancestor": ancestor_genes,
                   "ancestor_blind": ancestor_genes,
                   "evolved": evolved_genes,
                   "evolved_blind": evolved_genes,
                   "no_mutation": no_mutation_genes,
                   "no_mutation_blind": no_mutation_genes}
        if train.population:
            train.save(out / f"evolved_seed_{seed}.npz")
        for treatment, genes in choices.items():
            measurement = probe(genes, seed=11000 + seed, ticks=args.probe_ticks,
                                blind=treatment.endswith("_blind"))
            all_rows.append({"seed": seed, "treatment": treatment,
                             "training_population": train.population if treatment != "no_mutation" else control.population,
                             "training_max_generation": train.stats()["max_generation"] if treatment != "no_mutation" else control.stats()["max_generation"],
                             "count": len(genes), **measurement})
        print(f"Seed {seed}/{args.seeds}: " + " ".join(
            f"{r['treatment']}={r['harvest']:.4f}" for r in all_rows[-6:]))
    with (out / "probe_trials.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0])); writer.writeheader(); writer.writerows(all_rows)
    with (out / "training_history.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(history[0])); writer.writeheader(); writer.writerows(history)
    contrasts = {}
    for label, numerator, denominator in (("evolution_vs_ancestor", "evolved", "ancestor"),
                                          ("sensor_utility", "evolved", "evolved_blind"),
                                          ("mutation_effect", "evolved", "no_mutation"),
                                          ("ancestor_sensor_utility", "ancestor", "ancestor_blind"),
                                          ("no_mutation_sensor_utility", "no_mutation", "no_mutation_blind")):
        paired = np.array([next(r['harvest'] for r in all_rows if r['seed'] == seed and r['treatment'] == numerator) -
                           next(r['harvest'] for r in all_rows if r['seed'] == seed and r['treatment'] == denominator)
                           for seed in range(1, args.seeds + 1)])
        contrasts[label] = {"difference": float(np.mean(paired)),
                            "bootstrap_95_percent_ci": paired_ci(paired),
                            "wins": int(np.sum(paired > 0)), "trials": args.seeds,
                            "per_seed_differences": paired.tolist()}
    ev = contrasts["sensor_utility"]["per_seed_differences"]
    an = contrasts["ancestor_sensor_utility"]["per_seed_differences"]
    sensory_gain = np.array(ev) - np.array(an)
    contrasts["increase_in_sensor_utility"] = {"difference": float(np.mean(sensory_gain)),
                                                  "bootstrap_95_percent_ci": paired_ci(sensory_gain),
                                                  "wins": int(np.sum(sensory_gain > 0)),
                                                  "trials": args.seeds,
                                                  "per_seed_differences": sensory_gain.tolist()}
    summary = {"training_ticks": args.steps, "probe_ticks": args.probe_ticks,
               "seeds": args.seeds, "experimental_design": "paired seeds; novel-world common garden; identical starts; independent organisms",
               "treatment_means": {key: float(np.mean([r['harvest'] for r in all_rows if r['treatment'] == key]))
                                   for key in ("ancestor", "ancestor_blind", "evolved", "evolved_blind", "no_mutation", "no_mutation_blind")},
               "contrasts": contrasts}
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
        ticks = ["ancestor", "ancestor_blind", "evolved", "evolved_blind", "no_mutation", "no_mutation_blind"]
        # Keep standard Matplotlib default palette; raw replicated points shown.
        for i, treatment in enumerate(ticks):
            vals = [r['harvest'] for r in all_rows if r['treatment'] == treatment]
            ax.scatter(np.full(len(vals), i), vals, alpha=0.5, s=28)
            ax.plot([i - .20, i + .20], [np.mean(vals)] * 2, color="black", linewidth=2)
        ax.set_xticks(range(6), ["Founder", "Founder, blind", "Evolved", "Evolved, blind", "No mutation", "No mutation, blind"], rotation=16)
        ax.set_ylabel("Mean food harvested / organism / step")
        ax.set_title("Novel common-garden performance across paired seeds")
        fig.savefig(out / "common_garden.png", dpi=170)
        plt.close(fig)
        fig, ax = plt.subplots(figsize=(9, 4.6), layout="constrained")
        for condition in ("mutating", "nonmutating"):
            times = sorted({r['tick'] for r in history})
            y = [np.mean([r['population'] for r in history if r['condition'] == condition and r['tick'] == t])
                 for t in times]
            ax.plot(times, y, label=condition)
        ax.legend(); ax.set_xlabel("Tick"); ax.set_ylabel("Living organisms")
        ax.set_title("Training population dynamics (seed averages)")
        fig.savefig(out / "population_dynamics.png", dpi=170)
        plt.close(fig)
    except ImportError:
        pass
    print(json.dumps(summary["contrasts"], indent=2))
