"""Experiment 006: do evolved controllers condition their turning on food cues?

This is deliberately a *motor-only* trajectory experiment. It reuses the actual
World.controls() neural controller and reflect-wall movement equations, but does
not perform feeding, metabolism, survival, reproduction, or food regeneration.
All controllers move at the same fixed speed, keep their initial energy signal,
and see identical starting positions/headings within each paired comparison.

That design separates a sensory response from the secondary effects of eating.
It is NOT a full fitness or ecological performance test. No foraging policy is
inserted into any organism; all targeting is strictly external measurement.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from .experiment import paired_ci
from .simulation import Config, World

GROUPS = ("founder", "dense", "islands", "islands_costly")
STARTS = ("residence", "search")
CONDITIONS = ("rich", "barren", "ghost", "decoy", "food_blind", "straight")
CORE_RADIUS = 3.0
SPEED = 0.60
ARENA = 96
CENTER_AXIS = np.linspace(10., 86., 6)
CENTERS = np.array([(x, y) for y in CENTER_AXIS for x in CENTER_AXIS], dtype=np.float64)


@dataclass
class TrajectoryResult:
    summary: dict[str, float]
    initial_turn: np.ndarray
    trace: list[dict]  # optional sample of full motor trajectories


@lru_cache(maxsize=1)
def cue_landscapes() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Same target positions in every trial; independent sensory field allowed."""
    yy, xx = np.mgrid[:ARENA, :ARENA]
    rich = np.full((ARENA, ARENA), .01, dtype=np.float64)
    for cx, cy in CENTERS:
        rich += 10. * np.exp(-.5 * ((xx - cx) ** 2 + (yy - cy) ** 2) / 2.35 ** 2)
    rich = np.minimum(rich, 12.)
    barren = np.zeros_like(rich)
    # Spatially misleading information: rich cues come from a shifted map,
    # while the target cores used for scoring stay in their original places.
    decoy = np.roll(rich, shift=(6, 7), axis=(0, 1))
    for field in (rich, barren, decoy):
        field.flags.writeable = False
    return rich, barren, decoy


def sample_controllers(genomes: np.ndarray, *, seed: int, n: int = 36) -> np.ndarray:
    """Identical genome draws for every counterfactual in one training group."""
    if n < 1 or len(genomes) < 1 or np.asarray(genomes).shape[1:] != (2, 8):
        raise ValueError("Expected a nonempty batch of (2, 8) genomes")
    rng = np.random.default_rng(seed + 72_911)
    index = rng.choice(len(genomes), n, replace=len(genomes) < n)
    return np.asarray(genomes, dtype=np.float64)[index].copy()


def trajectory_probe(genomes: np.ndarray, *, seed: int, start: str,
                     condition: str, ticks: int = 90, record: int = 0) -> TrajectoryResult:
    """Evaluate motor trajectories around *the same* centers under cue changes.

    ``rich``: rich cores are sensed and are real hypothetical resources.
    ``barren``: same coordinates, but no food and no food cues.
    ``ghost``: food cues are identical to rich, but actual resources absent.
    ``decoy``: food cues displaced, resources still at original cores.
    ``food_blind``: real cores present, but inputs for food are set to zero.
    ``straight``: real cores present, but turning overridden to zero.

    Resources are scored as *potential exposure* only and are NEVER consumed.
    Evolved organisms therefore cannot feed or gain energy in this assay.
    """
    if start not in STARTS or condition not in CONDITIONS or ticks < 1 or record < 0:
        raise ValueError("Invalid trajectory condition")
    genes = np.asarray(genomes)
    n = len(genes)
    if not n or genes.shape != (n, 2, 8):
        raise ValueError("Expected a nonempty batch of (2, 8) genomes")
    rng = np.random.default_rng(seed + 73_909)
    cfg = Config(width=ARENA, height=ARENA, founders=n, max_population=n,
                 initial_energy=100., allow_reproduction=False, allow_mutation=False,
                 boundary_mode="reflect", resource_layout="islands", island_count=1,
                 fixed_speed=SPEED,
                 sensor_mode="food_blind" if condition == "food_blind" else "normal",
                 fixed_turn=0. if condition == "straight" else None)
    w = World(cfg, seed=seed, founder_genomes=genes)
    rich, barren, decoy = cue_landscapes()
    w.capacity = rich.copy()
    w.food = (barren if condition == "barren" else
              decoy if condition == "decoy" else rich).copy()
    reward_field = barren if condition in ("barren", "ghost") else rich
    radius = 1.1 if start == "residence" else 6.15
    offsets = rng.uniform(-np.pi, np.pi, n)
    # N probes may exceed 36; the same centers repeat, but most samples
    # have one agent per food core to minimize crowding as a confound.
    anchors = CENTERS[np.arange(n) % len(CENTERS)]
    w.x = anchors[:, 0] + radius * np.cos(offsets)
    w.y = anchors[:, 1] + radius * np.sin(offsets)
    w.angle = rng.uniform(-np.pi, np.pi, n)
    x0, y0 = w.x.copy(), w.y.copy()
    traces: list[dict] = []
    inside_ticks = np.zeros(n, dtype=np.int32)
    hit = np.full(n, start == "residence", dtype=bool)
    exited = np.zeros(n, dtype=bool)
    streak = np.zeros(n, dtype=np.int32)
    longest = np.zeros(n, dtype=np.int32)
    total_abs_turn = 0.
    total_signed_turn = 0.
    potential = 0.
    first_turn = np.zeros(n)
    initial_signal = np.nan
    first_step_approach = np.nan
    first_step_alignment_gain = np.nan
    early_target_progress = np.nan
    # NOTE: no w.step() -- it would couple sensory treatment to food
    # consumption and metabolism; only the original learned controller and
    # world motion equations are used here.
    for t in range(ticks):
        turn, speed, sensors = w.controls()
        if t == 0:
            first_turn = turn.copy()
            initial_signal = float(np.mean(sensors[:, 1:4]))
        total_abs_turn += float(np.sum(np.abs(turn)))
        total_signed_turn += float(np.sum(turn))
        if t == 0:
            bearing = np.arctan2(anchors[:, 1] - w.y, anchors[:, 0] - w.x)
            before = np.cos(bearing - w.angle)
            after = np.cos(bearing - (w.angle + turn))
            first_step_alignment_gain = float(np.mean(after - before))
        w.angle = (w.angle + turn + np.pi) % (2 * np.pi) - np.pi
        nx = w.x + speed * np.cos(w.angle)
        ny = w.y + speed * np.sin(w.angle)
        hit_x = (nx < 0) | (nx >= ARENA)
        hit_y = (ny < 0) | (ny >= ARENA)
        w.x = w._reflect_coordinate(nx, ARENA)
        w.y = w._reflect_coordinate(ny, ARENA)
        w.angle = np.where(hit_x, np.pi - w.angle, w.angle)
        w.angle = np.where(hit_y, -w.angle, w.angle)
        w.angle = (w.angle + np.pi) % (2 * np.pi) - np.pi
        if t == 0:
            first_step_approach = float(np.mean(radius - np.hypot(
                w.x - anchors[:, 0], w.y - anchors[:, 1])))
        if t == min(7, ticks - 1):
            early_target_progress = float(np.mean(radius - np.hypot(
                w.x - anchors[:, 0], w.y - anchors[:, 1])))
        # The target cores are intentionally unchanged when sensory cues are
        # shifted or erased. Here they serve ONLY as a measuring instrument.
        d2 = ((w.x[:, None] - CENTERS[None, :, 0]) ** 2 +
              (w.y[:, None] - CENTERS[None, :, 1]) ** 2)
        inside = np.min(d2, axis=1) <= CORE_RADIUS ** 2
        hit |= inside
        if start == "residence":
            exited |= ~inside
        inside_ticks += inside
        streak = np.where(inside, streak + 1, 0)
        longest = np.maximum(longest, streak)
        iy, ix = w._cells(w.x, w.y)
        potential += float(np.minimum(1.45, reward_field[iy, ix]).sum())
        if record:
            for j in range(min(record, n)):
                traces.append({"step": t + 1, "agent": j, "x": float(w.x[j]),
                               "y": float(w.y[j]), "angle": float(w.angle[j]),
                               "turn": float(turn[j]), "inside_core": int(inside[j]),
                               "initial_start": start, "condition": condition})
    direct_distance = np.hypot(w.x - x0, w.y - y0)
    return TrajectoryResult(
        summary={
            "core_occupancy": float(np.mean(inside_ticks) / ticks),
            "core_arrival": float(np.mean(hit)),
            "core_exit": float(np.mean(exited)) if start == "residence" else float("nan"),
            "longest_streak": float(np.mean(longest)),
            "mean_abs_turn": total_abs_turn / (n * ticks),
            "mean_signed_turn": total_signed_turn / (n * ticks),
            "path_efficiency": float(np.mean(direct_distance / (ticks * SPEED))),
            "potential_resource_exposure": potential / (n * ticks),
            "initial_food_signal": initial_signal,
            "first_step_target_approach": first_step_approach,
            "first_step_heading_gain": first_step_alignment_gain,
            "first_8_step_target_progress": early_target_progress,
        },
        initial_turn=first_turn,
        trace=traces,
    )


def _seed_pairs(rows: list[dict], *, group: str, start: str, metric: str,
                left: str = "rich", right: str = "barren") -> dict:
    differences = []
    for seed in sorted({r["seed"] for r in rows}):
        records = [r for r in rows if r["seed"] == seed and
                   r["group"] == group and r["start"] == start]
        a = next((r[metric] for r in records if r["condition"] == left), float("nan"))
        b = next((r[metric] for r in records if r["condition"] == right), float("nan"))
        if np.isfinite(a) and np.isfinite(b):
            differences.append(float(a - b))
    arr = np.asarray(differences)
    return {"mean": float(np.mean(arr)) if len(arr) else None,
            "n_training_seeds": int(len(arr)),
            "positive_seeds": int(np.sum(arr > 0)),
            "seed_differences": differences,
            "descriptive_bootstrap_95_ci": list(paired_ci(arr)) if len(arr) else None}


def run_trajectory_experiment(*, seeds: list[int], trained_results: Path,
                              output: Path, ticks: int = 90, progress: bool = False) -> dict:
    """Evaluate archived genomes without retraining, never edit input checkpoints."""
    if not seeds or len(set(seeds)) != len(seeds) or ticks < 1:
        raise ValueError("Unique seeds and positive ticks are required")
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    example_rows: list[dict] = []
    for seed in seeds:
        groups = {"founder": World(Config(), seed=seed).genomes}
        for group in GROUPS[1:]:
            path = trained_results / "checkpoints" / f"seed_{seed}_{group}.npz"
            if not path.is_file():
                raise FileNotFoundError(f"Missing Experiment 004 training checkpoint: {path}")
            groups[group] = World.load(path).genomes
        for group, genome_pool in groups.items():
            chosen = sample_controllers(genome_pool, seed=seed * 11 + 6901)
            for start in STARTS:
                counterfactuals: dict[str, TrajectoryResult] = {}
                for condition in CONDITIONS:
                    result = trajectory_probe(
                        chosen, seed=seed * 17 + 8123, start=start,
                        condition=condition, ticks=ticks,
                        record=7 if (seed == seeds[0] and group == "islands_costly") else 0,
                    )
                    counterfactuals[condition] = result
                    rows.append({"seed": seed, "group": group, "start": start,
                                 "condition": condition, **result.summary})
                    for point in result.trace:
                        example_rows.append({"seed": seed, "group": group, **point})
                # True matched-position and -genotype immediate sensory response.
                delta = np.abs(counterfactuals["rich"].initial_turn -
                               counterfactuals["barren"].initial_turn)
                for row in rows[-len(CONDITIONS):]:
                    row["immediate_cue_turn_delta"] = float(np.mean(delta))
                # Sanity-check orthogonal manipulations:
                # ghost rewards must not affect motor paths at fixed energy;
                # food blindness must match the barren sensory condition.
                ghost = counterfactuals["ghost"]
                rich = counterfactuals["rich"]
                blind = counterfactuals["food_blind"]
                barren = counterfactuals["barren"]
                assert np.array_equal(rich.initial_turn, ghost.initial_turn)
                assert np.array_equal(blind.initial_turn, barren.initial_turn)
                for key in ("core_occupancy", "core_arrival", "path_efficiency",
                            "mean_abs_turn", "mean_signed_turn",
                            "first_step_target_approach", "first_step_heading_gain",
                            "first_8_step_target_progress"):
                    assert rich.summary[key] == ghost.summary[key]
                    assert blind.summary[key] == barren.summary[key]
        if progress:
            print(f"Experiment 006 seed {seed} complete: {len(rows)} trials", flush=True)
    path = output / "trials.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with (output / "sample_trajectories.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(example_rows[0]))
        writer.writeheader(); writer.writerows(example_rows)
    means = {}
    for group in GROUPS:
        for start in STARTS:
            for condition in CONDITIONS:
                subset = [r for r in rows if r["group"] == group and
                          r["start"] == start and r["condition"] == condition]
                means[f"{group}/{start}/{condition}"] = {
                    key: float(np.nanmean([r[key] for r in subset]))
                    for key in ("core_occupancy", "core_arrival", "longest_streak",
                                "mean_abs_turn", "path_efficiency",
                                "potential_resource_exposure", "immediate_cue_turn_delta",
                                "first_step_target_approach", "first_step_heading_gain",
                                "first_8_step_target_progress")}
    paired = {}
    for group in GROUPS:
        for start in STARTS:
            for metric in ("core_occupancy", "core_arrival", "mean_abs_turn",
                           "path_efficiency", "potential_resource_exposure",
                           "first_step_target_approach", "first_step_heading_gain",
                           "first_8_step_target_progress"):
                paired[f"{group}/{start}/{metric}/rich_minus_barren"] = _seed_pairs(
                    rows, group=group, start=start, metric=metric)
                paired[f"{group}/{start}/{metric}/rich_minus_decoy"] = _seed_pairs(
                    rows, group=group, start=start, metric=metric, right="decoy")
    difference_in_differences = {}
    for group in GROUPS[1:]:
        for start in STARTS:
            for metric in ("core_arrival", "core_occupancy", "first_8_step_target_progress"):
                contrasts = []
                for seed in seeds:
                    def value(g: str, condition: str) -> float:
                        match = next(r for r in rows if r["seed"] == seed and
                                     r["group"] == g and r["start"] == start and
                                     r["condition"] == condition)
                        return float(match[metric])
                    contrasts.append((value(group, "rich") - value(group, "barren")) -
                                     (value("founder", "rich") - value("founder", "barren")))
                arr = np.asarray(contrasts)
                difference_in_differences[f"{group}/{start}/{metric}"] = {
                    "mean": float(arr.mean()), "seed_values": contrasts,
                    "positive_seeds": int(np.sum(arr > 0)),
                    "descriptive_bootstrap_95_ci": list(paired_ci(arr)),
                }
    summary = {
        "title": "Experiment 006: conditional food-cue steering versus generic looping",
        "training_seeds": seeds, "ticks": ticks, "trial_count": len(rows),
        "organisms_per_trial": 36, "speed_clamped": SPEED,
        "assay": "motor-only without metabolism, feeding, survival or reproduction",
        "means": means, "paired_seed_comparisons": paired,
        "evolved_minus_founder_cue_benefit": difference_in_differences,
        "qualifications": [
            "Reanalysis of previously evolved checkpoints, not independent preregistered selection.",
            "Training seed, not organism/trajectory, is the independent replicate.",
            "Cue and caloric fields are decoupled; potential exposure is NOT harvested food.",
            "Cue sensitivity alone does not imply beneficial targeting or intelligence.",
            "Constant energy and speed remove feedback from eating and movement energy costs.",
        ],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
