"""Accidental Biosphere: deterministic, vectorized, asynchronous-birth digital ecology.

There is NO scripted food seeking, social action, combat, parenting, or survival policy.
The genome maps local measurements to angular and forward motor commands.
Organisms acquire food from the grid cell they occupy; reproduction is triggered by
sufficient stored energy, not by a dedicated behavioral choice.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from .genetics import LOCI, founder_dna, traits, neutral_traits, phenotype_summary
from .reproduction import reproduce_biological
from .archive_storage import DiskArchive
from .regulatory import (empty_programs, founder_programs, evaluate, expression_signals,
                         describe, MAX_GENES, CHROM)
from .state_schema import (SCHEMA_VERSION, LIVE_ARRAY_FIELDS, SAVED_ARRAY_FIELDS,
                           LEGACY_REQUIRED_FIELDS, validate_world_state)

# Each column is directly interpretable in the small linear neural controller.
SENSORS = ("bias", "food_ahead", "food_left", "food_right", "forward_contrast",
           "left_right_contrast", "energy_fraction", "crowding")
MOTORS = ("turn", "speed")
GENES = (2, len(SENSORS))


@dataclass(frozen=True)
class Config:
    width: int = 72
    height: int = 54
    founders: int = 180
    max_population: int = 900
    initial_energy: float = 32.0
    metabolism: float = 0.20
    move_cost: float = 0.065
    max_bite: float = 1.45
    food_gain: float = 1.75
    growth_rate: float = 0.030
    resource_background: float = 0.25
    resource_patchiness: float = 1.0
    resource_layout: str = "hills"  # hills / islands (spatially separated rare patches)
    island_count: int = 8
    island_sigma: float = 2.8
    island_peak: float = 10.0
    lifespan: int = 330
    reproduction_age: int = 15
    reproduction_threshold: float = 47.0
    reproduction_cost: float = 27.0
    newborn_energy: float = 22.0
    mutation_probability: float = 0.14
    mutation_strength: float = 0.28
    sensor_distance: float = 3.0
    max_turn: float = 0.60
    max_speed: float = 0.90
    boundary_mode: str = "wrap"  # wrap / reflect (specular bouncing)
    patch_shift_interval: int = 0  # zero = stationary; shift both food and capacity
    # Modes used in preregistered experimental interventions.
    sensor_mode: str = "normal"  # normal / blind / food_blind / crowd_blind / mirror_food
    # Experimental motor interventions, never enabled by the normal ecology.
    # Useful for distinguishing speed from steering when comparing genotypes.
    fixed_speed: float | None = None
    fixed_turn: float | None = None
    allow_reproduction: bool = True
    allow_mutation: bool = True
    # Opt-in expanded biology; historical scientific experiments retain exact v0.9 dynamics.
    genetics_enabled: bool = False
    reproduction_mode: str = "mixed"  # asexual / sexual / mixed; hermaphroditic organisms
    body_mutation_probability: float = .045
    body_mutation_strength: float = .22
    copy_mutation_probability: float = .008
    regulation_enabled: bool = False
    regulatory_point_rate: float = .08
    regulatory_structure_rate: float = .04

    def __post_init__(self) -> None:
        if self.width < 8 or self.height < 8 or self.founders < 0 or self.max_population < 1:
            raise ValueError("Invalid world dimensions or population")
        if self.founders > self.max_population:
            raise ValueError("Founder count cannot exceed population limit")
        if self.resource_layout not in ("hills", "islands"):
            raise ValueError("Unsupported resource_layout")
        if self.island_count < 1 or self.island_sigma <= 0 or self.island_peak <= 0:
            raise ValueError("Invalid island geometry")
        if self.resource_background < 0 or self.resource_patchiness < 0:
            raise ValueError("Invalid resource background or patchiness")
        if self.boundary_mode not in ("wrap", "reflect"):
            raise ValueError("Unsupported boundary_mode")
        if self.patch_shift_interval < 0:
            raise ValueError("patch_shift_interval must be nonnegative")
        if self.move_cost < 0:
            raise ValueError("move_cost must be nonnegative")
        if self.sensor_mode not in ("normal", "blind", "food_blind", "crowd_blind", "mirror_food"):
            raise ValueError("Unsupported sensor_mode")
        if self.fixed_speed is not None and not 0 <= self.fixed_speed <= self.max_speed:
            raise ValueError("fixed_speed must be between 0 and max_speed")
        if self.fixed_turn is not None and not -self.max_turn <= self.fixed_turn <= self.max_turn:
            raise ValueError("fixed_turn exceeds max_turn")
        if not (0 <= self.mutation_probability <= 1):
            raise ValueError("mutation_probability must be in [0, 1]")
        if self.reproduction_mode not in ("asexual", "sexual", "mixed"):
            raise ValueError("Invalid reproduction mode")
        if not 0 <= self.body_mutation_probability <= 1 or not 0 <= self.copy_mutation_probability <= 1:
            raise ValueError("Biological mutation rates must be in [0, 1]")
        if self.regulation_enabled and not self.genetics_enabled:
            raise ValueError("Regulation requires the expanded genetics system")
        for rate in (self.regulatory_point_rate, self.regulatory_structure_rate):
            if not 0 <= rate <= 1 or not math.isfinite(rate):
                raise ValueError("Invalid regulatory mutation rate")
        if self.body_mutation_strength < 0:
            raise ValueError("Biological mutation strength must be nonnegative")
        if self.newborn_energy > self.reproduction_cost:
            raise ValueError("Reproduction may not create energy")
        if self.reproduction_threshold <= self.reproduction_cost:
            raise ValueError("Reproduction must retain some parent energy")
        if self.metabolism < 0 or self.food_gain < 0 or not (0 <= self.growth_rate <= 1):
            raise ValueError("Invalid ecological rates")
        # NaN bypasses ordinary >/< comparisons; catch invalid user/JSON input.
        finite_fields = ("initial_energy", "metabolism", "move_cost", "max_bite",
                         "food_gain", "growth_rate", "resource_background",
                         "resource_patchiness", "island_sigma", "island_peak",
                         "reproduction_threshold", "reproduction_cost",
                         "newborn_energy", "mutation_probability",
                         "mutation_strength", "sensor_distance", "max_turn",
                         "max_speed", "body_mutation_probability",
                         "body_mutation_strength", "copy_mutation_probability")
        if any(not math.isfinite(getattr(self, name)) for name in finite_fields):
            raise ValueError("Configuration contains nonfinite parameters")
        nonnegative = ("initial_energy", "max_bite", "newborn_energy",
                       "sensor_distance", "max_turn", "max_speed",
                       "mutation_strength", "resource_patchiness")
        if any(getattr(self, name) < 0 for name in nonnegative):
            raise ValueError("Configuration contains negative ecological parameters")
        if self.lifespan < 1 or self.reproduction_age < 0:
            raise ValueError("Invalid lifespan or reproductive age")


def patch_landscape(config: Config, rng: np.random.Generator) -> np.ndarray:
    """Generate stationary resource-capacity hills, not fixed foraging routes."""
    yy, xx = np.mgrid[:config.height, :config.width]
    cap = np.full((config.height, config.width), config.resource_background,
                  dtype=np.float64)
    if config.resource_layout == "islands":
        # Environmental structure only. Organisms are never given the island
        # positions, objectives, or a navigation routine. Sampling is identical.
        centers: list[tuple[float, float]] = []
        min_sep = max(3.0, 3.8 * config.island_sigma)
        for _ in range(config.island_count):
            # Pick the best-spaced candidate out of a bounded random search.
            # This works even in tiny test arenas where perfect separation is
            # mathematically impossible. No seed-dependent unbounded loop.
            trials = rng.uniform([0, 0], [config.width, config.height], size=(80, 2))
            if centers:
                prior = np.asarray(centers)
                diff = np.abs(trials[:, None, :] - prior[None, :, :])
                if config.boundary_mode == "wrap":
                    diff = np.minimum(diff, np.array([config.width, config.height]) - diff)
                distances = np.sqrt(np.sum(diff ** 2, axis=2))
                scores = np.min(distances, axis=1)
                acceptable = np.flatnonzero(scores >= min_sep)
                idx = int(acceptable[0]) if len(acceptable) else int(np.argmax(scores))
            else:
                idx = 0
            cx, cy = map(float, trials[idx])
            centers.append((cx, cy))
            dx, dy = np.abs(xx - cx), np.abs(yy - cy)
            if config.boundary_mode == "wrap":
                dx, dy = np.minimum(dx, config.width - dx), np.minimum(dy, config.height - dy)
            cap += config.island_peak * np.exp(-0.5 * (dx * dx + dy * dy) / config.island_sigma ** 2)
        return np.clip(cap, 0.01, 12.0)
    # Smooth localized hills are periodic: no boundary discontinuity on torus.
    for _ in range(max(5, round(config.width * config.height / 220))):
        cx = rng.uniform(0, config.width)
        cy = rng.uniform(0, config.height)
        rx = rng.uniform(2.8, 8.0)
        ry = rng.uniform(2.8, 7.0)
        dx = np.abs(xx - cx)
        dy = np.abs(yy - cy)
        dx = np.minimum(dx, config.width - dx)
        dy = np.minimum(dy, config.height - dy)
        cap += config.resource_patchiness * rng.uniform(1.1, 3.8) * np.exp(
            -0.5 * ((dx / rx) ** 2 + (dy / ry) ** 2))
    return np.clip(cap, 0.05, 12.0)


class World:
    def __init__(self, config: Config | None = None, seed: int = 1,
                 founder_genomes: np.ndarray | None = None):
        self.config = config if config is not None else Config()
        self.seed = int(seed)
        self.rng = np.random.default_rng(self.seed)
        self.capacity = patch_landscape(self.config, self.rng)
        self.food = self.capacity.copy()
        n = self.config.founders if founder_genomes is None else len(founder_genomes)
        if n > self.config.max_population:
            raise ValueError("Too many founder genomes")
        self.x = self.rng.uniform(0, self.config.width, n)
        self.y = self.rng.uniform(0, self.config.height, n)
        self.angle = self.rng.uniform(-np.pi, np.pi, n)
        self.energy = np.full(n, self.config.initial_energy, dtype=np.float64)
        self.age = np.zeros(n, dtype=np.int32)
        self.ids = np.arange(n, dtype=np.int64)
        self.parents = np.full(n, -1, dtype=np.int64)
        self.second_parents = np.full(n, -1, dtype=np.int64)
        self.generation = np.zeros(n, dtype=np.int32)
        self.genomes = (self.rng.normal(0, 0.7, (n, *GENES)) if founder_genomes is None
                        else np.asarray(founder_genomes, dtype=np.float64).copy())
        if self.genomes.shape != (n, *GENES):
            raise ValueError(f"Genomes must have shape (n, {GENES[0]}, {GENES[1]})")
        if self.config.genetics_enabled:
            batch = founder_dna(self.rng, n)
            self.body_dna, self.gene_copies = batch.dna, batch.copies
        else:
            self.body_dna = np.zeros((n, len(LOCI)), dtype=np.float64)
            self.gene_copies = np.ones((n, len(LOCI)), dtype=np.int8)
        if self.config.regulation_enabled:
            self.regulatory_programs, self.regulatory_lengths, self.next_gene_innovation = (
                founder_programs(self.rng, n))
        else:
            self.regulatory_programs, self.regulatory_lengths = empty_programs(n)
            self.next_gene_innovation = 1
        self.regulatory_mutations = 0
        self.regulatory_new_genes = 0
        self.regulatory_new_chromosomes = 0
        self.mutation_count = np.zeros(n, dtype=np.int32)
        self.total_body_mutations = 0
        self.total_copy_mutations = 0
        self.sexual_births = 0
        self.tick = 0
        self.next_id = n
        self.total_births = 0
        self.total_deaths = 0
        self.total_harvest = 0.0
        self.death_causes: dict[str, int] = {"starvation": 0, "age": 0}
        self.last_events: list[dict[str, Any]] = []
        self.last_mean_intake = 0.0
        self.last_total_intake = 0.0
        self.last_mean_speed = 0.0
        self.last_directionality = 0.0
        self.last_wall_hits = 0
        self.cumulative_wall_hits = 0
        self.patch_moves = 0
        # Inspector-only data, aligned with *currently living* organism IDs.
        # Neither changes motor outputs nor consumes random numbers.
        self.last_intake = np.zeros(n, dtype=np.float64)
        # Observation-only, vectorized life counters; motor evolution is unchanged.
        self.life_harvest = np.zeros(n, dtype=np.float64)
        self.life_distance = np.zeros(n, dtype=np.float64)
        self.peak_energy = self.energy.copy()
        self.offspring_count = np.zeros(n, dtype=np.int32)
        self.birth_tick = np.zeros(n, dtype=np.int64)
        self.first_meal_tick = np.full(n, -1, dtype=np.int64)
        self.first_offspring_tick = np.full(n, -1, dtype=np.int64)
        self.life_archive: dict[int, dict[str, Any]] = {}
        # Recent event and trend history, bounded independently of population.
        self.observation_log: list[dict[str, Any]] = []
        self.notable_events: list[dict[str, Any]] = []
        self.population_history: list[tuple[int, int, float]] = [(0, n, 0.0)]
        # Opt-in specimen tracks (bounded) are recorded from the moment selected.
        self.watch_traces: dict[int, list[dict[str, float | int]]] = {}
        # Manual terrain edits are isolated to the viewer's explicitly labeled
        # sandbox mode; experiments never call fertilize().
        self.manual_interventions: list[dict[str, Any]] = []

    def biology(self) -> dict[str, np.ndarray]:
        """Inheritable phenotype with age-dependent juvenile physical development.

        Growth is the same physiological expression rule for all organisms;
        an individual's maturation locus determines how quickly it develops.
        There is no programmed food-seeking, goal or optimal adaptation.
        """
        if not self.config.genetics_enabled:
            return neutral_traits(self.population)
        expressed = traits(self.body_dna, self.gene_copies)
        if self.config.regulation_enabled and self.population:
            signals = self._regulation_signals()
            signals_out = evaluate(self.regulatory_programs, self.regulatory_lengths, signals)
            for name, channel in (("maintenance", 0), ("food_gain", 1),
                                  ("propulsion", 2), ("agility", 3),
                                  ("sensor_gain", 4), ("size", 5),
                                  ("investment", 6)):
                expressed[name] *= np.exp(.17 * signals_out[:, channel])
            # Regulatory machinery costs energy even if the new effects are neutral.
            expressed["maintenance"] *= 1. + .006 * self.regulatory_lengths
        adult_age = np.maximum(1., self.config.reproduction_age * expressed["maturation"])
        maturity = np.clip(self.age / adult_age, 0., 1.)
        expressed["size"] *= .55 + .45 * maturity
        expressed["bite"] *= .60 + .40 * maturity
        expressed["propulsion"] *= .75 + .25 * maturity
        expressed["maintenance"] *= .70 + .30 * maturity
        return expressed

    def _regulation_signals(self) -> np.ndarray:
        """Food, energy, crowding, age and left/right food gradients; no policy."""
        cfg = self.config
        n = self.population
        food = self._sample_food(self.x, self.y)
        if cfg.sensor_mode in ("blind", "food_blind"):
            food = np.zeros(n)
            asymmetry = np.zeros(n)
        else:
            left = self._sample_food(self.x + cfg.sensor_distance * np.cos(self.angle + np.pi/3),
                                     self.y + cfg.sensor_distance * np.sin(self.angle + np.pi/3))
            right = self._sample_food(self.x + cfg.sensor_distance * np.cos(self.angle - np.pi/3),
                                      self.y + cfg.sensor_distance * np.sin(self.angle - np.pi/3))
            asymmetry = left - right
            if cfg.sensor_mode == "mirror_food":
                asymmetry = -asymmetry
        iy, ix = self._cells(self.x, self.y)
        counts = np.bincount(iy * cfg.width + ix, minlength=cfg.height * cfg.width)
        crowd = np.clip((counts[iy * cfg.width + ix] - 1) / 8, 0, 1)
        if cfg.sensor_mode in ("blind", "crowd_blind"):
            crowd[:] = 0
        return expression_signals(food=food, energy=self.energy / cfg.reproduction_threshold,
                                  crowd=crowd, maturity=self.age / cfg.lifespan,
                                  asymmetry=asymmetry)

    def regulation(self) -> np.ndarray:
        """Read-only current expression outputs for the selected genotype."""
        if not self.config.regulation_enabled:
            return np.zeros((self.population, 9))
        return evaluate(self.regulatory_programs, self.regulatory_lengths,
                        self._regulation_signals())

    def fertilize(self, x: float, y: float, *, radius: float = 2.4,
                  strength: float = 3.0) -> float:
        """Sandbox-only brush: increase carrying capacity and matching food.

        Deterministic, bounded and saved as an intervention. Replaces neither
        genomes nor survival policies; marks the environment as manipulated.
        """
        if not (np.isfinite(x) and np.isfinite(y) and np.isfinite(radius) and
                np.isfinite(strength) and radius > 0 and strength > 0):
            raise ValueError("Invalid fertilize brush parameters")
        yy, xx = np.mgrid[:self.config.height, :self.config.width]
        dx, dy = np.abs(xx - x), np.abs(yy - y)
        if self.config.boundary_mode == "wrap":
            dx = np.minimum(dx, self.config.width - dx)
            dy = np.minimum(dy, self.config.height - dy)
        bloom = strength * np.exp(-0.5 * (dx * dx + dy * dy) / radius ** 2)
        new_capacity = np.minimum(self.capacity + bloom, 12.0)
        added = new_capacity - self.capacity
        self.capacity = new_capacity
        self.food = np.minimum(self.food + added, self.capacity)
        amount = float(np.sum(added))
        self.manual_interventions.append({"tick": self.tick, "kind": "fertilize",
                                          "x": float(x), "y": float(y),
                                          "radius": float(radius), "added": amount})
        return amount

    @property
    def population(self) -> int:
        return len(self.x)

    @staticmethod
    def _reflect_coordinate(pos: np.ndarray, limit: int) -> np.ndarray:
        """Mirrored extension of a closed wall, safe at exact grid limits."""
        projected = np.mod(pos, 2 * limit)
        reflected = np.where(projected < limit, projected, 2 * limit - projected)
        return np.minimum(reflected, np.nextafter(float(limit), 0.0))

    def _cells(self, x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.config.boundary_mode == "wrap":
            return np.floor(y).astype(np.intp) % self.config.height, np.floor(x).astype(np.intp) % self.config.width
        cy = self._reflect_coordinate(y, self.config.height)
        cx = self._reflect_coordinate(x, self.config.width)
        return np.floor(cy).astype(np.intp), np.floor(cx).astype(np.intp)

    def _sample_food(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        iy, ix = self._cells(x, y)
        # Absolute available energy density (normalized), not percent full.
        # Otherwise organisms could never detect a rich patch at initial saturation.
        return np.clip(self.food[iy, ix] / 12.0, 0, 1)

    def perceive(self) -> np.ndarray:
        """Neural input in egocentric orientation. No action is hardcoded."""
        n = self.population
        if n == 0:
            return np.empty((0, len(SENSORS)), dtype=np.float64)
        d = self.config.sensor_distance * self.biology()["sensor_range"]
        offsets = (0, np.pi / 3, -np.pi / 3)
        fs = [self._sample_food(self.x + d * np.cos(self.angle + o),
                                self.y + d * np.sin(self.angle + o))
              for o in offsets]
        f, l, r = fs
        iy, ix = self._cells(self.x, self.y)
        counts = np.bincount(iy * self.config.width + ix, minlength=self.config.height * self.config.width)
        crowd = np.minimum(counts[iy * self.config.width + ix] - 1, 8) / 8.0
        state = np.stack((np.ones(n), f, l, r, f - (l + r) / 2, l - r,
                          np.clip(self.energy / self.config.reproduction_threshold, 0, 2),
                          crowd), axis=1)
        if self.config.genetics_enabled:
            state[:, 1:6] *= self.biology()["sensor_gain"][:, None]
        if self.config.sensor_mode == "blind":
            # Retain the internal energy signal & bias; blind only external senses.
            state[:, 1:6] = 0.0
            state[:, 7] = 0.0
        elif self.config.sensor_mode == "food_blind":
            state[:, 1:6] = 0.0
        elif self.config.sensor_mode == "crowd_blind":
            state[:, 7] = 0.0
        elif self.config.sensor_mode == "mirror_food":
            # Preserve forward readings and lateral magnitude, but reverse
            # their compass directions. This is a causal intervention, not
            # natural evolution or a trained behavior.
            state[:, [2, 3]] = state[:, [3, 2]]
            state[:, 5] *= -1
        return state

    def controls(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        sensors = self.perceive()
        if not len(sensors):
            return np.empty(0), np.empty(0), sensors
        outputs = np.einsum("nij,nj->ni", self.genomes, sensors)
        bio = self.biology()
        if self.config.regulation_enabled:
            regulation = self.regulation()
            outputs[:, 0] += regulation[:, 7] * .40
            outputs[:, 1] += regulation[:, 8] * .40
        turn = np.tanh(outputs[:, 0]) * self.config.max_turn * bio["agility"]
        # Linear controller output squashed to a nonnegative propulsion magnitude.
        speed = ((0.05 + 0.95 / (1 + np.exp(-np.clip(outputs[:, 1], -20, 20)))) *
                 self.config.max_speed * bio["propulsion"])
        if self.config.fixed_speed is not None:
            speed = np.full(len(speed), self.config.fixed_speed)
        if self.config.fixed_turn is not None:
            turn = np.full(len(turn), self.config.fixed_turn)
        return turn, speed, sensors

    def step(self) -> dict[str, Any]:
        cfg = self.config
        self.tick += 1
        self.last_events = []
        self.last_wall_hits = 0
        if cfg.patch_shift_interval and self.tick % cfg.patch_shift_interval == 0:
            # Move both the food stock and the carrying-capacity landscape:
            # patches relocate without instantly creating or deleting food.
            sx = int(self.rng.integers(6, max(7, cfg.width // 3 + 1)))
            sy = int(self.rng.integers(6, max(7, cfg.height // 3 + 1)))
            # Include both directions; environmental movement is not learned.
            sx *= int(self.rng.choice((-1, 1)))
            sy *= int(self.rng.choice((-1, 1)))
            self.capacity = np.roll(self.capacity, (sy, sx), axis=(0, 1))
            self.food = np.roll(self.food, (sy, sx), axis=(0, 1))
            self.patch_moves += 1
        n = self.population
        if n == 0:
            self.food += cfg.growth_rate * (self.capacity - self.food)
            self.last_mean_intake = 0.0
            self.last_total_intake = 0.0
            self.last_mean_speed = 0.0
            self.last_directionality = 0.0
            self.last_intake = np.empty(0, dtype=np.float64)
            return self.stats(0, 0, detailed=False)

        turn, speed, senses = self.controls()
        self.last_mean_speed = float(np.mean(speed))
        contrast = senses[:, 5]
        self.last_directionality = float(np.mean(turn * contrast)) if cfg.sensor_mode == "normal" else 0.0
        self.angle = (self.angle + turn + np.pi) % (2 * np.pi) - np.pi
        next_x = self.x + speed * np.cos(self.angle)
        next_y = self.y + speed * np.sin(self.angle)
        if cfg.boundary_mode == "wrap":
            self.x = next_x % cfg.width
            self.y = next_y % cfg.height
        else:
            hit_x = (next_x < 0) | (next_x >= cfg.width)
            hit_y = (next_y < 0) | (next_y >= cfg.height)
            self.last_wall_hits = int(np.count_nonzero(hit_x | hit_y))
            self.cumulative_wall_hits += self.last_wall_hits
            self.x = self._reflect_coordinate(next_x, cfg.width)
            self.y = self._reflect_coordinate(next_y, cfg.height)
            self.angle = np.where(hit_x, np.pi - self.angle, self.angle)
            self.angle = np.where(hit_y, -self.angle, self.angle)
            self.angle = (self.angle + np.pi) % (2 * np.pi) - np.pi
        self.age += 1

        iy, ix = self._cells(self.x, self.y)
        indices = iy * cfg.width + ix
        # Simultaneous, equitable sharing: np.add.at avoids repeated-index over-crediting.
        counts = np.bincount(indices, minlength=cfg.height * cfg.width)
        bio = self.biology()
        intake = np.minimum(cfg.max_bite * bio["bite"], self.food[iy, ix] / counts[indices])
        np.add.at(self.food, (iy, ix), -intake)
        self.food = np.clip(self.food, 0, self.capacity)
        self.last_intake = intake.copy()
        self.life_harvest += intake
        self.life_distance += speed
        self.peak_energy = np.maximum(self.peak_energy, self.energy)
        new_meals = (self.first_meal_tick < 0) & (intake > 1e-8)
        self.first_meal_tick[new_meals] = self.tick
        self.last_mean_intake = float(np.mean(intake))
        self.last_total_intake = float(np.sum(intake))
        self.total_harvest += self.last_total_intake
        self.energy += (intake * cfg.food_gain * bio["food_gain"] -
                        cfg.metabolism * bio["maintenance"] -
                        speed * cfg.move_cost * bio["size"] * (bio["propulsion"] ** .5))
        self.peak_energy = np.maximum(self.peak_energy, self.energy)
        dead_starvation = self.energy <= 0
        dead_old = self.age >= cfg.lifespan * bio["longevity"]
        dead = dead_starvation | dead_old
        self.death_causes["starvation"] += int(np.sum(dead_starvation))
        self.death_causes["age"] += int(np.sum(dead_old & ~dead_starvation))
        died = int(np.sum(dead))
        if died:
            for dead_idx in np.flatnonzero(dead):
                dead_id = int(self.ids[dead_idx])
                self.life_archive[dead_id] = {
                    "id": dead_id, "parent_id": int(self.parents[dead_idx]),
                    "parent2_id": int(self.second_parents[dead_idx]),
                    "body_dna": self.body_dna[dead_idx].tolist(),
                    "gene_copies": self.gene_copies[dead_idx].tolist(),
                    "regulatory_genes": describe(self.regulatory_programs[dead_idx],
                                                 self.regulatory_lengths[dead_idx]),
                    "mutation_count": int(self.mutation_count[dead_idx]),
                    "generation": int(self.generation[dead_idx]),
                    "born_tick": int(self.birth_tick[dead_idx]),
                    "died_tick": int(self.tick),
                    "cause": "starvation" if dead_starvation[dead_idx] else "age",
                    "age": int(self.age[dead_idx]),
                    "x": float(self.x[dead_idx]), "y": float(self.y[dead_idx]),
                    "final_energy": float(self.energy[dead_idx]),
                    "peak_energy": float(self.peak_energy[dead_idx]),
                    "food_harvested": float(self.life_harvest[dead_idx]),
                    "distance_traveled": float(self.life_distance[dead_idx]),
                    "offspring": int(self.offspring_count[dead_idx]),
                    "first_meal_tick": int(self.first_meal_tick[dead_idx]),
                    "first_offspring_tick": int(self.first_offspring_tick[dead_idx]),
                    "genome": self.genomes[dead_idx].tolist(),
                }
                self.last_events.append({"tick": self.tick, "kind": "death",
                                         "id": int(self.ids[dead_idx]),
                                         "cause": "starvation" if dead_starvation[dead_idx] else "age",
                                         "x": float(self.x[dead_idx]), "y": float(self.y[dead_idx])})
            if isinstance(self.life_archive, DiskArchive):
                self.life_archive.flush()
            self._retain(~dead)
            self.total_deaths += died

        born = 0
        if cfg.genetics_enabled:
            born = self._reproduce_biological()
        else:
            if cfg.allow_reproduction and self.population < cfg.max_population:
                candidates = np.flatnonzero((self.age >= cfg.reproduction_age) &
                                             (self.energy >= cfg.reproduction_threshold))
                self.rng.shuffle(candidates)  # cap is allocated without agent-id priority
                candidates = candidates[:cfg.max_population - self.population]
                born = len(candidates)
                if born:
                    parent_ids = self.ids[candidates].copy()
                    newborn_ids = np.arange(self.next_id, self.next_id + born, dtype=np.int64)
                    self.next_id += born
                    child_genomes = self.genomes[candidates].copy()
                    if cfg.allow_mutation and cfg.mutation_probability:
                        mask = self.rng.random(child_genomes.shape) < cfg.mutation_probability
                        child_genomes += mask * self.rng.normal(0, cfg.mutation_strength, child_genomes.shape)
                        np.clip(child_genomes, -5, 5, out=child_genomes)
                    child_x = self.x[candidates] + self.rng.normal(0, 1.3, born)
                    child_y = self.y[candidates] + self.rng.normal(0, 1.3, born)
                    if cfg.boundary_mode == "wrap":
                        child_x %= cfg.width
                        child_y %= cfg.height
                    else:
                        child_x = self._reflect_coordinate(child_x, cfg.width)
                        child_y = self._reflect_coordinate(child_y, cfg.height)
                    child_angle = self.rng.uniform(-np.pi, np.pi, born)
                    child_generation = self.generation[candidates] + 1
                    self.energy[candidates] -= cfg.reproduction_cost
                    self.offspring_count[candidates] += 1
                    first_parent = self.first_offspring_tick[candidates] < 0
                    self.first_offspring_tick[candidates[first_parent]] = self.tick
                    self.x = np.concatenate((self.x, child_x))
                    self.y = np.concatenate((self.y, child_y))
                    self.angle = np.concatenate((self.angle, child_angle))
                    self.energy = np.concatenate((self.energy, np.full(born, cfg.newborn_energy)))
                    self.age = np.concatenate((self.age, np.zeros(born, dtype=np.int32)))
                    self.ids = np.concatenate((self.ids, newborn_ids))
                    self.parents = np.concatenate((self.parents, parent_ids))
                    self.generation = np.concatenate((self.generation, child_generation))
                    self.genomes = np.concatenate((self.genomes, child_genomes))
                    self.body_dna = np.concatenate((self.body_dna, np.zeros((born, len(LOCI)))))
                    self.gene_copies = np.concatenate((self.gene_copies, np.ones((born, len(LOCI)), dtype=np.int8)))
                    program, lengths = empty_programs(born)
                    self.regulatory_programs = np.concatenate((self.regulatory_programs, program))
                    self.regulatory_lengths = np.concatenate((self.regulatory_lengths, lengths))
                    self.second_parents = np.concatenate((self.second_parents, np.full(born, -1, dtype=np.int64)))
                    self.mutation_count = np.concatenate((self.mutation_count, np.zeros(born, dtype=np.int32)))
                    self.last_intake = np.concatenate((self.last_intake, np.zeros(born)))
                    self.life_harvest = np.concatenate((self.life_harvest, np.zeros(born)))
                    self.life_distance = np.concatenate((self.life_distance, np.zeros(born)))
                    self.peak_energy = np.concatenate((self.peak_energy, np.full(born, cfg.newborn_energy)))
                    self.offspring_count = np.concatenate((self.offspring_count, np.zeros(born, dtype=np.int32)))
                    self.birth_tick = np.concatenate((self.birth_tick, np.full(born, self.tick, dtype=np.int64)))
                    self.first_meal_tick = np.concatenate((self.first_meal_tick, np.full(born, -1, dtype=np.int64)))
                    self.first_offspring_tick = np.concatenate((self.first_offspring_tick, np.full(born, -1, dtype=np.int64)))
                    self.total_births += born
                    self.last_events.extend({"tick": self.tick, "kind": "birth", "id": int(id_),
                                             "parent_id": int(parent), "generation": int(gen),
                                             "x": float(cx), "y": float(cy)}
                                            for id_, parent, gen, cx, cy in
                                            zip(newborn_ids, parent_ids, child_generation, child_x, child_y))

        self.food += cfg.growth_rate * (self.capacity - self.food)
        if self.last_events:
            self.observation_log.extend(self.last_events)
            del self.observation_log[:-3500]
        if self.watch_traces and self.tick % 2 == 0:
            index = {int(id_): j for j, id_ in enumerate(self.ids)}
            for tracked_id, trace in self.watch_traces.items():
                j = index.get(tracked_id)
                if j is not None:
                    trace.append({"tick": int(self.tick), "x": float(self.x[j]),
                                  "y": float(self.y[j]), "energy": float(self.energy[j]),
                                  "intake": float(self.last_intake[j])})
                    del trace[:-240]
        self._notice_ecological_milestones()
        if self.tick % 8 == 0:
            self.population_history.append((self.tick, self.population, self.last_mean_intake))
            del self.population_history[:-1500]
        return self.stats(born, died, detailed=False)

    def _reproduce_biological(self) -> int:
        """Run ecology-driven birth mechanics (see reproduction.py)."""
        return reproduce_biological(self)

    def _notice_ecological_milestones(self) -> None:
        """Record verifiable one-time facts, never invented personalities or events."""
        observed = {event['tag'] for event in self.notable_events}
        facts = (
            ('first_birth', self.total_births >= 1, 'First observed offspring born'),
            ('five_generations', bool(self.population and np.max(self.generation) >= 5),
             'A fifth-generation organism is alive'),
            ('starvation', self.death_causes.get('starvation', 0) > 0,
             'First observed starvation death'),
            ('old_age', self.death_causes.get('age', 0) > 0,
             'First observed age-related death'),
            ('population_cap', self.population >= self.config.max_population,
             'Population reached the configured habitat cap'),
            ('extinction', self.population == 0 and self.total_deaths > 0,
             'The population went extinct'),
            ('first_genetic_mutation', self.config.genetics_enabled and self.total_body_mutations > 0,
             'A newborn inherited a mutated biological allele'),
            ('first_gene_copy_change', self.config.genetics_enabled and self.total_copy_mutations > 0,
             'A gene duplication or deletion occurred'),
            ('first_two_parent_birth', self.config.genetics_enabled and self.sexual_births > 0,
             'First locally paired two-parent offspring born'),
            ('first_regulatory_gene', self.regulatory_new_genes > 0,
             'A novel regulatory gene instruction was inherited'),
            ('first_chromosomal_rearrangement', self.regulatory_new_chromosomes > 0,
             'An organism inherited a newly formed chromosome'),
        )
        for tag, condition, message in facts:
            if condition and tag not in observed:
                self.notable_events.append({'tag': tag, 'tick': int(self.tick),
                                            'message': message})
                observed.add(tag)

    def _retain(self, mask: np.ndarray) -> None:
        for field in LIVE_ARRAY_FIELDS:
            setattr(self, field, getattr(self, field)[mask])

    def enable_disk_archive(self, path: str | Path) -> None:
        """Spill dead specimens into SQLite; never change the living ecosystem.

        An existing populated database is refused to prevent quietly mixing
        histories from different worlds. Portable checkpoints include the DB.
        """
        if isinstance(self.life_archive, DiskArchive):
            raise ValueError("This world already has an on-disk archive")
        archive = DiskArchive(path)
        if len(archive):
            archive.close()
            raise ValueError("Archive already contains specimens; use a fresh path")
        for id_, record in self.life_archive.items():
            archive[id_] = record
        archive.flush()
        self.life_archive = archive

    def watch(self, id_: int) -> bool:
        """Begin persistent movement/energy sampling without modifying the ecology."""
        detail = self.specimen(id_)
        if detail is None:
            return False
        if id_ not in self.watch_traces:
            if len(self.watch_traces) >= 12:
                del self.watch_traces[next(iter(self.watch_traces))]
            self.watch_traces[id_] = []
        if detail['alive'] and not self.watch_traces[id_]:
            self.watch_traces[id_].append({"tick": int(self.tick),
                "x": float(detail['x']), "y": float(detail['y']),
                "energy": float(detail['final_energy']), "intake": 0.0})
        return True

    def specimen(self, id_: int) -> dict[str, Any] | None:
        """Inspectable lifetime for a living or dead individual, across saves."""
        matches = np.flatnonzero(self.ids == id_)
        if len(matches):
            j = int(matches[0])
            return {
                "id": int(id_), "alive": True, "parent_id": int(self.parents[j]),
                "parent2_id": int(self.second_parents[j]),
                "body_dna": self.body_dna[j].tolist(),
                "gene_copies": self.gene_copies[j].tolist(),
                "regulatory_genes": describe(self.regulatory_programs[j],
                                             self.regulatory_lengths[j]),
                "mutation_count": int(self.mutation_count[j]),
                "generation": int(self.generation[j]), "born_tick": int(self.birth_tick[j]),
                "died_tick": None, "age": int(self.age[j]), "cause": None,
                "x": float(self.x[j]), "y": float(self.y[j]),
                "final_energy": float(self.energy[j]), "peak_energy": float(self.peak_energy[j]),
                "food_harvested": float(self.life_harvest[j]),
                "distance_traveled": float(self.life_distance[j]),
                "offspring": int(self.offspring_count[j]),
                "first_meal_tick": int(self.first_meal_tick[j]),
                "first_offspring_tick": int(self.first_offspring_tick[j]),
                "genome": self.genomes[j].tolist(),
            }
        record = self.life_archive.get(int(id_))
        return {**record, "alive": False} if record is not None else None

    def ancestry(self, id_: int, *, limit: int = 6) -> list[int]:
        """Direct ancestor IDs, nearest parent first, with loop defense."""
        if limit < 0:
            raise ValueError("limit must be nonnegative")
        ancestors: list[int] = []
        seen = {int(id_)}
        current = int(id_)
        for _ in range(limit):
            detail = self.specimen(current)
            if detail is None or detail['parent_id'] < 0:
                break
            parent = int(detail['parent_id'])
            if parent in seen:
                break
            seen.add(parent)
            ancestors.append(parent)
            current = parent
        return ancestors

    def relatives(self, id_: int, *, limit: int = 32, offset: int = 0) -> list[int]:
        """Paged direct offspring in ID/birth order, without silently truncating.

        Negative offsets select from the end, useful for finding the latest child.
        """
        if limit < 1:
            raise ValueError("limit must be positive")
        living = self.ids[(self.parents == id_) | (self.second_parents == id_)].astype(int).tolist()
        if isinstance(self.life_archive, DiskArchive):
            # Fetch only as many candidates as needed for the requested page,
            # not the entire long-run database. The first K merged IDs can
            # only come from the first K of each sorted sequence.
            count = abs(offset) + limit if offset < 0 else offset + limit
            dead = self.life_archive.children_ids(int(id_), limit=count, offset=0,
                                                  newest_first=offset < 0)
            if offset < 0:
                combined = sorted(dead + sorted(living, reverse=True)[:count])
                return combined[max(0, len(combined) + offset):][:limit]
            return sorted(dead + living[:count])[offset:offset + limit]
        dead = [k for k, data in self.life_archive.items()
                if data["parent_id"] == id_ or data.get("parent2_id", -1) == id_]
        children = sorted(dead + living)
        start = max(0, len(children) + offset) if offset < 0 else offset
        return children[start:start + limit]

    def stats(self, births: int = 0, deaths: int = 0, *, detailed: bool = True) -> dict[str, Any]:
        n = self.population
        return {"tick": self.tick, "population": n, "births": births, "deaths": deaths,
                "cumulative_births": self.total_births, "cumulative_deaths": self.total_deaths,
                "max_generation": int(np.max(self.generation)) if n else 0,
                "mean_generation": float(np.mean(self.generation)) if n else 0.0,
                "mean_energy": float(np.mean(self.energy)) if n else 0.0,
                "mean_age": float(np.mean(self.age)) if n else 0.0,
                "mean_intake": self.last_mean_intake,
                "mean_speed": self.last_mean_speed,
                "directionality": self.last_directionality,
                "wall_hits": self.last_wall_hits, "cumulative_wall_hits": self.cumulative_wall_hits,
                "patch_moves": self.patch_moves,
                "resource_stock": float(np.sum(self.food)),
                "genetic_diversity": float(np.mean(np.std(self.genomes.reshape(n, -1), axis=0))) if n > 1 and detailed else 0.0,
                "cumulative_harvest": self.total_harvest,
                "genetics_enabled": int(self.config.genetics_enabled),
                "mean_body_size": float(np.mean(self.biology()["size"])) if n else 0.0,
                "mean_genome_loci": float(16 + np.mean(np.sum(self.gene_copies, axis=1))) if n else 0.0,
                "total_biology_mutations": self.total_body_mutations,
                "total_structural_mutations": self.total_copy_mutations,
                "total_sexual_births": self.sexual_births,
                "regulation_enabled": int(self.config.regulation_enabled),
                "mean_regulatory_genes": float(np.mean(self.regulatory_lengths)) if n else 0.,
                "regulatory_innovations": self.regulatory_new_genes,
                "regulatory_new_chromosomes": self.regulatory_new_chromosomes}

    def save(self, path: str | Path) -> None:
        """Versioned, deterministic checkpoint; atomic replacement for filesystem paths.

        File-like objects remain supported for in-memory paired-world comparison.
        """
        validate_world_state(self, neural_shape=GENES)
        state = {"schema_version": SCHEMA_VERSION,
                 "seed": self.seed, "tick": self.tick, "next_id": self.next_id,
                 "total_births": self.total_births, "total_deaths": self.total_deaths,
                 "total_harvest": self.total_harvest, "death_causes": self.death_causes,
                 "total_body_mutations": self.total_body_mutations,
                 "total_copy_mutations": self.total_copy_mutations,
                 "sexual_births": self.sexual_births,
                 "next_gene_innovation": self.next_gene_innovation,
                 "regulatory_mutations": self.regulatory_mutations,
                 "regulatory_new_genes": self.regulatory_new_genes,
                 "regulatory_new_chromosomes": self.regulatory_new_chromosomes,
                 "last_mean_intake": self.last_mean_intake, "last_total_intake": self.last_total_intake,
                 "last_mean_speed": self.last_mean_speed,
                 "last_directionality": self.last_directionality,
                 "last_wall_hits": self.last_wall_hits,
                 "cumulative_wall_hits": self.cumulative_wall_hits,
                 "patch_moves": self.patch_moves,
                 "manual_interventions": self.manual_interventions,
                 "life_archive": ({} if isinstance(self.life_archive, DiskArchive)
                                  else self.life_archive),
                 "disk_archive": isinstance(self.life_archive, DiskArchive),
                 "observation_log": self.observation_log,
                 "notable_events": self.notable_events,
                 "population_history": self.population_history,
                 "watch_traces": self.watch_traces,
                 "config": asdict(self.config), "rng_state": self.rng.bit_generator.state}
        arrays = {name: getattr(self, name) for name in SAVED_ARRAY_FIELDS}
        if isinstance(self.life_archive, DiskArchive):
            arrays["archive_database"] = np.frombuffer(self.life_archive.snapshot_bytes(),
                                                        dtype=np.uint8)
        if hasattr(path, "write"):
            np.savez_compressed(path, state=json.dumps(state), **arrays)
            return
        target = Path(path)
        if not str(target).endswith(".npz"):
            target = Path(str(target) + ".npz")  # preserves NumPy's historical behavior
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w+b", prefix=f".{target.name}.", suffix=".tmp",
                dir=target.parent, delete=False
            ) as handle:
                temporary = Path(handle.name)
                np.savez_compressed(handle, state=json.dumps(state), **arrays)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path: str | Path) -> World:
        with np.load(path, allow_pickle=False) as data:
            state = json.loads(str(data["state"]))
            version = int(state.get("schema_version", 1))
            if version < 1 or version > SCHEMA_VERSION:
                raise ValueError(f"Unsupported checkpoint schema version: {version}")
            missing = set(LEGACY_REQUIRED_FIELDS) - set(data.files)
            if missing:
                raise ValueError(f"Checkpoint missing required arrays: {sorted(missing)}")
            world = cls(Config(**state["config"]), seed=state["seed"])
            for name in LEGACY_REQUIRED_FIELDS:
                setattr(world, name, data[name].copy())
            # v0.9 and earlier files have no biology arrays and remain legacy worlds.
            if "body_dna" not in data and world.config.genetics_enabled:
                raise ValueError("Genetics-enabled checkpoint is missing DNA; refusing silent data loss")
            world.body_dna = (data["body_dna"].copy() if "body_dna" in data
                              else np.zeros((world.population, len(LOCI))))
            world.gene_copies = (data["gene_copies"].copy() if "gene_copies" in data
                                 else np.ones((world.population, len(LOCI)), dtype=np.int8))
            if bool(state.get("disk_archive", False)) and "archive_database" not in data:
                raise ValueError("Checkpoint missing its embedded SQLite history")
            archive_blob = (data["archive_database"].tobytes()
                            if state.get("disk_archive", False) else None)
            if world.config.regulation_enabled and ("regulatory_programs" not in data or
                                                    "regulatory_lengths" not in data):
                raise ValueError("Regulation-enabled checkpoint missing regulatory DNA")
            world.regulatory_programs = (data["regulatory_programs"].copy()
                                         if "regulatory_programs" in data else empty_programs(world.population)[0])
            world.regulatory_lengths = (data["regulatory_lengths"].copy()
                                        if "regulatory_lengths" in data else empty_programs(world.population)[1])
            world.second_parents = (data["second_parents"].copy() if "second_parents" in data
                                    else np.full(world.population, -1, dtype=np.int64))
            world.mutation_count = (data["mutation_count"].copy() if "mutation_count" in data
                                    else np.zeros(world.population, dtype=np.int32))
            world.last_intake = data["last_intake"].copy() if "last_intake" in data else np.zeros(world.population)
            defaults = {
                "life_harvest": np.zeros(world.population),
                "life_distance": np.zeros(world.population),
                "peak_energy": world.energy.copy(),
                "offspring_count": np.zeros(world.population, dtype=np.int32),
                "birth_tick": (int(state["tick"]) - world.age).astype(np.int64),
                "first_meal_tick": np.full(world.population, -1, dtype=np.int64),
                "first_offspring_tick": np.full(world.population, -1, dtype=np.int64),
            }
            for name, default in defaults.items():
                setattr(world, name, data[name].copy() if name in data else default)
        for name in ("tick", "next_id", "total_births", "total_deaths", "total_harvest",
                     "death_causes", "last_mean_intake", "last_total_intake", "last_mean_speed", "last_directionality",
                     "last_wall_hits", "cumulative_wall_hits", "patch_moves"):
            # Older v0.1/v0.2 checkpoints predate the geometry observables.
            setattr(world, name, state.get(name, 0))
        world.total_body_mutations = int(state.get("total_body_mutations", 0))
        world.total_copy_mutations = int(state.get("total_copy_mutations", 0))
        world.sexual_births = int(state.get("sexual_births", 0))
        world.next_gene_innovation = int(state.get("next_gene_innovation", 1))
        world.regulatory_mutations = int(state.get("regulatory_mutations", 0))
        world.regulatory_new_genes = int(state.get("regulatory_new_genes", 0))
        world.regulatory_new_chromosomes = int(state.get("regulatory_new_chromosomes", 0))
        world.manual_interventions = state.get("manual_interventions", [])
        world.life_archive = (DiskArchive.from_bytes(archive_blob) if archive_blob is not None
                              else {int(k): v for k, v in state.get("life_archive", {}).items()})
        world.observation_log = state.get("observation_log", [])
        world.notable_events = state.get("notable_events", [])
        world.population_history = [tuple(t) for t in state.get("population_history", [])]
        world.watch_traces = {int(k): v for k, v in state.get("watch_traces", {}).items()}
        if not world.population_history:
            world.population_history = [(world.tick, world.population, world.last_mean_intake)]
        world.rng.bit_generator.state = state["rng_state"]
        if not isinstance(world.death_causes, dict):
            world.death_causes = {"starvation": 0, "age": 0}
        world.death_causes.setdefault("starvation", 0)
        world.death_causes.setdefault("age", 0)
        validate_world_state(world, neural_shape=GENES)
        return world
