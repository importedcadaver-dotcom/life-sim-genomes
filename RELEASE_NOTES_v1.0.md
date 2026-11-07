# The Accidental Biosphere v1.0 — Genetic Life

**First release with multi-trait digital biology, inheritable morphology, structural gene changes and local sexual recombination.**

## Added

- 12 genome loci controlling creature size, metabolism, digestion, movement, turning, senses, lifespan, maturation, reproductive investment, and cute pink/pastel appearance.
- Variable gene-copy count (0–3 per locus), mutation and random duplication/deletion inherited by descendants.
- Individual infant development: smaller newborns grow toward their inherited adult phenotype without DNA changes.
- Local two-parent mating, per-locus crossover, two-parent genealogy and energy-conserving reproduction; asexual and mixed alternatives.
- DNA lab at the top of the viewer, shortcut **G**. Gene values, copy numbers, lineage and phenotype multipliers are visible for living and archived specimens.
- **DNA Spark** cheat in the Sugar Rush menu (**Q**, then **5**): random selected-creature DNA edit, permanently and visibly logged as non-scientific.
- Local parallel CPU genetics experiment (`python -m biosphere genomics`) with a matched mutation-disabled control, 12-seed example, CSV evidence, figures, and explanatory journal.
- An independent mutation-disabled selection-versus-drift assay (`python -m biosphere gene-selection`).
- Historical checkpoint loading and separate genetics opt-in for existing scientific scripts.
- New factual observation milestones for a first mutation, first gene-copy change and first two-parent birth.

## Fixed

- Recorded offspring lineage CSV now accepts two-parent records.
- Cheat-spawned babies carry the new body DNA and gene copy arrays and preserve save/load dimensional consistency.
- The DNA lab is fully visible at 1020×685 in Pillow-backed QA renders.
- Older programmatic calls to `simulate()` without new optional argument names still work.

## Measured

- **113/113 tests passed.**
- 12 matched mutation-on/off seed pairs ran for 1,600 ticks; read the full report before interpreting fitness differences.
- 12 matched metabolic-selection/neutral-drift pairs ran for 700 ticks.
- Legacy neural-only simulation remained byte-for-byte equivalent in all compared arrays over 430 ticks.

## Not implemented or verified

- Not molecular DNA, autonomous new gene inventions, unlimited genome length, speciation, diseases or protein expression.
- Pygame's real graphical window is not tested here; use `run_graphical_qa_windows.bat` on Windows.
- This is a scientific sandbox and game, not a verified open-ended evolution research platform.
