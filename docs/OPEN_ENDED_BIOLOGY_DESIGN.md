# Beyond fixed loci: rigorous design for evolvable regulatory and body architecture

**Status: proposal only.** v1.0.1 intentionally does not implement any of these new biology systems. They would alter the simulation, invalidating comparability of historical experiments unless the engine is versioned.

## Feasibility boundary

A simulation can evolve new **sequences**, regulatory circuits, neural connectivity, combinations of actions and unexpectedly useful functions *within the operations its world makes possible*. It cannot literally invent an unknown physical interaction if there is no way to express or execute that interaction. For example, a genotype grammar with `sense`, `move`, `attach`, `secrete`, `store`, and `digest` primitives could evolve an unplanned cooperative pumping strategy. It could not spontaneously generate magnetism or a novel chemistry without model-level representations for such interactions.

Do not interpret random executable Python as a genome. Mutant strings passed to `eval` or imported as modules would be insecure, nondeterministic and scientifically hard to interpret. Use a constrained interpreter with finite energy, instruction limits and deterministic operations.

## Proposed genotype layers

1. **Chromosomes as immutable digital records.** Each includes a stable innovation identifier, discrete gene boundaries, per-gene type, alleles/instructions, regulatory inputs and optional homolog identifier. Duplications, inversions, deletions, insertions and recombination should be serializable and replayable. A chromosome is a sequence of executable *virtual instructions*, not arbitrary Python code.
2. **Gene expression / regulation.** Environmental and internal sensor molecules trigger gene on/off states; expression changes carry a metabolic cost, delay and decay. This enables developmental timing and context-dependent expression. An initial minimal rule might be a bounded weighted regulatory graph with inhibitory/activating edges.
3. **Evolvable morphology.** Encode repeatable segments or virtual cells with locations, sizes, energy maintenance and a narrow set of functional ports. Bodies can gain or lose segments, but their mechanics follow world laws shared by every organism. Decorative visuals render the body *after* morphology is generated.
4. **Evolvable computation.** Agents begin with simple sense-and-act genes. Structural mutations can create novel combinations of small operators such as `add`, `gate`, `delay`, `compare`, `activate` and bounded memory. These are the **expressive vocabulary**; evolution can discover arrangements never manually prescribed.
5. **Reproduction with homolog alignment.** Recombination should align innovation IDs/gene families, not blindly zip arbitrary arrays. Single-parent cloning remains a valid path; pairing requires compatible representations and a documented cost budget.
6. **Ecology/fitness is still implicit.** No hand-authored survival behavior or “top 50%” pruning. Reproduction consumes parent energy; performance is reproductive success, persistence, resource budgets and ecological effects under a declared world.

## Performance and safety constraints

- Per-organism instruction cap per simulation tick and total memory/segment caps.
- Always-bounded outputs for motor force, secretion rates and sensed quantities.
- Deterministic interpreter using explicit PRNG state; serializable full organism state.
- Prohibit filesystem, networking, dynamic imports and arbitrary native execution from genotype instructions.
- Preserve global energy/resource accounting and verify non-creation of energy except explicitly modeled world inputs or cheats.
- Do not regenerate the entire phenotype from scratch each draw frame. Cache genotype compilation keyed by stable genome hash; invalidate only on mutation/development changes.
- Avoid arbitrary global genome growth. Structural mutations must have costs, and long-lived archives should stream to disk rather than retaining full sequence histories in RAM.
- Version the interpreter opcodes and checkpoints. Unknown opcode must fail safely (or be represented as inert) rather than executing arbitrary code.
- Track phenotypic diversity, genome complexity, lineage survival, novelty and ecological function separately; do not use genome length as a proxy for intelligence.

## Phased experiments with acceptance gates

### Phase 0: engineering release gate

Complete **Windows SDL/Pygame GUI QA**, migration tests for older checkpoints, a bounded/archive-storage design and deterministic test baselines. Do not couple a new genome representation to viewer event handling.

### Phase 1: regulatory networks only

Keep the same 12-locus physiology and movement, but add a small regulatory graph controlling expression of existing loci. Test: disabled regulator restores legacy phenotype; environmental stimulus changes expression without changing DNA; no negative energy creation; deterministic checkpoint reproduction; overhead stays within a measured target.

### Phase 2: variable-length inert genes

Allow insertion, deletion and duplication of *neutral/inert* genes. They must inherit, recombine, survive save/reload and accrue real costs. Test that random genomes don't crash and mutations don't execute new Python. Record fixation under neutral drift.

### Phase 3: bounded functional gene modules

Allow expression of genes encoding combinations of existing bounded operators. Examples: oscillator, feedback control, environmental cue filter, delayed metabolite store. **Do not** pre-script “cooperation” or “hunting”; let selection or drift act on the modules. Include control groups with modules disabled and shuffled, with preregistered primary outcomes.

### Phase 4: evolvable virtual body architecture

Introduce a physical construction graph with a few primitive tissue or cell types, not hardcoded animal silhouettes. Cell replication/maintenance costs energy. Use small populations at first, test morphology generation over 100k mutations, and treat novel appearance as evidence of variation—not function.

### Phase 5: population-scale testing

Parallel independent seeds (NumPy `SeedSequence` or other documented independent PRNG streams), randomized environments, matched starting configurations, neutral genetic markers and archive manifests. Replicate discoveries in novel conditions and report negative runs. Add novelty search as **experimental comparison**, not a replacement for actual ecological selection.

## Why this plan is not NEAT pasted into a biology simulator

NEAT demonstrated useful principles for evolving *network topology*: structural innovations, alignment for crossover, and protecting innovation through speciation. Our objective is broader: genotypes must also produce bodies, resource costs, developmental schedules and interactions with the physical world. Borrowing topology methods is a research starting point, not evidence that complex life will spontaneously arise.

## Scientific validity requirements

- State **what is preprogrammed** (the instruction vocabulary, world physics, initial genome grammar, mutation operators, environmental gradients).
- State **what is evolved** (variable genome sequences, network connections, regulatory edges, body segments, behavioral policies).
- Distinguish **heritable adaptation**, genetic drift, developmental plasticity, and experimental artifact with interventions.
- Preserve controls across environments and independent training seeds; track *reproduction and resource accounting*, not just attractive trajectories.
- Report structural novelty only if it has a stable representation and measurable functionality, not just a unique genome hash or color.

## Key research references

- Stanley & Miikkulainen, *Evolving Neural Networks through Augmenting Topologies* (2002), DOI 10.1162/106365602320169811: https://pubmed.ncbi.nlm.nih.gov/12180173/
- NumPy documentation on reproducible parallel random streams: https://numpy.org/doc/stable/reference/random/parallel.html
- Python Packaging User Guide on controlled project metadata: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/

**Decision:** Treat the first new-genome release as a **new engine version** with migration, compatibility tests and deliberate biological changes. Do not silently modify archived v0.1–v1.0 experimental dynamics.
