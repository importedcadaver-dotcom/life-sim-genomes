"""Experiment 005: does evolved steering *find* food, or *stay* to exploit it?

Two distinct, tightly controlled assays with matched starting positions:
  SEARCH: 36 organisms begin outside a separated food core.
  RESIDENCE: 36 organisms begin inside a separated food core.
Experiments use checkpoint genomes but cannot alter archived training worlds.
No target-finding or retention policy is added to the organisms themselves.
"""
from __future__ import annotations

import csv
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from .experiment import paired_ci
from .navigation import intervention_config
from .simulation import Config, World

MODES = ("speed_fixed", "fixed_zero_turn", "fixed_food_blind", "fixed_mirror_food")
GROUPS = ("founder", "dense", "islands", "islands_costly")
STARTS = ("search", "residence")


def probe_residency(genomes: np.ndarray, *, seed: int, start: str,
                    mode: str = "speed_fixed", ticks: int = 75) -> dict[str, float]:
    """A matched assay with per-agent arrival/exit, occupancy, and ingestion.

    Each agent is assigned a grid island only for measurements, NOT for control.
    Closest available resource core at every tick counts, which avoids forced
    loyalty to the original island. Agents have fixed motor speed 0.6 under all
    modes, no reproduction and enough energy to avoid death in this assay.
    """
    if start not in STARTS or mode not in MODES or ticks < 1:
        raise ValueError("Unknown residency assay condition")
    if len(genomes) < 1:
        raise ValueError("At least one genome required")
    rng = np.random.default_rng(seed + 72_911)
    n = 36
    chosen = np.asarray(genomes)[rng.choice(len(genomes), n, replace=len(genomes) < n)].copy()
    cfg = Config(width=96, height=96, founders=n, max_population=n,
                 initial_energy=140.0, lifespan=ticks + 80,
                 allow_reproduction=False, allow_mutation=False,
                 growth_rate=0.10, move_cost=0.32, sensor_distance=3.0,
                 resource_layout="islands", resource_background=0.01,
                 boundary_mode="reflect")
    cfg = intervention_config(cfg, mode)
    w = World(cfg, seed=seed, founder_genomes=chosen)
    locations = np.linspace(10.0, 86.0, 6)
    centers = np.array([(x, y) for y in locations for x in locations], dtype=np.float64)
    yy, xx = np.mgrid[:cfg.height, :cfg.width]
    capacity = np.full((cfg.height, cfg.width), 0.01, dtype=np.float64)
    for cx, cy in centers:
        capacity += 10.0 * np.exp(-0.5 * ((xx - cx) ** 2 + (yy - cy) ** 2) / 2.35 ** 2)
    w.capacity = np.minimum(capacity, 12.0)
    w.food = w.capacity.copy()
    radius = 6.15 if start == "search" else 1.1
    offsets = rng.uniform(-np.pi, np.pi, n)
    w.x = centers[:, 0] + radius * np.cos(offsets)
    w.y = centers[:, 1] + radius * np.sin(offsets)
    w.angle = rng.uniform(-np.pi, np.pi, n)
    # All genomes and sensory ablations share the same initial environment,
    # starting locations and headings for each seed and start condition.
    inside_count = np.zeros(n, dtype=np.int32)
    streak = np.zeros(n, dtype=np.int32)
    longest = np.zeros(n, dtype=np.int32)
    ever_hit = np.full(n, start == "residence", dtype=bool)
    first_hit = np.zeros(n, dtype=np.int32) if start == "residence" else np.full(n, ticks + 1)
    first_exit = np.full(n, ticks + 1, dtype=np.int32)
    post_hit_exposure = np.zeros(n, dtype=np.int32)
    post_hit_inside = np.zeros(n, dtype=np.int32)
    post_hit_food = np.zeros(n, dtype=np.float64)
    pre_hit_food = np.zeros(n, dtype=np.float64)
    ever_exited = np.zeros(n, dtype=bool)
    ever_reentered = np.zeros(n, dtype=bool)
    stay10 = np.ones(n, dtype=bool)
    for t in range(1, ticks + 1):
        w.step()
        if w.population != n:
            raise RuntimeError("Assay requires survival and stable agent identities")
        dist = np.sqrt((w.x[:, None] - centers[None, :, 0]) ** 2 +
                       (w.y[:, None] - centers[None, :, 1]) ** 2)
        inside = dist.min(axis=1) <= 3.0
        first_entrants = inside & ~ever_hit
        first_hit[first_entrants] = t
        ever_hit |= inside
        post_hit_exposure += ever_hit
        post_hit_inside += inside & ever_hit
        post_hit_food += np.where(ever_hit, w.last_intake, 0.0)
        pre_hit_food += np.where(~ever_hit, w.last_intake, 0.0)
        inside_count += inside
        streak = np.where(inside, streak + 1, 0)
        longest = np.maximum(longest, streak)
        if start == "residence":
            first_leavers = ~inside & ~ever_exited
            first_exit[first_leavers] = t
            ever_reentered |= inside & ever_exited
            ever_exited |= ~inside
            if t <= 10:
                stay10 &= inside
    return {
        "hit_fraction": float(ever_hit.mean()),
        "first_hit_penalized": float(first_hit.mean()),
        "mean_first_hit_among_arrivals": (float(first_hit[ever_hit].mean())
                                          if ever_hit.any() else float("nan")),
        "occupancy_fraction": float(inside_count.sum() / (n * ticks)),
        "post_contact_dwell": float(post_hit_inside.sum() / max(1, post_hit_exposure.sum())),
        "mean_longest_core_streak": float(longest.mean()),
        "harvest_per_agent_tick": float(w.total_harvest / (n * ticks)),
        "harvest_post_contact_per_agent_tick": float(post_hit_food.sum() / (n * ticks)),
        "harvest_pre_contact_per_agent_tick": float(pre_hit_food.sum() / (n * ticks)),
        "exit_fraction": float(ever_exited.mean()) if start == "residence" else float("nan"),
        "reentry_fraction": float(ever_reentered.mean()) if start == "residence" else float("nan"),
        "unbroken_10tick_stay_fraction": float(stay10.mean()) if start == "residence" else float("nan"),
    }


def paired_differences(rows: list[dict], *, group: str, start: str,
                       metric: str, left: str = "speed_fixed",
                       right: str = "fixed_zero_turn") -> dict:
    paired = []
    for seed in sorted({r["seed"] for r in rows}):
        items = [r for r in rows if r["seed"] == seed and r["group"] == group and
                 r["start"] == start]
        a = next((r[metric] for r in items if r["mode"] == left), float("nan"))
        b = next((r[metric] for r in items if r["mode"] == right), float("nan"))
        if np.isfinite(a) and np.isfinite(b):
            paired.append(float(a - b))
    arr = np.array(paired)
    return {"mean_difference": float(arr.mean()) if len(arr) else None,
            "paired_seeds": len(arr), "positive_seeds": int((arr > 0).sum()),
            "paired_bootstrap_95_ci": list(paired_ci(arr)) if len(arr) else None,
            "seed_differences": paired}


def run_residency(*, seeds: list[int], trained_results: Path, output: Path,
                  ticks: int = 75, progress: bool = False) -> dict:
    if not seeds or len(set(seeds)) != len(seeds) or ticks < 1:
        raise ValueError("Unique seeds and positive ticks required")
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for seed in seeds:
        original = World(Config(), seed=seed)
        groups = {"founder": original.genomes}
        for group in GROUPS[1:]:
            path = trained_results / "checkpoints" / f"seed_{seed}_{group}.npz"
            if not path.exists():
                raise FileNotFoundError(f"Missing saved Experiment 004 world: {path}")
            groups[group] = World.load(path).genomes
        for group, genomes in groups.items():
            for start in STARTS:
                for mode in MODES:
                    row = {"seed": seed, "group": group, "start": start, "mode": mode,
                           **probe_residency(genomes, seed=seed * 11 + 4_901,
                                             start=start, mode=mode, ticks=ticks)}
                    rows.append(row)
        if progress:
            print(f"Experiment 005 complete: seed {seed} ({len(rows)} trials)", flush=True)
    with (output / "trials.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    means = {}
    for group in GROUPS:
        for start in STARTS:
            for mode in MODES:
                subset = [r for r in rows if r["group"] == group and
                          r["start"] == start and r["mode"] == mode]
                means[f"{group}/{start}/{mode}"] = {
                    k: float(np.mean([r[k] for r in subset])) for k in (
                        "hit_fraction", "occupancy_fraction", "mean_longest_core_streak",
                        "harvest_per_agent_tick", "harvest_post_contact_per_agent_tick",
                        "unbroken_10tick_stay_fraction") if np.isfinite(subset[0][k])}
    contrasts = {}
    for group in GROUPS:
        for start in STARTS:
            for metric in ("hit_fraction", "occupancy_fraction", "harvest_per_agent_tick",
                           "mean_longest_core_streak", "unbroken_10tick_stay_fraction"):
                if start == "search" and metric == "unbroken_10tick_stay_fraction":
                    continue
                contrasts[f"{group}/{start}/{metric}"] = paired_differences(
                    rows, group=group, start=start, metric=metric)
    summary = {"protocol": "Experiment 005: independent search and residency assays",
               "seeds": seeds, "ticks": ticks, "targets_per_trial": 36,
               "motor_speed_clamped": 0.6,
               "training_source": str(trained_results), "trial_count": len(rows),
               "means": means, "contrasts": contrasts,
               "caveats": ["Exploratory reused checkpoint genomes, not new training.",
                           "An organism may enter a different nearby food island.",
                           "Search hit is defined as distance <=3.0 from any core.",
                           "No deaths/reproduction permitted in assay; no population-level coevolution.",
                           "Positive retention does not establish goal-directed planning."]}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
