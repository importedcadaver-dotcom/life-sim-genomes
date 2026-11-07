"""Experiment 004: sparse targets, movement costs, and the limits of evolved steering.

All manipulation of targets and motor controls happens only in experiments.
The organism's neural network is unchanged: 16 inherited weights, no foraging rules.
Matched-seed comparisons use independent evolving populations as replicate units.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np

from .environment import _finite_mean
from .experiment import paired_ci, sample_genomes
from .investigation import stimulus_response
from .simulation import Config, World

ECOLOGIES: dict[str, dict[str, Any]] = {
    "dense": {},
    "islands": {"resource_layout": "islands", "resource_background": 0.01,
                "move_cost": 0.20},
    "islands_costly": {"resource_layout": "islands", "resource_background": 0.01,
                       "move_cost": 0.50},
}
GROUPS = ("founder", *ECOLOGIES)
INTERVENTIONS = ("normal", "zero_turn", "food_blind", "mirror_food", "speed_fixed",
                 "fixed_zero_turn", "fixed_food_blind", "fixed_mirror_food")


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if rows:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def intervention_config(cfg: Config, mode: str) -> Config:
    if mode == "normal":
        return cfg
    if mode == "zero_turn":
        return replace(cfg, fixed_turn=0.0)
    if mode == "food_blind":
        return replace(cfg, sensor_mode="food_blind")
    if mode == "mirror_food":
        return replace(cfg, sensor_mode="mirror_food")
    if mode == "speed_fixed":
        return replace(cfg, fixed_speed=0.60)
    if mode == "fixed_zero_turn":
        return replace(cfg, fixed_speed=0.60, fixed_turn=0.0)
    if mode == "fixed_food_blind":
        return replace(cfg, fixed_speed=0.60, sensor_mode="food_blind")
    if mode == "fixed_mirror_food":
        return replace(cfg, fixed_speed=0.60, sensor_mode="mirror_food")
    raise ValueError(f"unknown intervention: {mode}")


def common_garden(genomes: np.ndarray, *, seed: int, ticks: int,
                  ecology: str, intervention: str = "normal") -> dict[str, float]:
    """Matched, reproduction-free holdout. Dead agents contribute zero harvest."""
    if ecology not in ECOLOGIES or ticks < 1:
        raise ValueError("Invalid ecology or duration")
    if intervention not in INTERVENTIONS:
        raise ValueError("unknown intervention")
    if not len(genomes):
        return {"harvest": float("nan"), "survival": float("nan"),
                "mean_speed": float("nan"), "retained_energy": float("nan")}
    cfg = Config(founders=len(genomes), max_population=len(genomes),
                 initial_energy=60.0, lifespan=ticks + 20,
                 allow_reproduction=False, allow_mutation=False,
                 **ECOLOGIES[ecology])
    cfg = intervention_config(cfg, intervention)
    w = World(cfg, seed=seed, founder_genomes=genomes)
    speeds = 0.0
    for _ in range(ticks):
        w.step()
        speeds += w.last_mean_speed * w.population  # conditional speed, population-weighted
    return {"harvest": w.total_harvest / (len(genomes) * ticks),
            "survival": w.population / len(genomes),
            "mean_speed": speeds / (len(genomes) * ticks),
            "retained_energy": float(w.energy.sum()) / len(genomes)}


def target_assay(genomes: np.ndarray, *, seed: int, ticks: int = 55,
                 intervention: str = "normal") -> dict[str, float]:
    """Direct test of natural steering with 36 independent, unmoving targets.

    One randomly oriented organism begins at equal radial distance from each of
    36 planted Gaussian islands (6x6, 15-unit grid). Every intervention receives
    the same genomes, initial angles, positions and resource map. The targets
    are *experimental probes*, not routes known to the organisms or training data.
    """
    if intervention not in INTERVENTIONS or ticks < 1:
        raise ValueError("unknown intervention or duration")
    if len(genomes) == 0:
        return {key: float("nan") for key in ("harvest", "hit_fraction",
                "occupancy_fraction", "mean_final_distance", "mean_radial_progress")}
    rng = np.random.default_rng(seed + 24_113)
    n = 36
    # Resample the same genotype indices for all interventions and conditions.
    chosen = genomes[rng.choice(len(genomes), n, replace=len(genomes) < n)].copy()
    cfg = Config(width=96, height=96, founders=n, max_population=n,
                 initial_energy=100.0, lifespan=ticks + 80,
                 allow_reproduction=False, allow_mutation=False,
                 growth_rate=0.12, move_cost=0.32, sensor_distance=3.0,
                 resource_layout="islands", resource_background=0.01,
                 boundary_mode="reflect")
    cfg = intervention_config(cfg, intervention)
    w = World(cfg, seed=seed, founder_genomes=chosen)
    locations = np.linspace(10.0, 86.0, 6)
    centers = np.array([(x, y) for y in locations for x in locations], dtype=float)
    yy, xx = np.mgrid[:cfg.height, :cfg.width]
    capacity = np.full((cfg.height, cfg.width), 0.01, dtype=float)
    for x, y in centers:
        capacity += 10.0 * np.exp(-0.5 * ((xx - x)**2 + (yy - y)**2) / 2.35**2)
    w.capacity = np.minimum(capacity, 12.0)
    w.food = w.capacity.copy()
    radians = rng.uniform(-np.pi, np.pi, n)
    w.x = centers[:, 0] + 6.15 * np.cos(radians)
    w.y = centers[:, 1] + 6.15 * np.sin(radians)
    w.angle = rng.uniform(-np.pi, np.pi, n)
    ever_hit = np.zeros(n, dtype=bool)
    occupancy = 0
    for _ in range(ticks):
        w.step()
        if not w.population:
            break
        # Allow the nearest island to change, avoiding artificial assignments.
        dist = np.sqrt((w.x[:, None] - centers[None, :, 0])**2 +
                       (w.y[:, None] - centers[None, :, 1])**2)
        nearest = dist.min(axis=1)
        close = nearest <= 3.0
        ever_hit[:w.population] |= close
        occupancy += int(np.count_nonzero(close))
    if w.population:
        dist = np.sqrt((w.x[:, None] - centers[None, :, 0])**2 +
                       (w.y[:, None] - centers[None, :, 1])**2)
        final = float(dist.min(axis=1).mean())
    else:
        final = float("nan")
    return {"harvest": w.total_harvest / (n * ticks),
            "hit_fraction": float(ever_hit.mean()),
            "occupancy_fraction": occupancy / (n * ticks),
            "mean_final_distance": final,
            "mean_radial_progress": 6.15 - final if np.isfinite(final) else float("nan")}


def paired_contrast(rows: list[dict[str, Any]], *, measure: str, ecology: str | None,
                    left: str, right: str, left_intervention: str = "normal",
                    right_intervention: str = "normal") -> dict[str, Any]:
    selected = [r for r in rows if ecology is None or r.get("ecology") == ecology]
    paired = []
    for seed in sorted({r["seed"] for r in selected}):
        matched = [r for r in selected if r["seed"] == seed]
        l = next((r[measure] for r in matched if r["group"] == left and
                  r["intervention"] == left_intervention), float("nan"))
        r = next((r[measure] for r in matched if r["group"] == right and
                  r["intervention"] == right_intervention), float("nan"))
        if np.isfinite(l) and np.isfinite(r):
            paired.append(float(l - r))
    values = np.asarray(paired, dtype=float)
    return {"mean_difference": float(np.mean(values)) if len(values) else None,
            "bootstrap_95_percent_ci": list(paired_ci(values)) if len(values) else None,
            "positive_seeds": int(np.count_nonzero(values > 0)),
            "paired_seeds": len(values), "per_seed_differences": paired}


def run_navigation_experiment(*, seeds: list[int], steps: int, probe_ticks: int,
                              count: int, output: Path,
                              save_checkpoints: bool = True,
                              progress: bool = True) -> dict[str, Any]:
    if not seeds or len(seeds) != len(set(seeds)) or min(steps, probe_ticks, count) < 1:
        raise ValueError("Unique nonempty seeds and positive durations/count required")
    output.mkdir(parents=True, exist_ok=True)
    if save_checkpoints:
        (output / "checkpoints").mkdir(exist_ok=True)
    training: list[dict[str, Any]] = []
    holdout: list[dict[str, Any]] = []
    assays: list[dict[str, Any]] = []
    response: list[dict[str, Any]] = []
    parts_dir = output / "seed_parts"
    parts_dir.mkdir(exist_ok=True)
    for seed in seeds:
        part_path = parts_dir / f"seed_{seed}.json"
        cache_settings = {"seed": seed, "steps": steps, "probe_ticks": probe_ticks,
                          "count": count, "ecologies": ECOLOGIES}
        if part_path.exists():
            saved = json.loads(part_path.read_text(encoding="utf-8"))
            if saved.get("cache_settings") != cache_settings:
                raise ValueError(f"Incompatible cached replicate: {part_path}")
            training.extend(saved["training"])
            holdout.extend(saved["holdout"])
            assays.extend(saved["assays"])
            response.extend(saved["response"])
            if progress:
                print(f"seed {seed}: loaded completed cached replicate", flush=True)
            continue
        reference = World(Config(), seed=seed)
        origin = {name: getattr(reference, name).copy() for name in
                  ("x", "y", "angle", "genomes", "age", "energy")}
        gene_sets: dict[str, np.ndarray] = {
            "founder": sample_genomes(reference.genomes, count, seed + 15_203)
        }
        for ecology, settings in ECOLOGIES.items():
            checkpoint = output / "checkpoints" / f"seed_{seed}_{ecology}.npz"
            if checkpoint.exists():
                w = World.load(checkpoint)
                if w.tick != steps or w.seed != seed or w.config != Config(**settings):
                    raise ValueError(f"Checkpoint mismatch: {checkpoint}")
            else:
                w = World(Config(**settings), seed=seed)
            # Stronger matching than v0.3: identical founder coordinates and
            # brains even when terrain generation consumes different RNG draws.
            if w.tick == 0:
                for attr, values in origin.items():
                    setattr(w, attr, values.copy())
                for _ in range(steps):
                    w.step()
            stats = w.stats(detailed=False)
            training.append({"seed": seed, "ecology": ecology,
                             "population": w.population, "births": w.total_births,
                             "starvation_deaths": w.death_causes["starvation"],
                             "mean_generation": stats["mean_generation"],
                             "max_generation": stats["max_generation"],
                             "total_harvest": w.total_harvest})
            gene_sets[ecology] = sample_genomes(w.genomes, count, seed + 15_203)
            if save_checkpoints:
                w.save(output / "checkpoints" / f"seed_{seed}_{ecology}.npz")
        for group, genes in gene_sets.items():
            response.append({"seed": seed, "group": group, "n": len(genes),
                             **stimulus_response(genes)})
        for ecology in ECOLOGIES:
            for group, genes in gene_sets.items():
                measurement = common_garden(genes, seed=seed + 70_000,
                                            ticks=probe_ticks, ecology=ecology)
                holdout.append({"seed": seed, "ecology": ecology, "group": group,
                                "intervention": "normal", "n": len(genes), **measurement})
            for group in ("islands", "islands_costly"):
                for mode in ("zero_turn", "food_blind", "mirror_food", "speed_fixed"):
                    genes = gene_sets[group]
                    measurement = common_garden(genes, seed=seed + 70_000,
                                                ticks=probe_ticks, ecology=ecology,
                                                intervention=mode)
                    holdout.append({"seed": seed, "ecology": ecology, "group": group,
                                    "intervention": mode, "n": len(genes), **measurement})
        for group, genes in gene_sets.items():
            for mode in ("normal", "zero_turn", "food_blind", "mirror_food"):
                measurement = target_assay(genes, seed=seed + 85_000, intervention=mode)
                assays.append({"seed": seed, "group": group, "intervention": mode,
                               "n": 36, **measurement})
        part = {"cache_settings": cache_settings,
                "training": training[-len(ECOLOGIES):],
                "holdout": [r for r in holdout if r["seed"] == seed],
                "assays": [r for r in assays if r["seed"] == seed],
                "response": [r for r in response if r["seed"] == seed]}
        # Atomic completed-replicate cache, so an interrupted long run can
        # restart without biasing or duplicating completed seeds.
        tmp = part_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(part, allow_nan=False), encoding="utf-8")
        tmp.replace(part_path)
        if progress:
            print(f"seed {seed}: " + ", ".join(
                f"{r['ecology']}={r['population']}" for r in training[-len(ECOLOGIES):]), flush=True)

    _write_rows(output / "training.csv", training)
    _write_rows(output / "holdout.csv", holdout)
    _write_rows(output / "target_assay.csv", assays)
    _write_rows(output / "controller.csv", response)
    planned: dict[str, dict[str, Any]] = {}
    def h(label: str, env: str, left: str, right: str, mode: str = "normal",
          other_mode: str = "normal", measure: str = "harvest") -> None:
        planned[label] = paired_contrast(holdout, ecology=env, measure=measure,
                    left=left, right=right, left_intervention=mode,
                    right_intervention=other_mode)
    def t(label: str, left: str, right: str, mode: str = "normal",
          other_mode: str = "normal", measure: str = "hit_fraction") -> None:
        planned[label] = paired_contrast(assays, ecology=None, measure=measure,
                    left=left, right=right, left_intervention=mode,
                    right_intervention=other_mode)
    h("island_evolution_vs_founder", "islands", "islands", "founder")
    h("island_specialization", "islands", "islands", "dense")
    h("costly_island_specialization", "islands_costly", "islands_costly", "islands")
    h("island_zero_turn_minus_normal", "islands", "islands", "islands", "zero_turn")
    h("island_normal_minus_blind", "islands", "islands", "islands", "normal", "food_blind")
    h("island_normal_minus_mirror", "islands", "islands", "islands", "normal", "mirror_food")
    h("costly_zero_turn_minus_normal", "islands_costly", "islands_costly", "islands_costly", "zero_turn")
    t("target_evolved_vs_founder", "islands", "founder")
    t("target_normal_minus_zero_turn", "islands", "islands", "normal", "zero_turn")
    t("target_normal_minus_blind", "islands", "islands", "normal", "food_blind")
    t("target_normal_minus_mirror", "islands", "islands", "normal", "mirror_food")
    t("target_costly_normal_minus_zero_turn", "islands_costly", "islands_costly", "normal", "zero_turn")
    t("target_occupancy_normal_minus_zero_turn", "islands", "islands", "normal", "zero_turn",
      measure="occupancy_fraction")
    summary: dict[str, Any] = {
        "experiment": "004: sparse islands, movement costs, direct target navigation",
        "status": "exploratory controlled simulation; no conclusions baked into scoring",
        "settings": {"seeds": seeds, "steps": steps, "probe_ticks": probe_ticks,
                     "genome_sample": count, "ecologies": ECOLOGIES,
                     "target_assay_ticks": 55, "target_assay_genomes": 36,
                     "default_config": asdict(Config())},
        "training": {e: {"mean_population": float(np.mean([
            r["population"] for r in training if r["ecology"] == e])),
            "extinctions": sum(r["population"] == 0 for r in training if r["ecology"] == e),
            "replicates": len(seeds)} for e in ECOLOGIES},
        "holdout_means": {e: {g: _finite_mean([
            r["harvest"] for r in holdout if r["ecology"] == e and
            r["group"] == g and r["intervention"] == "normal"])
            for g in GROUPS} for e in ECOLOGIES},
        "assay_means": {g: {mode: {metric: _finite_mean([
            r[metric] for r in assays if r["group"] == g and r["intervention"] == mode])
            for metric in ("hit_fraction", "occupancy_fraction", "harvest", "mean_radial_progress")}
            for mode in ("normal", "zero_turn", "food_blind", "mirror_food")}
            for g in GROUPS},
        "controller_means": {g: {k: _finite_mean([
            r[k] for r in response if r["group"] == g])
            for k in ("baseline_speed", "directional_cue_response")}
            for g in GROUPS},
        "contrasts": planned,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    try:
        plot_navigation(output, holdout, assays)
    except ImportError:
        pass
    return summary


def plot_navigation(output: Path, holdout: list[dict[str, Any]],
                    assays: list[dict[str, Any]]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def means(rows: list[dict[str, Any]], metric: str, **criteria: str) -> float:
        data = [float(r[metric]) for r in rows if all(r.get(k) == v for k, v in criteria.items())]
        finite = [v for v in data if np.isfinite(v)]
        return float(np.mean(finite)) if finite else float("nan")

    names = list(ECOLOGIES)
    values = [[means(holdout, "harvest", ecology=env, group=group,
                     intervention="normal") for env in names] for group in GROUPS]
    fig, ax = plt.subplots(figsize=(9, 4.7), layout="constrained")
    img = ax.imshow(values, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(names)), ["Dense", "Sparse islands", "Costly islands"])
    ax.set_yticks(range(len(GROUPS)), ["Founder", "Dense-evolved", "Island-evolved", "Costly-island-evolved"])
    for i, row in enumerate(values):
        for j, value in enumerate(row):
            ax.text(j, i, f"{value:.3f}" if np.isfinite(value) else "extinct",
                    ha="center", va="center", color="white" if np.isfinite(value) and value < 0.4 else "black")
    fig.colorbar(img, ax=ax, label="Harvest / founder organism / tick")
    ax.set_title("Independent training ecologies → novel held-out environments")
    fig.savefig(output / "ecology_transfer.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 4.5), layout="constrained")
    assays_order = ("normal", "zero_turn", "food_blind", "mirror_food")
    xs = np.arange(len(assays_order))
    width = 0.20
    for i, group in enumerate(GROUPS):
        vals = [means(assays, "hit_fraction", group=group, intervention=mode)
                for mode in assays_order]
        ax.bar(xs + (i - 1.5) * width, vals, width, label=group)
    ax.set_xticks(xs, ("Normal", "No steering", "Food-blind", "Cues mirrored"))
    ax.set_ylabel("Fraction entering a food-target core")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=8)
    ax.set_title("Target-acquisition challenge: 36 independent islands per trial")
    fig.savefig(output / "target_acquisition.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    for group in ("islands", "islands_costly"):
        normal = {r["seed"]: r["harvest"] for r in holdout if r["ecology"] == group and
                  r["group"] == group and r["intervention"] == "normal"}
        for mode in ("zero_turn", "food_blind", "mirror_food"):
            treated = {r["seed"]: r["harvest"] for r in holdout if r["ecology"] == group and
                       r["group"] == group and r["intervention"] == mode}
            diffs = [normal[seed] - treated[seed] for seed in normal
                     if seed in treated and np.isfinite(normal[seed]) and np.isfinite(treated[seed])]
            xpos = len(ax.patches)
            ax.bar(xpos, np.mean(diffs) if diffs else np.nan)
    ax.set_xticks(range(6), ("Island vs no turn", "Island vs blind", "Island vs mirrored",
                             "Costly vs no turn", "Costly vs blind", "Costly vs mirrored"),
                  rotation=18, ha="right")
    ax.axhline(0, color="gray", linewidth=0.8)
    ax.set_ylabel("Unmodified performance − intervention")
    ax.set_title("Does retaining natural sensory control help harvesting?")
    fig.savefig(output / "steering_causality.png", dpi=160); plt.close(fig)


def run_motor_isolation(*, seeds: list[int], count: int, probe_ticks: int,
                        trained_results: Path, output: Path) -> dict[str, Any]:
    """Post-training steering-only test at exactly matched propulsion speed.

    Reads untouched evolved checkpoints from Experiment 004. This avoids a
    second evolution and prevents changing trained populations while debugging.
    Cue ablations affect both motor neurons, but fixing speed to 0.60 clamps
    the *actual* speed, isolating the realized heading/turning pathway.
    """
    if not seeds or count <= 0 or probe_ticks <= 0:
        raise ValueError("Invalid post-training parameters")
    output.mkdir(parents=True, exist_ok=True)
    modes = ("speed_fixed", "fixed_zero_turn", "fixed_food_blind", "fixed_mirror_food")
    rows: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for seed in seeds:
        founder = World(Config(), seed=seed)
        genes = {"founder": sample_genomes(founder.genomes, count, seed + 15_203)}
        for ecology in ECOLOGIES:
            path = trained_results / "checkpoints" / f"seed_{seed}_{ecology}.npz"
            if not path.exists():
                raise FileNotFoundError(f"Cannot isolate effects without training checkpoint {path}")
            world = World.load(path)
            if world.seed != seed or world.config != Config(**ECOLOGIES[ecology]):
                raise ValueError(f"Unexpected training configuration in {path}")
            genes[ecology] = sample_genomes(world.genomes, count, seed + 15_203)
        for group, genomes in genes.items():
            for mode in modes:
                measurement = target_assay(genomes, seed=seed + 85_000,
                                           ticks=55, intervention=mode)
                targets.append({"seed": seed, "group": group,
                                "intervention": mode, **measurement})
                for ecology in ("islands", "islands_costly"):
                    measure = common_garden(genomes, seed=seed + 70_000,
                                             ticks=probe_ticks, ecology=ecology,
                                             intervention=mode)
                    rows.append({"seed": seed, "ecology": ecology,
                                 "group": group, "intervention": mode, **measure})
    _write_rows(output / "motor_isolation.csv", rows)
    _write_rows(output / "motor_isolation_targets.csv", targets)
    planned: dict[str, Any] = {}
    for group in ("islands", "islands_costly"):
        env = "islands" if group == "islands" else "islands_costly"
        for changed in ("fixed_zero_turn", "fixed_food_blind", "fixed_mirror_food"):
            planned[f"{group}_{changed}_garden"] = paired_contrast(
                rows, measure="harvest", ecology=env, left=group, right=group,
                left_intervention="speed_fixed", right_intervention=changed)
            for metric in ("hit_fraction", "occupancy_fraction", "harvest"):
                planned[f"{group}_{changed}_target_{metric}"] = paired_contrast(
                    targets, measure=metric, ecology=None, left=group, right=group,
                    left_intervention="speed_fixed", right_intervention=changed)
    summary: dict[str, Any] = {
        "method": "Matched motor interventions with actual speed held constant at 0.60",
        "source_training_results": str(trained_results),
        "settings": {"seeds": seeds, "count": count, "probe_ticks": probe_ticks,
                     "evaluation_ecologies": ["islands", "islands_costly"],
                     "modes": modes, "target_assay_ticks": 55},
        "means": {env: {group: {mode: _finite_mean([
            r["harvest"] for r in rows if r["ecology"] == env and
            r["group"] == group and r["intervention"] == mode])
            for mode in modes} for group in ("islands", "islands_costly")}
            for env in ("islands", "islands_costly")},
        "target_means": {group: {mode: {metric: _finite_mean([
            r[metric] for r in targets if r["group"] == group and r["intervention"] == mode])
            for metric in ("hit_fraction", "occupancy_fraction", "harvest")}
            for mode in modes} for group in ("islands", "islands_costly")},
        "contrasts": planned}
    (output / "motor_isolation_summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False), encoding="utf-8")
    return summary
