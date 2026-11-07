# Experiment 009 — Artificial DNA, mutation, inheritance and selection

## Question

Does the upgraded engine support inheritable biological phenotypes, genuine two-parent recombination, bounded gene duplications/deletions, and differential lineage success under ecological constraints? Does switching new mutations on systematically improve birth counts over the first 1,600 ticks?

## Tests and design

### Test A: Matched mutation controls

Twelve random-seed pairs: seeds 2001–2012. Each world begins with 75 randomized organisms in a 48×36 habitat with 250 carrying-capacity slots, 0.008 food regrowth and mixed local mating. Both members of a pair have the same initial seed and founding distributions. One condition enables neural/body/copy-number mutation; the other disables all new mutations while preserving heritable founder variation, resource competition, and crossover. Both run 1,600 ticks, and genotype/copy-number means are saved every 50 ticks. The two branches diverge after their first different mutation events; shared initial random seed does not mean identical random noise throughout.

**Results** (12 seeds; descriptive only):

| Outcome | Mutation ON | Mutation OFF |
|---|---:|---:|
| Mean births per world | 888.9 | 851.8 |
| Mean surviving organisms at tick 1,600 | 189.8 | 175.9 |
| Mean maximum living generation | 14.08 | 13.33 |
| Extinct worlds | 0/12 | 0/12 |
| Total biological point mutations | 5,733 | 0 |
| Total gene-copy mutations | 1,068 | 0 |
| Total two-parent births | 551 | 328 |

Matched mutation-enabled worlds had more births in **9 of 12** pairs, not all 12. Mean difference: +37.2 births. These are exploratory results, and no confidence interval or null-hypothesis significance claim is established. Increased births alone do not show *novel intelligence* or unbounded genetic complexity; offspring density, mutation load, controller changes and mate availability interact.

A full recorded population's modeled genome includes 16 neural sites plus 0–36 body-gene copies (28 initially; 16–52 possible). The mutation-enabled worlds' mean site count across final populations was close to 28, with modest upward drift; copied loci do not introduce new gene names.

### Test B: Selection versus neutral drift

Twelve independent matched seeds (12–23), 700 ticks. Each environment starts with 110 organisms (55 plus alleles and 55 minus alleles), identical zero-weight controllers and all other biological loci set to zero. Reproduction is **asexual**, with **no mutation**; allele shifts come from inherited standing variation rather than new copies, neural changes or recombination.

- **Functional condition:** half carry metabolic-efficiency allele +1.7, half −1.7, in the same scarce-food environment. This locus changes energy expenditure by design.
- **Neutral control:** the same half/half labels are carried on the `pigment` locus instead. Pigment changes colors but has no functional effect on feeding, metabolism, motor control or reproduction.

All 12 functional-condition populations survived and the +1.7 efficient lineage became the only surviving genotype in **12/12**. The neutral-color condition showed variable drift: 10/12 populations survived, with the positive marker's final fraction averaging about 50% among survivors. Positive-only neutral fixation occurred in 2 surviving runs and negative-only fixation in 3. Comparing neutral markers to the specified efficiency gene verifies that model differences are not simply an artifact of the lineage-counting code.

**Crucial caveat:** this result validates a *deliberately engineered trait advantage*. It does not mean evolution discovered a novel biochemical function. Selection can also generate genetic drift, ecological overshoot, or extinction; it is not a universal optimization guarantee.

### Replay and audit

- All 113 existing and new automated tests passed, including DNA inheritance, newborn growth, controlled metabolic effects, energy accounting, DNA mutation bounds, parent links, reproduction modes and exact checkpoint continuation.
- The original v0.9 neural-only dynamics were compared from identical seed 911, 430 ticks. Every tested array (`ids`, positions, ages, energies, food, controllers and parents) matched **exactly**, showing legacy evolution remains unchanged when genetics is disabled.
- Local-CPU sequential and parallel genomics experiments produce identical output CSVs for the same seeds and configurations.
- The lineage CSV exporter now supports optional `parent2_id` fields without crashing.
- Graphical Pygame UI is not launch-tested on Windows here; previews are generated through the existing Pillow drawing harness, and Windows has a graphical QA launcher.

### Inspectable outputs

`results/genetics_study_12seed/` includes `genomic_timelines.csv`, `final_populations.csv`, `summary.json`, mutation comparison and gene-copy trajectory charts.

`results/gene_selection/` includes `selection_timecourses.csv`, `selection_final.csv`, `selection_summary.json`, and the selection-versus-drift chart.

The study is an initial internal validation, not a scientific paper. New biological rules alter selection pressures; do **not** compare v1.0 genetics-enabled outcomes to v0.9 control runs as though only one variable changed.
