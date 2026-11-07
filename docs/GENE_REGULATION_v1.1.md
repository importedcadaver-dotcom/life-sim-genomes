# v1.1: Evolvable gene-regulatory chromosomes

## What is implemented

The original ecological selection, 16 neural controller weights and 12 continuous biological loci remain intact. This release adds a **separately opt-in**, heritable, bounded instruction sequence controlling the *expression* of some biological and motor traits. New viewer worlds opt in; historical headless experiments and old checkpoints stay on the original rules unless explicitly enabled.

The virtual genome is not literal DNA, a protein simulator, an unrestricted computer, or a free-form program in Python. Every action is performed by a safe numerical interpreter in `biosphere/regulatory.py`.

### Gene format

One regulatory instruction has seven fields:

| Field | Meaning |
|---|---|
| Opcode | DIRECT, GATE, INVERSE, PRODUCT, or NONCODING (neutral instruction) |
| Source | Constant, local resource level, internal energy, crowding, relative age, left/right food difference, or one of two internal regulator registers |
| Target | Basal metabolism, digestion, propulsion, turning, sensing, growth, reproduction investment, motor turn bias, motor speed bias, or either regulator register |
| Weight | Heritable signed effect strength, clamped to -3..3 |
| Threshold | Heritable activation threshold, clamped to -2..2 |
| Chromosome | Heritable chromosome group identifier, 0..7 |
| Innovation ID | Gene identity inherited through recombination; inserted/duplicated genes acquire new IDs |

Each organism has a **variable-length active sequence** (0–16 instructions) with zero padding for efficient NumPy storage. Founders receive 2–4 random genes on two chromosome groups. The order matters: a rule can set regulator A; a later rule can read it and conditionally influence maintenance or steering. Noncoding instructions initially have **no effect** on phenotype but can mutate into functional instructions.

Regulatory expression is re-evaluated from current surroundings and physiological state. The interpreter is deterministic, side-effect-free, and consumes no random numbers. Outputs affect the ordinary ecological equations through bounded multipliers: `exp(0.17 * clip(expression,-3,+3))`. Motor biases are bounded before the existing turn/speed nonlinearities. Extra expressed machinery costs maintenance energy (`0.6%` per active regulatory instruction). This discourages uncontrolled genomic bloat but does not guarantee optimal genome sizes.

### Structural changes

- Point mutations modify opcodes, signal connections, targets, weights, or thresholds.
- Insertions can create new instructions from the available language.
- Existing instructions can duplicate or be deleted.
- Chromosome fission moves a gene into a genuinely new chromosome group; chromosome copying duplicates an entire selected group (bounded by the 16-gene capacity).
- Two-parent reproduction chooses whole chromosome groups from each mate. Asexual inheritance copies the parent sequence before mutation.
- Regulatory mutations are counted separately. Observers can inspect genes, innovation IDs, chromosomes, current expression and some history in the DNA panel. Genes are stored in deceased-specimen biographies and checkpoints.

### What evolution can and cannot discover

The game does **not** hand-code "when hungry, search for food" or choose optimal genetics. Novel combinations of genetic instructions can produce different conditional pathways, including multi-gene chains using both regulator registers. Whether those combinations benefit reproduction is an ecological result, not a designed fitness score.

However, **no program can acquire a brand-new physical output absent from the substrate**. For example, evolving a new pathway from energy → regulator A → digestion is possible; spontaneously inventing wings, photosynthesis, or a new element is not possible until more modular body parts, reactions, and interactions are defined. The substrate is deliberately bounded to prevent runaway computation, corrupt saves, and executable code injection. “Open-ended” is a research aspiration, not a claim about v1.1.

### Extension sequence and acceptance gates

1. Validate regulatory expression and conservation of energy; test neutral genes independently.
2. Demonstrate chromosome birth, duplication, deletion, and inherited novelty across multiple generations.
3. Use matched training-seed comparisons and *a priori* outcomes to test fitness effects, including blinded sensors and mutation-disabled controls.
4. Introduce a general virtual chemistry substrate (typed resources, reaction graphs, mass/energy budgets) as its own version, then allow genes to construct paths **only from conserved physical primitives**.
5. Introduce modular morphology and ecological interactions only after chemistry and phenotype layers support meaningful novel capabilities.
6. Add complexity and novelty metrics with appropriate null models; do not count every code duplication as a useful biological innovation.

### Backward compatibility

`Config(regulation_enabled=False)` is the default, even in genetics mode, to preserve Experiments 001–009 and historical checkpoints. `python -m biosphere run --regulation` enables the new system and also enables biological genetics. New viewer sessions enable regulation unless launched with `--no-regulation` or `--legacy-genetics`. Checkpoints use schema 3 and contain active program matrices, lengths, innovation counters, and optional SQLite archive snapshots. Existing schema 1/2 checkpoints load without introducing new random draws or changing their rules.

### References

- Vaishnav et al., **The evolution, evolvability and engineering of gene regulatory DNA** (Nature 2022): https://www.nature.com/articles/s41586-022-04506-6
- Papadadonakis et al., **Evolution of gene regulatory networks by means of selection and random genetic drift** (PeerJ 2024): https://pmc.ncbi.nlm.nih.gov/articles/PMC11365478/
- Stanley & Miikkulainen, **Evolving Neural Networks through Augmenting Topologies** (Evolutionary Computation 2002): https://pubmed.ncbi.nlm.nih.gov/12180173/

This implementation is inspired by broad principles (evolvable regulation, structural mutation and complexity management), not a direct reproduction of any cited experimental system.
