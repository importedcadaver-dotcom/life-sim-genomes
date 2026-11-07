"""Reproducible digital-genetics studies. Local CPU processes, no cloud access.

Reports realized births, deaths, allele/copy-number distributions, and ancestry;
these are observational results, not a hand-written fitness ranking.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from dataclasses import asdict, replace
import csv
import json
from pathlib import Path
import statistics
from typing import Any

import numpy as np

from .genetics import LOCI
from .simulation import Config, World


def _rows_for_seed(task: tuple[int, int, int, dict[str, Any], bool]):
    seed, ticks, interval, config_dict, mutation_on = task
    config = Config(**config_dict)
    if not mutation_on:
        config = replace(config, allow_mutation=False)
    world = World(config, seed)
    rows = []
    for _ in range(ticks + 1):
        if world.tick % interval == 0 or world.tick == ticks or world.population == 0:
            base = {
                "seed": seed, "mutation_on": int(mutation_on), "tick": world.tick,
                "population": world.population, "births": world.total_births,
                "deaths": world.total_deaths, "max_generation": int(np.max(world.generation)) if world.population else 0,
                "sexual_births": world.sexual_births,
                "point_mutations": world.total_body_mutations,
                "copy_mutations": world.total_copy_mutations,
            }
            for k, locus in enumerate(LOCI):
                base[f"allele_{locus}"] = (float(np.mean(world.body_dna[:, k])) if world.population else float("nan"))
                base[f"copies_{locus}"] = (float(np.mean(world.gene_copies[:, k])) if world.population else float("nan"))
            rows.append(base)
        if world.tick == ticks or world.population == 0:
            break
        world.step()
    return rows


def run_study(*, seeds: list[int], ticks: int, output: Path,
              founders: int = 75, capacity: int = 250, workers: int = 1,
              compare_mutations: bool = True, reproduction: str = "mixed",
              growth: float = .008, sample_every: int = 50) -> dict[str, Any]:
    if not seeds or any(not isinstance(s, int) for s in seeds) or len(set(seeds)) != len(seeds):
        raise ValueError("Seeds must be a nonempty list of distinct integers")
    if ticks < 1 or workers < 1 or sample_every < 1:
        raise ValueError("ticks, workers, sample_every must be positive")
    cfg = Config(width=48, height=36, founders=founders, max_population=capacity,
                 growth_rate=growth, reproduction_mode=reproduction, genetics_enabled=True)
    config = asdict(cfg)
    jobs = [(seed, ticks, sample_every, config, mutation_on)
            for seed in seeds for mutation_on in ((True, False) if compare_mutations else (True,))]
    if workers == 1:
        results = [_rows_for_seed(task) for task in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(_rows_for_seed, jobs))
    output.mkdir(parents=True, exist_ok=True)
    rows = [row for group in results for row in group]
    with (output / "genomic_timelines.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    finals = [group[-1] for group in results]
    with (output / "final_populations.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(finals[0]))
        writer.writeheader()
        writer.writerows(finals)
    def summary(mutation_on):
        selected = [r for r in finals if bool(r["mutation_on"]) == mutation_on]
        return {
            "mean_births": statistics.mean(r["births"] for r in selected),
            "mean_survivors": statistics.mean(r["population"] for r in selected),
            "mean_max_generation": statistics.mean(r["max_generation"] for r in selected),
            "extinctions": sum(r["population"] == 0 for r in selected),
            "total_point_mutations": sum(r["point_mutations"] for r in selected),
            "total_copy_mutations": sum(r["copy_mutations"] for r in selected),
            "total_sexual_births": sum(r["sexual_births"] for r in selected),
        }
    report = {
        "method": "asynchronous life-history selection (not top-50% truncation)",
        "independent_seeds": len(seeds), "seeds": seeds, "ticks": ticks,
        "comparison": "mutation enabled vs disabled from matched random seeds" if compare_mutations else "mutation enabled only",
        "config": config,
        "mutation_enabled": summary(True),
        "mutation_disabled": summary(False) if compare_mutations else None,
        "caveat": "Exploratory simulation outcomes; allele shifts do not alone prove adaptation. "
                  "The fixed locus vocabulary and up to three copies/locus are not open-ended genome evolution.",
    }
    (output / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
