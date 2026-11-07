"""Optional cute observatory features, isolated from evolutionary experiments.

Cheats explicitly mark World.manual_interventions. Mini-games observe a *snapshot*
without consuming World.rng or modifying its ecological state. Comparative
lab runs independent deterministic clones and never edits the observed world.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from io import BytesIO
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from .simulation import World
from .genetics import mutate, INDEX
from .regulatory import inherit_programs

PASTELS = ((255, 162, 202), (249, 188, 222), (195, 162, 241),
           (255, 198, 150), (165, 215, 205), (250, 222, 167))


def creature_color(genome: np.ndarray, body_dna: np.ndarray | None = None,
                   copies: np.ndarray | None = None) -> tuple[int, int, int]:
    """Heritable pigment: biology-locus pigment or legacy controller color."""
    if body_dna is not None:
        dosage = float(np.asarray(copies)[INDEX["pigment"]]) if copies is not None else 1.0
        g = float(np.asarray(body_dna)[INDEX["pigment"]]) * dosage
        index = int(np.floor(np.clip((g + 2.5) / 5.0, 0, .9999) * len(PASTELS)))
        return PASTELS[index]
    g = float(np.asarray(genome)[0, 0])
    return PASTELS[int(np.floor((g + 5) / 10 * len(PASTELS))) % len(PASTELS)]


def cheat(world: World, action: str, selected: int | None = None) -> str:
    """Explicitly non-scientific, saved interventions; never use in experiments."""
    valid = {"feast", "energy", "babies", "immortal", "gene_spark"}
    if action not in valid:
        raise ValueError("Unknown cheat")
    if action == "feast":
        amount = float(np.sum(world.capacity - world.food))
        world.food = world.capacity.copy()
        message = f"Candy rain! Restored {amount:.0f} food units"
    elif action == "energy":
        idx = np.flatnonzero(world.ids == selected) if selected is not None else np.empty(0, int)
        if not len(idx):
            return "Select a living creature to give a super snack"
        j = int(idx[0])
        world.energy[j] += 40.0
        world.peak_energy[j] = max(world.peak_energy[j], world.energy[j])
        message = f"Creature #{selected} ate an energy cupcake (+40)"
    elif action == "gene_spark":
        idx = np.flatnonzero(world.ids == selected) if selected is not None else np.empty(0, int)
        if not len(idx):
            return "Select a living creature to edit its DNA"
        if not world.config.genetics_enabled:
            return "DNA Spark requires a genetics-enabled ecosystem"
        j = int(idx[0])
        batch = mutate(world.body_dna[j:j + 1], world.gene_copies[j:j + 1], world.rng,
                       point_rate=.80, strength=.70, copy_rate=.35)
        world.body_dna[j] = batch.dna[0]
        world.gene_copies[j] = batch.copies[0]
        change = int(batch.point_changes[0] + batch.copy_changes[0])
        world.mutation_count[j] += change
        world.total_body_mutations += int(batch.point_changes[0])
        world.total_copy_mutations += int(batch.copy_changes[0])
        if world.config.regulation_enabled:
            program, count, world.next_gene_innovation, new = inherit_programs(
                world.regulatory_programs[j], world.regulatory_lengths[j], None, None,
                world.rng, world.next_gene_innovation, mutate_enabled=True,
                point_rate=.8, structural_rate=1.)
            world.regulatory_programs[j] = program
            world.regulatory_lengths[j] = count
            world.regulatory_mutations += sum(new.values())
            world.regulatory_new_genes += new['insertions'] + new['duplications']
            world.regulatory_new_chromosomes += new['chromosome_births']
            world.mutation_count[j] += sum(new.values())
            change += sum(new.values())
        message = f"DNA Spark: #{selected} acquired {change} artificial genetic changes"
    elif action == "immortal":
        world.config = replace(world.config, lifespan=1_000_000,
                               metabolism=0.0, move_cost=0.0)
        message = "Cozy mode: aging and movement metabolism disabled"
    else:
        idx = np.flatnonzero(world.ids == selected) if selected is not None else np.empty(0, int)
        if not len(idx):
            return "Select a living creature to make baby copies"
        count = min(8, world.config.max_population - world.population)
        if count <= 0:
            return "Habitat full: no room for baby copies"
        source = int(idx[0])
        offspring = np.arange(world.next_id, world.next_id + count, dtype=np.int64)
        world.next_id += count
        old_id = int(world.ids[source])
        old_gen = int(world.generation[source])
        new_x = world.x[source] + np.linspace(-1.4, 1.4, count)
        new_y = world.y[source] + np.linspace(1.2, -1.2, count)
        if world.config.boundary_mode == "wrap":
            new_x, new_y = new_x % world.config.width, new_y % world.config.height
        else:
            new_x = world._reflect_coordinate(new_x, world.config.width)
            new_y = world._reflect_coordinate(new_y, world.config.height)
        for name, values in (
            ("x", new_x), ("y", new_y),
            ("angle", np.full(count, world.angle[source])),
            ("energy", np.full(count, world.config.newborn_energy)),
            ("age", np.zeros(count, dtype=np.int32)), ("ids", offspring),
            ("parents", np.full(count, old_id, dtype=np.int64)),
            ("second_parents", np.full(count, -1, dtype=np.int64)),
            ("mutation_count", np.zeros(count, dtype=np.int32)),
            ("generation", np.full(count, old_gen + 1, dtype=np.int32)),
            ("last_intake", np.zeros(count)), ("life_harvest", np.zeros(count)),
            ("life_distance", np.zeros(count)),
            ("peak_energy", np.full(count, world.config.newborn_energy)),
            ("offspring_count", np.zeros(count, dtype=np.int32)),
            ("birth_tick", np.full(count, world.tick, dtype=np.int64)),
            ("first_meal_tick", np.full(count, -1, dtype=np.int64)),
            ("first_offspring_tick", np.full(count, -1, dtype=np.int64)),
        ):
            setattr(world, name, np.concatenate([getattr(world, name), values]))
        world.genomes = np.concatenate([world.genomes, np.repeat(
            world.genomes[source:source + 1], count, axis=0)])
        world.body_dna = np.concatenate([world.body_dna, np.repeat(
            world.body_dna[source:source + 1], count, axis=0)])
        world.gene_copies = np.concatenate([world.gene_copies, np.repeat(
            world.gene_copies[source:source + 1], count, axis=0)])
        world.regulatory_programs = np.concatenate([world.regulatory_programs, np.repeat(
            world.regulatory_programs[source:source + 1], count, axis=0)])
        world.regulatory_lengths = np.concatenate([world.regulatory_lengths, np.repeat(
            world.regulatory_lengths[source:source + 1], count, axis=0)])
        world.offspring_count[source] += count
        if world.first_offspring_tick[source] < 0:
            world.first_offspring_tick[source] = world.tick
        world.total_births += count
        events = [{"tick": world.tick, "kind": "birth", "id": int(id_),
                   "parent_id": old_id, "generation": old_gen + 1,
                   "x": float(x), "y": float(y), "origin": "cheat"}
                  for id_, x, y in zip(offspring, new_x, new_y)]
        world.observation_log.extend(events)
        world.last_events.extend(events)
        message = f"{count} baby clones appeared · explicitly spawned by a cheat"
    world.manual_interventions.append({"tick": int(world.tick), "kind": "cheat",
                                       "action": action, "selected_id": selected})
    return message


@dataclass
class Challenge:
    kind: str
    title: str
    prompt: str
    labels: list[str]
    values: list[float]
    chosen: int | None = None
    award: int = 0

    @property
    def winner(self) -> int:
        return int(np.argmax(self.values))

    def answer(self, index: int) -> bool:
        if not 0 <= index < len(self.values):
            raise ValueError("Invalid answer")
        if self.chosen is not None:
            return bool(np.isclose(self.values[self.chosen], max(self.values)))
        self.chosen = index
        correct = bool(np.isclose(self.values[index], max(self.values), rtol=1e-7, atol=1e-7))
        self.award = 1 if correct else 0
        return correct


@dataclass
class MiniGames:
    round: int = 0
    correct: int = 0
    attempts: int = 0
    challenge: Challenge | None = None

    def create(self, world: World, kind: str) -> Challenge:
        """No mutation of world, no consumption of world.rng."""
        if kind not in ("berries", "speed", "genes"):
            raise ValueError("Unknown mini-game")
        self.round += 1
        rng = np.random.default_rng([world.seed & 0xFFFFFFFF, world.tick, self.round,
                                     17 if kind == "berries" else 29])
        if kind == "berries":
            cells = []
            for _ in range(18):
                x, y = int(rng.integers(world.config.width)), int(rng.integers(world.config.height))
                if all((x - px) ** 2 + (y - py) ** 2 > 36 for px, py in cells):
                    cells.append((x, y))
                if len(cells) == 3:
                    break
            while len(cells) < 3:
                cells.append((int(rng.integers(world.config.width)),
                              int(rng.integers(world.config.height))))
            values = [float(world.food[y, x]) for x, y in cells]
            labels = [f"Patch {k + 1}  ({x},{y})" for k, (x, y) in enumerate(cells)]
            challenge = Challenge("berries", "BERRY HUNT",
                                  "Which illustrated patch has the most food?",
                                  labels, values)
        else:
            if world.population < 3:
                raise ValueError("Need three living organisms for the creature detective games")
            indices = rng.choice(world.population, 3, replace=False)
            if kind == "genes":
                if not world.config.regulation_enabled:
                    raise ValueError("Genome Detective needs a gene-regulation world")
                labels = [f"Creature #{int(world.ids[j])}  ·  G{int(world.generation[j])}"
                          for j in indices]
                challenge = Challenge("genes", "GENOME DETECTIVE",
                                      "Which creature has the most regulatory genes?",
                                      labels, [float(world.regulatory_lengths[j]) for j in indices])
            else:
                _, speeds, _ = world.controls()
                labels = [f"Creature #{int(world.ids[j])}  ·  G{int(world.generation[j])}"
                          for j in indices]
                challenge = Challenge("speed", "SPEED DETECTIVE",
                                      "Which creature has the highest current motor speed?",
                                      labels, [float(speeds[j]) for j in indices])
        self.challenge = challenge
        return challenge

    def answer(self, index: int) -> bool:
        if self.challenge is None:
            raise ValueError("No challenge")
        old = self.challenge.chosen
        correct = self.challenge.answer(index)
        if old is None:
            self.attempts += 1
            self.correct += int(correct)
        return correct


@dataclass
class Chronicle:
    bookmarks: list[int] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    traces: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    last_saved_tick: int = -1

    def toggle(self, world: World, specimen_id: int) -> bool:
        if world.specimen(specimen_id) is None:
            return False
        if specimen_id in self.bookmarks:
            self.bookmarks.remove(specimen_id)
            return False
        if len(self.bookmarks) >= 16:
            self.bookmarks.pop(0)
        self.bookmarks.append(specimen_id)
        world.watch(specimen_id)
        return True

    def observe(self, world: World) -> None:
        # Compact memory cache for UI; full session stream is exported on save.
        self.events.extend(dict(e) for e in world.last_events)
        self.events = self.events[-8000:]
        if world.tick % 3 != 0:
            return
        positions = {int(id_): j for j, id_ in enumerate(world.ids)}
        for specimen_id in self.bookmarks:
            idx = positions.get(specimen_id)
            if idx is None:
                continue
            key = str(specimen_id)
            track = self.traces.setdefault(key, [])
            track.append({"tick": int(world.tick), "x": float(world.x[idx]),
                          "y": float(world.y[idx]), "energy": float(world.energy[idx])})
            # Preserve a human-browsable recent-life replay, bounded for long runs.
            del track[:-2000]

    def save(self, path: str | Path, games: MiniGames, *, checkpoint: str | Path | None = None) -> None:
        data = {"format": "accidental-biosphere-v0.9-observer", "bookmarks": self.bookmarks,
                "events": self.events, "traces": self.traces,
                "games": {"round": games.round, "correct": games.correct,
                          "attempts": games.attempts},
                "note": "Observational annotations, not evolutionary evidence. "
                        "Recent event cache is capped at 8000; tracked positions at 2000 per creature."}
        if checkpoint is not None:
            data["checkpoint_sha256"] = hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path, *, checkpoint: str | Path | None = None) -> tuple[Chronicle, MiniGames]:
        state = json.loads(Path(path).read_text(encoding="utf-8"))
        if state.get("format") != "accidental-biosphere-v0.9-observer":
            raise ValueError("Unsupported observer notebook")
        expected = state.get("checkpoint_sha256")
        if expected and checkpoint is not None:
            actual = hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
            if actual != expected:
                raise ValueError("Observer notebook belongs to a different world checkpoint")
        book = cls(bookmarks=[int(x) for x in state.get("bookmarks", [])][:16],
                   events=state.get("events", [])[-8000:], traces=state.get("traces", {}))
        stats = state.get("games", {})
        return book, MiniGames(round=int(stats.get("round", 0)),
                               correct=int(stats.get("correct", 0)),
                               attempts=int(stats.get("attempts", 0)))


LAB_VARIANTS = {"half_growth": "Half food regrowth", "double_cost": "Double movement cost",
                "food_blind": "Disable external food sensors"}


class PairedLab:
    """Two worlds cloned from one identical RNG+state snapshot, main world untouched."""
    def __init__(self, source: World, mode: str = "half_growth"):
        if mode not in LAB_VARIANTS:
            raise ValueError("Unknown lab mode")
        raw = BytesIO()
        source.save(raw)
        raw.seek(0)
        self.control = World.load(raw)
        raw.seek(0)
        self.changed = World.load(raw)
        cfg = self.changed.config
        updates = ({"growth_rate": cfg.growth_rate * .5} if mode == "half_growth" else
                   {"move_cost": cfg.move_cost * 2} if mode == "double_cost" else
                   {"sensor_mode": "food_blind"})
        self.changed.config = replace(cfg, **updates)
        self.mode = mode
        self.start_tick = source.tick
        self.source_intervention_count = len(source.manual_interventions)
        self.steps = 0
        self.initial_births = source.total_births
        self.initial_deaths = source.total_deaths
        self.limit = 100

    @property
    def done(self) -> bool:
        return self.steps >= self.limit or not self.control.population or not self.changed.population

    def advance(self, n: int = 1) -> None:
        for _ in range(max(0, min(n, 12))):
            if self.done:
                break
            self.control.step()
            self.changed.step()
            self.steps += 1

    def report(self) -> dict[str, Any]:
        return {"source_tick": self.start_tick, "mode": self.mode, "steps": self.steps,
                "source_interventions": self.source_intervention_count,
                "scientific_status": "illustrative_only" if self.source_intervention_count else "single_pair_not_replicated",
                "causal_design": "Cloned initial world and RNG, single-factor intervention, no edits to source",
                "control": {"population": self.control.population,
                            "births": self.control.total_births - self.initial_births,
                            "deaths": self.control.total_deaths - self.initial_deaths},
                "variant": {"population": self.changed.population,
                            "births": self.changed.total_births - self.initial_births,
                            "deaths": self.changed.total_deaths - self.initial_deaths}}
