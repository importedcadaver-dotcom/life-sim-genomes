"""Pre-specified internal validity test: beneficial vs neutral inherited marker.

No mutation, neural variation, artificial top-percentile filtering, or mating.
Selection happens naturally through the existing feeding/reproduction rules.
Shows that trait differences can cause differential lineage success in this model;
this is an engineered test, not proof of open-ended evolutionary innovation.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import statistics

import numpy as np

from .genetics import INDEX
from .simulation import Config, World


def run_assay(*, seeds: list[int], ticks: int, output: Path,
              sample_every: int = 25) -> dict:
    if not seeds or ticks < 1 or sample_every < 1:
        raise ValueError("seeds, ticks and sampling interval must be valid")
    output.mkdir(parents=True, exist_ok=True)
    cfg = Config(width=44, height=32, founders=110, max_population=270,
                 genetics_enabled=True, reproduction_mode="asexual", allow_mutation=False,
                 growth_rate=.006, resource_background=.08, metabolism=.50,
                 move_cost=.30)
    data = []
    final = []
    for seed in seeds:
        for condition in ("metabolic", "neutral"):
            w = World(cfg, seed)
            # Controlled genetic background; only one specified locus varies.
            w.genomes[:] = 0
            w.body_dna[:] = 0
            w.gene_copies[:] = 1
            cohort = np.arange(w.population)
            np.random.default_rng(seed + 100).shuffle(cohort)
            locus = INDEX["metabolic_efficiency"] if condition == "metabolic" else INDEX["pigment"]
            w.body_dna[cohort[:55], locus] = 1.7
            w.body_dna[cohort[55:], locus] = -1.7
            for t in range(ticks + 1):
                if t % sample_every == 0 or t == ticks or w.population == 0:
                    alleles = w.body_dna[:, locus]
                    plus = int(np.count_nonzero(alleles > 0))
                    minus = int(np.count_nonzero(alleles < 0))
                    data.append({"seed": seed, "condition": condition, "tick": w.tick,
                                 "positive": plus, "negative": minus,
                                 "fraction_positive": plus / w.population if w.population else "",
                                 "population": w.population, "births": w.total_births,
                                 "deaths": w.total_deaths})
                if t == ticks or not w.population:
                    break
                w.step()
            final.append(data[-1].copy())
    with (output / "selection_timecourses.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader();writer.writerows(data)
    with (output / "selection_final.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(final[0]))
        writer.writeheader();writer.writerows(final)
    report = {"seeds": seeds, "ticks": ticks, "config": cfg.__dict__, "conditions": {}}
    for condition in ("metabolic", "neutral"):
        selected = [r for r in final if r["condition"] == condition]
        alive = [r for r in selected if r["population"] > 0]
        report["conditions"][condition] = {
            "survivor_runs": len(alive), "extinctions": len(selected) - len(alive),
            "mean_final_population": statistics.mean(r["population"] for r in selected),
            "mean_positive_fraction_surviving":
                statistics.mean(r["fraction_positive"] for r in alive) if alive else None,
            "positive_fixed_runs": sum(r["negative"] == 0 and r["positive"] > 0 for r in selected),
            "negative_fixed_runs": sum(r["positive"] == 0 and r["negative"] > 0 for r in selected),
        }
    report["interpretation"] = ("The effect of a deliberately specified metabolic-efficiency "
                                "allele on differential reproduction is a model validation, not an "
                                "unforeseen trait or a claim about real organisms.")
    (output / "selection_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
