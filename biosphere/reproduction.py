"""Biological reproduction mechanics, isolated from World time-stepping.

This module owns local partner matching, recombination, mutation and energy
accounting. World owns the living data arrays and invokes this procedure.
Mutation and crossover must NOT be called from UI or science recording code.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from .genetics import mutate, recombine
from .regulatory import inherit_programs, empty_programs

if TYPE_CHECKING:
    from .simulation import World


def reproduce_biological(self: World) -> int:
    """Local mating (or budding), crossover, mutation and energy-conserving births.

    There is no top-percentile survival shortcut. Organisms must acquire
    enough actual food to reproduce; others may starve or die of old age.
    """
    cfg = self.config
    if not cfg.allow_reproduction or self.population >= cfg.max_population:
        return 0
    bio = self.biology()
    threshold = cfg.reproduction_threshold * bio["investment"]
    ready = np.flatnonzero((self.age >= cfg.reproduction_age * bio["maturation"]) &
                               (self.energy >= threshold))
    if not len(ready):
        return 0
    self.rng.shuffle(ready)
    # Spatially local partner search over 9x9 cells, not global fitness ranking.
    from collections import defaultdict
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    row, col = self._cells(self.x[ready], self.y[ready])
    for idx, yy, xx in zip(ready, row, col):
        buckets[(int(yy), int(xx))].append(int(idx))
    used: set[int] = set()
    first: list[int] = []
    second: list[int] = []
    max_births = cfg.max_population - self.population
    for i in ready:
        i = int(i)
        if i in used or len(first) >= max_births:
            continue
        mate = -1
        if cfg.reproduction_mode != "asexual":
            cy, cx = self._cells(self.x[i:i + 1], self.y[i:i + 1])
            choices = []
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    yy, xx = int(cy[0]) + dy, int(cx[0]) + dx
                    if cfg.boundary_mode == "wrap":
                        yy %= cfg.height
                        xx %= cfg.width
                    elif not (0 <= yy < cfg.height and 0 <= xx < cfg.width):
                        continue
                    for j in buckets.get((yy, xx), []):
                        if j == i or j in used:
                            continue
                        x_dist, y_dist = abs(self.x[j] - self.x[i]), abs(self.y[j] - self.y[i])
                        if cfg.boundary_mode == "wrap":
                            x_dist = min(x_dist, cfg.width - x_dist)
                            y_dist = min(y_dist, cfg.height - y_dist)
                        if x_dist * x_dist + y_dist * y_dist <= 16.0:
                            choices.append(j)
            if choices:
                mate = choices[int(self.rng.integers(len(choices)))]
        if mate == -1 and cfg.reproduction_mode == "sexual":
            continue
        first.append(i)
        second.append(mate)
        used.add(i)
        if mate != -1:
            used.add(mate)
    born = len(first)
    if born == 0:
        return 0
    a = np.asarray(first, dtype=np.intp)
    b = np.asarray(second, dtype=np.intp)
    is_pair = b >= 0
    new_genomes = self.genomes[a].copy()
    new_dna = self.body_dna[a].copy()
    new_copies = self.gene_copies[a].copy()
    if np.any(is_pair):
        ba, bb = a[is_pair], b[is_pair]
        neural_mask = self.rng.random(new_genomes[is_pair].shape) < .5
        new_genomes[is_pair] = np.where(neural_mask, self.genomes[ba], self.genomes[bb])
        cross_dna, cross_copies = recombine(self.body_dna[ba], self.gene_copies[ba],
                                            self.body_dna[bb], self.gene_copies[bb], self.rng)
        new_dna[is_pair], new_copies[is_pair] = cross_dna, cross_copies
    neural_changes = np.zeros(born, dtype=np.int32)
    if cfg.allow_mutation:
        if cfg.mutation_probability:
            mask = self.rng.random(new_genomes.shape) < cfg.mutation_probability
            new_genomes += mask * self.rng.normal(0, cfg.mutation_strength, new_genomes.shape)
            np.clip(new_genomes, -5, 5, out=new_genomes)
            neural_changes = mask.reshape(born, -1).sum(axis=1).astype(np.int32)
        batch = mutate(new_dna, new_copies, self.rng,
                       point_rate=cfg.body_mutation_probability,
                       strength=cfg.body_mutation_strength,
                       copy_rate=cfg.copy_mutation_probability)
        new_dna, new_copies = batch.dna, batch.copies
        self.total_body_mutations += int(batch.point_changes.sum())
        self.total_copy_mutations += int(batch.copy_changes.sum())
        neural_changes += batch.point_changes + batch.copy_changes
    # Heritable variable-length gene programs. No extra random draws occur for
    # historical worlds, preserving old evolutionary experiment fingerprints.
    if cfg.regulation_enabled:
        children_programs, children_lengths = empty_programs(born)
        for child_index, pa in enumerate(a):
            pb = int(b[child_index])
            child, size, self.next_gene_innovation, changes = inherit_programs(
                self.regulatory_programs[pa], self.regulatory_lengths[pa],
                self.regulatory_programs[pb] if pb >= 0 else None,
                self.regulatory_lengths[pb] if pb >= 0 else None,
                self.rng, self.next_gene_innovation,
                mutate_enabled=cfg.allow_mutation,
                point_rate=cfg.regulatory_point_rate,
                structural_rate=cfg.regulatory_structure_rate)
            children_programs[child_index], children_lengths[child_index] = child, size
            self.regulatory_new_genes += changes['insertions'] + changes['duplications']
            self.regulatory_mutations += sum(changes.values())
            self.regulatory_new_chromosomes += changes['chromosome_births']
            neural_changes[child_index] += sum(changes.values())
    else:
        children_programs, children_lengths = empty_programs(born)
    self.sexual_births += int(np.count_nonzero(is_pair))
    # Reproductive investment affects both payment and initial offspring energy;
    # paired parents contribute half each. It never creates net energy.
    spend_a = cfg.reproduction_cost * bio["investment"][a]
    cost_a = np.where(is_pair, spend_a / 2, spend_a)
    self.energy[a] -= cost_a
    np.add.at(self.offspring_count, a, 1)
    first_a = self.first_offspring_tick[a] < 0
    self.first_offspring_tick[a[first_a]] = self.tick
    if np.any(is_pair):
        pb = b[is_pair]
        self.energy[pb] -= cfg.reproduction_cost * bio["investment"][pb] / 2
        np.add.at(self.offspring_count, pb, 1)
        first_b = self.first_offspring_tick[pb] < 0
        self.first_offspring_tick[pb[first_b]] = self.tick
    available = (spend_a + np.where(is_pair,
                   cfg.reproduction_cost * bio["investment"][np.maximum(b, 0)], 0)) / (1 + is_pair)
    newborn = cfg.newborn_energy / cfg.reproduction_cost * available
    ids = np.arange(self.next_id, self.next_id + born, dtype=np.int64)
    self.next_id += born
    px = self.x[a] + self.rng.normal(0, 1.3, born)
    py = self.y[a] + self.rng.normal(0, 1.3, born)
    if cfg.boundary_mode == "wrap":
        px %= cfg.width
        py %= cfg.height
    else:
        px = self._reflect_coordinate(px, cfg.width)
        py = self._reflect_coordinate(py, cfg.height)
    born_gen = np.maximum(self.generation[a], self.generation[np.maximum(b, 0)]) + 1
    self.x = np.concatenate((self.x, px))
    self.y = np.concatenate((self.y, py))
    self.angle = np.concatenate((self.angle, self.rng.uniform(-np.pi, np.pi, born)))
    self.energy = np.concatenate((self.energy, newborn))
    self.age = np.concatenate((self.age, np.zeros(born, dtype=np.int32)))
    parent_a, parent_b = self.ids[a].copy(), np.where(is_pair, self.ids[np.maximum(b, 0)], -1)
    self.parents = np.concatenate((self.parents, parent_a))
    self.second_parents = np.concatenate((self.second_parents, parent_b))
    self.ids = np.concatenate((self.ids, ids))
    self.generation = np.concatenate((self.generation, born_gen))
    self.genomes = np.concatenate((self.genomes, new_genomes))
    self.body_dna = np.concatenate((self.body_dna, new_dna))
    self.gene_copies = np.concatenate((self.gene_copies, new_copies))
    self.regulatory_programs = np.concatenate((self.regulatory_programs, children_programs))
    self.regulatory_lengths = np.concatenate((self.regulatory_lengths, children_lengths))
    self.mutation_count = np.concatenate((self.mutation_count, neural_changes))
    self.last_intake = np.concatenate((self.last_intake, np.zeros(born)))
    self.life_harvest = np.concatenate((self.life_harvest, np.zeros(born)))
    self.life_distance = np.concatenate((self.life_distance, np.zeros(born)))
    self.peak_energy = np.concatenate((self.peak_energy, newborn))
    self.offspring_count = np.concatenate((self.offspring_count, np.zeros(born, dtype=np.int32)))
    self.birth_tick = np.concatenate((self.birth_tick, np.full(born, self.tick, dtype=np.int64)))
    self.first_meal_tick = np.concatenate((self.first_meal_tick, np.full(born, -1, dtype=np.int64)))
    self.first_offspring_tick = np.concatenate((self.first_offspring_tick, np.full(born, -1, dtype=np.int64)))
    self.total_births += born
    self.last_events.extend({"tick": self.tick, "kind": "birth", "id": int(id_),
                             "parent_id": int(pa), "parent2_id": int(pb), "generation": int(gen),
                             "x": float(xx), "y": float(yy)}
                            for id_, pa, pb, gen, xx, yy in
                            zip(ids, parent_a, parent_b, born_gen, px, py))
    return born

