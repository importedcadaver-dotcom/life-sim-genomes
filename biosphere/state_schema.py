"""Save schema and living-array consistency contracts.

Keep every organism-aligned vector in LIVE_ARRAY_FIELDS. These names are used by
retain/save and checked after load, preventing future genetics fields from
remaining attached to the wrong organism after a death.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from .genetics import LOCI
from .regulatory import MAX_GENES, FIELD_COUNT, validate_programs

if TYPE_CHECKING:
    from .simulation import World

SCHEMA_VERSION = 3
LIVE_ARRAY_FIELDS = (
    "x", "y", "angle", "energy", "age", "ids", "parents",
    "second_parents", "generation", "genomes", "body_dna",
    "gene_copies", "mutation_count", "last_intake", "life_harvest",
    "life_distance", "peak_energy", "offspring_count", "birth_tick",
    "first_meal_tick", "first_offspring_tick", "regulatory_programs", "regulatory_lengths",
)
SAVED_ARRAY_FIELDS = ("capacity", "food", *LIVE_ARRAY_FIELDS)
LEGACY_REQUIRED_FIELDS = (
    "capacity", "food", "x", "y", "angle", "energy", "age",
    "ids", "parents", "generation", "genomes",
)

def validate_world_state(world: World, *, neural_shape: tuple[int, int] = (2, 8)) -> None:
    """Check invariants at save/load boundaries, not on every simulation tick."""
    n = world.population
    cfg = world.config
    if n > cfg.max_population or n < 0:
        raise ValueError("Checkpoint population exceeds configured capacity")
    for name in LIVE_ARRAY_FIELDS:
        value = getattr(world, name)
        if not isinstance(value, np.ndarray) or value.ndim == 0 or value.shape[0] != n:
            raise ValueError(f"Checkpoint organism array {name} is not population-aligned")
        if not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)):
            raise ValueError(f"Checkpoint organism array {name} contains nonfinite/invalid values")
    if world.genomes.shape != (n, *neural_shape):
        raise ValueError("Checkpoint neural genome shape is incompatible with current engine")
    if world.body_dna.shape != (n, len(LOCI)) or world.gene_copies.shape != (n, len(LOCI)):
        raise ValueError("Checkpoint biological genome shape is incompatible with current engine")
    if np.any((world.gene_copies < 0) | (world.gene_copies > 3)):
        raise ValueError("Checkpoint biological gene copy numbers must be within [0, 3]")
    validate_programs(world.regulatory_programs, world.regulatory_lengths)
    if (world.config.regulation_enabled and n and
            world.next_gene_innovation <= np.max(world.regulatory_programs[:, :, 6])):
        raise ValueError("Checkpoint next regulatory innovation ID overlaps existing genes")
    if len(np.unique(world.ids)) != n or np.any(world.ids < 0):
        raise ValueError("Checkpoint living organism IDs are duplicated or negative")
    if n and world.next_id <= int(np.max(world.ids)):
        raise ValueError("Checkpoint next_id must exceed all living organism IDs")
    for name in ("food", "capacity"):
        value = getattr(world, name)
        if value.shape != (cfg.height, cfg.width) or not np.all(np.isfinite(value)):
            raise ValueError(f"Checkpoint resource array {name} has invalid shape or values")
    if np.any(world.capacity < 0) or np.any(world.food < -1e-8) or np.any(world.food > world.capacity + 1e-8):
        raise ValueError("Checkpoint resources must remain between zero and capacity")
