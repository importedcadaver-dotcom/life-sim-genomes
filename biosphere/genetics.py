"""Inheritable digital biology, deliberately distinct from molecular DNA.

The genome has 16 neural weights and 12 named, continuously valued biology loci.
Each biological locus has 0-3 copies. Copy loss/duplication changes expressed
'dosage' and therefore genome size; it does not create a new kind of locus.
No manually assigned fitness score is used: death and reproduction in World
supply differential success through resource competition.
"""
from __future__ import annotations

from typing import NamedTuple

import numpy as np

LOCI = (
    "body_size", "metabolic_efficiency", "digestion", "propulsion",
    "turning", "sensor_range", "sensor_gain", "longevity",
    "maturation", "investment", "pigment", "spots",
)
INDEX = {name: k for k, name in enumerate(LOCI)}
LOCUS_COUNT = len(LOCI)


class GeneticsBatch(NamedTuple):
    dna: np.ndarray
    copies: np.ndarray
    point_changes: np.ndarray
    copy_changes: np.ndarray


def founder_dna(rng: np.random.Generator, population: int) -> GeneticsBatch:
    if population < 0:
        raise ValueError("population must be nonnegative")
    # Real founder variation in the new mode; no hard-coded survival traits.
    dna = rng.normal(0, .62, (population, LOCUS_COUNT))
    return GeneticsBatch(np.clip(dna, -2.5, 2.5),
                         np.ones((population, LOCUS_COUNT), dtype=np.int8),
                         np.zeros(population, dtype=np.int32),
                         np.zeros(population, dtype=np.int32))


def mutate(dna: np.ndarray, copies: np.ndarray, rng: np.random.Generator,
           *, point_rate: float = .045, strength: float = .22,
           copy_rate: float = .008) -> GeneticsBatch:
    """Copy errors and structural duplication/loss; never mutate parents in place."""
    if not 0 <= point_rate <= 1 or not 0 <= copy_rate <= 1 or strength < 0:
        raise ValueError("Invalid mutation parameters")
    genome = np.asarray(dna, dtype=float).copy()
    dosage = np.asarray(copies, dtype=np.int8).copy()
    if genome.ndim != 2 or genome.shape[1] != LOCUS_COUNT or dosage.shape != genome.shape:
        raise ValueError("Invalid biological DNA/copy-number shape")
    point_mask = rng.random(genome.shape) < point_rate
    genome += point_mask * rng.normal(0, strength, genome.shape)
    np.clip(genome, -2.5, 2.5, out=genome)
    structural_mask = rng.random(genome.shape) < copy_rate
    signed = rng.choice(np.array([-1, 1], dtype=np.int8), size=genome.shape)
    dosage = np.clip(dosage + structural_mask * signed, 0, 3).astype(np.int8)
    changed = structural_mask & (dosage != copies)
    return GeneticsBatch(genome, dosage, point_mask.sum(axis=1).astype(np.int32),
                         changed.sum(axis=1).astype(np.int32))


def recombine(dna_a: np.ndarray, copy_a: np.ndarray,
              dna_b: np.ndarray, copy_b: np.ndarray,
              rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Uniform per-locus inheritance; both parent genomes stay unchanged."""
    if dna_a.shape != dna_b.shape or copy_a.shape != copy_b.shape or dna_a.shape != copy_a.shape:
        raise ValueError("Parent genotype shapes differ")
    mask = rng.random(dna_a.shape) < .5
    return np.where(mask, dna_a, dna_b).copy(), np.where(mask, copy_a, copy_b).copy()


def traits(dna: np.ndarray, copies: np.ndarray) -> dict[str, np.ndarray]:
    """Vectorized genotype-to-phenotype map; every fitness-relevant locus used.

    Factors are relative to the old ecology. More efficient guts and larger
    bodies are not free: they increase maintenance or movement costs.
    """
    if dna.ndim != 2 or dna.shape[1] != LOCUS_COUNT or dna.shape != copies.shape:
        raise ValueError("Invalid DNA/copy-number shapes")
    z = np.clip(dna * copies, -2.5, 2.5)
    def q(name: str) -> np.ndarray:
        return z[:, INDEX[name]]
    size = np.exp(.22 * q("body_size"))
    digestion = np.exp(.24 * q("digestion"))
    eyes = np.exp(.23 * q("sensor_range"))
    return {
        "size": size,
        "maintenance": np.exp(.26 * q("body_size") - .31 * q("metabolic_efficiency") +
                              .13 * q("digestion") + .10 * q("sensor_range") +
                              .09 * q("longevity")),
        "food_gain": digestion,
        "bite": np.exp(.20 * q("body_size")),
        "propulsion": np.exp(.23 * q("propulsion") - .13 * q("body_size")),
        "agility": np.exp(.24 * q("turning") - .12 * q("body_size")),
        "sensor_range": eyes,
        "sensor_gain": np.exp(.29 * q("sensor_gain")),
        "longevity": np.exp(.27 * q("longevity")),
        "maturation": np.exp(.30 * q("maturation")),
        "investment": np.exp(.20 * q("investment")),
        "pigment": q("pigment"),
        "spots": q("spots"),
    }


def neutral_traits(count: int) -> dict[str, np.ndarray]:
    """Exact old ecology when opt-in digital biology is disabled."""
    d = np.zeros((count, LOCUS_COUNT), dtype=np.float64)
    c = np.ones((count, LOCUS_COUNT), dtype=np.int8)
    return traits(d, c)


def phenotype_summary(dna: np.ndarray, copies: np.ndarray) -> dict[str, float]:
    result = traits(np.asarray(dna, dtype=float).reshape(1, -1),
                    np.asarray(copies, dtype=np.int8).reshape(1, -1))
    return {name: float(value[0]) for name, value in result.items()}
