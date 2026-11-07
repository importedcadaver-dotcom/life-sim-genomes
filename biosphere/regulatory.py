"""Safe, heritable, variable-length gene regulatory programs.

A bounded instruction *language*, not user Python and not molecular DNA.
Chromosome membership and gene order are inherited; mutation can add novel
instructions, duplicate and delete genes, and move genes between chromosomes.
The interpreter permits novel *circuits made of supported primitives* but
cannot invent physics, arbitrary organs, or executable instructions.

Representation: ``(population, MAX_GENES, FIELD_COUNT)`` float64, padded by
zeros beyond ``lengths``. Integral fields are validated at save boundaries.
This rectangular encoding permits efficient population compaction and clean
NumPy checkpoints while maintaining variable-length gene sequences.
"""
from __future__ import annotations

import numpy as np

MAX_GENES = 16
FIELD_COUNT = 7
OP, SOURCE, TARGET, WEIGHT, THRESHOLD, CHROM, INNOVATION = range(FIELD_COUNT)
INPUTS = ("constant", "local_food", "energy", "crowding", "age", "food_asymmetry",
          "regulator_a", "regulator_b")
TARGETS = ("maintenance", "digestion", "propulsion", "turning", "sensing",
           "growth", "reproduction", "turn_bias", "speed_bias", "regulator_a",
           "regulator_b")
OPCODES = ("direct", "gate", "inverse", "product", "noncoding")
MAX_CHROMOSOMES = 8
REGULATORS = (9, 10)


def empty_programs(n: int) -> tuple[np.ndarray, np.ndarray]:
    return np.zeros((n, MAX_GENES, FIELD_COUNT), dtype=np.float64), np.zeros(n, dtype=np.int16)


def founder_programs(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray, int]:
    """Make founders with diverse, mostly short sequences. IDs are stable per gene."""
    matrix, lengths = empty_programs(n)
    # Each founder has 2 to 4 regulatory genes, no initial complex design.
    lengths[:] = rng.integers(2, 5, size=n, dtype=np.int16)
    next_innovation = 1
    for i, length in enumerate(lengths):
        for slot in range(int(length)):
            matrix[i, slot] = random_gene(rng, next_innovation, chrom=slot % 2)
            next_innovation += 1
    return matrix, lengths, next_innovation


def random_gene(rng: np.random.Generator, innovation: int, chrom: int = 0) -> np.ndarray:
    return np.array([rng.integers(len(OPCODES)), rng.integers(len(INPUTS)),
                     rng.integers(len(TARGETS)), rng.uniform(-1.2, 1.2),
                     rng.uniform(-.7, .7), chrom, innovation], dtype=np.float64)


def validate_programs(programs: np.ndarray, lengths: np.ndarray) -> None:
    if programs.ndim != 3 or programs.shape[1:] != (MAX_GENES, FIELD_COUNT):
        raise ValueError("Regulatory checkpoint program shape is invalid")
    if lengths.shape != (len(programs),):
        raise ValueError("Regulatory checkpoint lengths do not align")
    if (not np.all(np.isfinite(programs)) or not np.all(np.isfinite(lengths)) or
            np.any(lengths != np.floor(lengths)) or
            np.any(lengths < 0) or np.any(lengths > MAX_GENES)):
        raise ValueError("Regulatory checkpoint contains nonfinite or invalid lengths")
    for row, count in zip(programs, lengths):
        active = row[:int(count)]
        if len(active) == 0:
            continue
        for column, maximum in ((OP, len(OPCODES)), (SOURCE, len(INPUTS)),
                                (TARGET, len(TARGETS)), (CHROM, MAX_CHROMOSOMES)):
            vals = active[:, column]
            if np.any(vals != np.floor(vals)) or np.any(vals < 0) or np.any(vals >= maximum):
                raise ValueError("Regulatory checkpoint has invalid instruction codes")
        ids = active[:, INNOVATION]
        if np.any(ids < 1) or np.any(ids != np.floor(ids)):
            raise ValueError("Regulatory checkpoint has invalid innovation IDs")
        if np.any(np.abs(active[:, WEIGHT]) > 3.0) or np.any(np.abs(active[:, THRESHOLD]) > 2.0):
            raise ValueError("Regulatory checkpoint has invalid weights")
        if not np.array_equal(row[int(count):], np.zeros_like(row[int(count):])):
            raise ValueError("Regulatory checkpoint has nonzero padding")


def evaluate(programs: np.ndarray, lengths: np.ndarray, signals: np.ndarray) -> np.ndarray:
    """Evaluate organisms' regulatory DAG-like sequential programs.

    Each instruction reads an external signal or the current value of one of
    two regulatory registers. Because registers are updated sequentially, gene
    rearrangements change function. No RNG, dynamic execution or side effects.
    Signals are population x 6 (constant, food, energy, crowd, age, asymmetry).
    Output is population x 9 physiological/motor channels, softly bounded.
    """
    n = len(lengths)
    if programs.shape != (n, MAX_GENES, FIELD_COUNT) or signals.shape != (n, 6):
        raise ValueError("Regulation input shape mismatch")
    regs = np.zeros((n, 2), dtype=np.float64)
    outputs = np.zeros((n, 9), dtype=np.float64)
    for slot in range(MAX_GENES):
        active = np.flatnonzero(lengths > slot)
        if not len(active):
            break
        genes = programs[active, slot]
        source = genes[:, SOURCE].astype(np.intp)
        external = source < 6
        values = np.empty(len(active))
        if np.any(external):
            x = active[external]
            values[external] = signals[x, source[external]]
        if np.any(~external):
            x = active[~external]
            values[~external] = regs[x, source[~external] - 6]
        delta = np.clip(values - genes[:, THRESHOLD], -4, 4)
        ops = genes[:, OP].astype(np.intp)
        activity = np.where(ops == 0, np.tanh(delta),
                   np.where(ops == 1, np.maximum(0, np.tanh(delta)),
                   np.where(ops == 2, -np.tanh(delta),
                            np.where(ops == 3, np.tanh(delta) * values,
                                     np.zeros_like(delta)))))
        effect = np.clip(activity * genes[:, WEIGHT], -2., 2.)
        target = genes[:, TARGET].astype(np.intp)
        structural = target >= 9
        if np.any(structural):
            j = active[structural]
            np.add.at(regs, (j, target[structural] - 9), effect[structural])
            np.clip(regs, -3.0, 3.0, out=regs)
        if np.any(~structural):
            j = active[~structural]
            np.add.at(outputs, (j, target[~structural]), effect[~structural])
    return np.clip(outputs, -3., 3.)


def expression_signals(*, food: np.ndarray, energy: np.ndarray,
                       crowd: np.ndarray, maturity: np.ndarray,
                       asymmetry: np.ndarray) -> np.ndarray:
    n = len(food)
    return np.stack([np.ones(n), np.clip(food, 0, 1), np.clip(energy, 0, 2),
                     np.clip(crowd, 0, 1), np.clip(maturity, 0, 2),
                     np.clip(asymmetry, -1, 1)], axis=1)


def inherit_programs(parent_programs: np.ndarray, parent_lengths: np.ndarray,
                     mate_programs: np.ndarray | None, mate_lengths: np.ndarray | None,
                     rng: np.random.Generator, next_innovation: int,
                     *, mutate_enabled: bool, point_rate: float = .08,
                     structural_rate: float = .04) -> tuple[np.ndarray, np.ndarray, int, dict[str, int]]:
    """Chromosome-block crossover, gene innovation and bounded mutations.

    Parents are 1D gene sequences with chromosome membership labels. For each
    chromosome we choose one parent's block (when paired); new instructions
    are born through insertion, not through arbitrary Python generation.
    """
    a = parent_programs[:int(parent_lengths)]
    b = None if mate_programs is None else mate_programs[:int(mate_lengths)]
    genes: list[np.ndarray] = []
    if b is None:
        genes = [g.copy() for g in a]
    else:
        for chrom in range(MAX_CHROMOSOMES):
            donor = a if rng.random() < .5 else b
            genes.extend(g.copy() for g in donor if int(g[CHROM]) == chrom)
    genes = genes[:MAX_GENES]
    counter = {"insertions": 0, "deletions": 0, "duplications": 0,
               "point_changes": 0, "chromosome_changes": 0,
               "chromosome_births": 0}
    if mutate_enabled:
        for gene in genes:
            if rng.random() < point_rate:
                column = int(rng.integers(0, 5))
                if column == OP:
                    gene[OP] = int(rng.integers(len(OPCODES)))
                elif column == SOURCE:
                    gene[SOURCE] = int(rng.integers(len(INPUTS)))
                elif column == TARGET:
                    gene[TARGET] = int(rng.integers(len(TARGETS)))
                elif column == WEIGHT:
                    gene[WEIGHT] = np.clip(gene[WEIGHT] + rng.normal(0, .4), -3, 3)
                else:
                    gene[THRESHOLD] = np.clip(gene[THRESHOLD] + rng.normal(0, .3), -2, 2)
                counter["point_changes"] += 1
        if rng.random() < structural_rate:
            choices = ["insert", "copy", "delete", "chrom", "chrom_copy", "chrom_split"]
            move = choices[int(rng.integers(len(choices)))]
            active_chroms = {int(g[CHROM]) for g in genes}
            available_chroms = sorted(set(range(MAX_CHROMOSOMES)) - active_chroms)
            if move == "delete" and genes:
                del genes[int(rng.integers(len(genes)))]
                counter["deletions"] += 1
            elif move in ("insert", "copy") and len(genes) < MAX_GENES:
                pos = int(rng.integers(len(genes) + 1))
                if move == "insert" or not genes:
                    target_chrom = int(rng.integers(MAX_CHROMOSOMES))
                    fresh = random_gene(rng, next_innovation, chrom=target_chrom)
                    counter["insertions"] += 1
                else:
                    fresh = genes[int(rng.integers(len(genes)))].copy()
                    target_chrom = int(fresh[CHROM])
                    fresh[INNOVATION] = next_innovation
                    counter["duplications"] += 1
                genes.insert(pos, fresh)
                if target_chrom in available_chroms:
                    counter["chromosome_births"] += 1
                next_innovation += 1
            elif move == "chrom" and genes:
                chosen = genes[int(rng.integers(len(genes)))]
                target_chrom = int(rng.integers(MAX_CHROMOSOMES))
                original_chrom = int(chosen[CHROM])
                if target_chrom in available_chroms and sum(
                        int(g[CHROM]) == original_chrom for g in genes) > 1:
                    counter["chromosome_births"] += 1
                chosen[CHROM] = target_chrom
                counter["chromosome_changes"] += 1
            elif move == "chrom_split" and genes and available_chroms:
                # Genome fission requires at least two genes in original chromosome.
                eligible = [g for g in genes if sum(
                    int(other[CHROM]) == int(g[CHROM]) for other in genes) > 1]
                if eligible:
                    chosen = eligible[int(rng.integers(len(eligible)))]
                    chosen[CHROM] = int(rng.choice(available_chroms))
                    counter["chromosome_changes"] += 1
                    counter["chromosome_births"] += 1
            elif move == "chrom_copy" and genes and available_chroms:
                # Duplicate an entire chromosome block, not just one gene.
                source_chrom = int(rng.choice(sorted(active_chroms)))
                block = [g.copy() for g in genes if int(g[CHROM]) == source_chrom]
                if len(genes) + len(block) <= MAX_GENES:
                    new_chrom = int(rng.choice(available_chroms))
                    for copied in block:
                        copied[CHROM] = new_chrom
                        copied[INNOVATION] = next_innovation
                        next_innovation += 1
                    genes.extend(block)
                    counter["duplications"] += len(block)
                    counter["chromosome_births"] += 1
    matrix = np.zeros((MAX_GENES, FIELD_COUNT), dtype=np.float64)
    if genes:
        matrix[:len(genes)] = np.asarray(genes)
    return matrix, np.int16(len(genes)), next_innovation, counter


def describe(program: np.ndarray, count: int) -> list[dict[str, object]]:
    return [{"id": int(g[INNOVATION]), "chromosome": int(g[CHROM]) + 1,
             "operation": OPCODES[int(g[OP])], "reads": INPUTS[int(g[SOURCE])],
             "affects": TARGETS[int(g[TARGET])],
             "strength": round(float(g[WEIGHT]), 3),
             "threshold": round(float(g[THRESHOLD]), 3)}
            for g in program[:int(count)]]
