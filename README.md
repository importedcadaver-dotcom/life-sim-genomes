# The Accidental Biosphere 1.1 — Evolvable Regulatory Life

A **cute, pink artificial-life observatory** backed by a reproducible digital-ecology experiment. The inhabitants inherit small neural controllers and, in genetics mode, an additional 12-locus biological genome. They eat, move, grow, reproduce, mutate and die. In v1.1, regulatory circuits can evolve within a bounded instruction language. Their behavior is simulated, **not scripted intelligence**.

**1.0.1 was the maintenance and audit release**: it does not change ecological rules, mutation probabilities, or experimental outcomes. Four matched 320-tick simulations reproduced v1.0 bit for bit. The new maintenance tests cover checkpoint validation, file-write failure recovery, old/new gameplay interactions and observer-sidecar integrity.


## What's new in v1.1

New viewer worlds now have heritable **variable-length regulatory genes** and evolvable chromosome groups. Each gene may read local food, energy, age, crowding or another regulatory signal and affect real physiological or motor pathways. Genes can become noncoding, duplicate, be newly inserted, be deleted, or participate in chromosome fission/copying. This is a **bounded virtual instruction system**, not unbounded biological invention or executable Python. Press `G` and then `VIEW REGULATORS` to see each creature's actual instructions and current expression. The `E` minigame menu now includes Genome Detective.

Historical experiments remain opt-in safe: headless `run` defaults to the earlier neural-only ecology; use `--regulation` to enable the new system (implies `--genetics`). `--disk-archive` writes dead-organism histories to SQLite and embeds the indexed archive in portable checkpoints. New viewer worlds enable regulation by default; use `--no-regulation` for v1.0-style 12-locus biology or `--legacy-genetics` for original neural-only mode.

The new regulation experiment was **inconclusive on fitness**: eight-seed paired runs averaged 124.4 births with regulation versus 120.4 without it, but regulation won only five of eight seed pairs. The important new capabilities are inherited regulatory dynamics and chromosome innovation, not proven open-ended evolution. Full docs: [v1.1 gene regulation](docs/GENE_REGULATION_v1.1.md), [Experiment 010](docs/EXPERIMENT_010.md), [engagement design](docs/ENGAGEMENT_DESIGN_v1.1.md), and [disk archive](docs/DISK_ARCHIVE_v1.1.md).

## Quick launch (Windows)

Extract the ZIP to a writable folder. Double-click `run_windows.bat` to install just the viewer dependencies and start a fresh genetics-enabled world. To run real graphical input tests, double-click `run_graphical_qa_windows.bat`. The actual Windows/Pygame rendering path has **not yet been validated in this environment**; the preexisting image preview harness is not a substitute.

Or use a terminal:

```powershell
python -m pip install -r requirements-viewer.txt
python -m biosphere view
```

**Headless research requires only NumPy.** For plotting and development, `requirements.txt` and `requirements-dev.txt` remain available. `pyproject.toml` describes the optional dependency groups.

```powershell
# Genetics-enabled research; headless run defaults to historical neural-only mode.
python -m biosphere run --genetics --regulation --seed 19 --steps 1500 --events --output results/my_genetic_world

# Two-parent-only ecology (viewer normally starts in mixed mode)
python -m biosphere view --reproduction-mode sexual

# Small test suite, static inventory and original research study examples
python -m pytest -q
python tools/audit_project.py --output results/my_audit/project_metrics.json
python -m biosphere genomics --seeds 4 --ticks 600 --workers 1 --output results/my_genome_study
```

## Explore the game

| Key | Action |
|---|---|
| `G` | DNA inspector: genes, copy numbers and expressed traits |
| `O` | Neural microscope: sensory inputs, inherited controller |
| `Y`, `A` | Family tree and extinct-organism archive |
| `D` | Living chronicle, bookmarks and sampled movement trails |
| `W` | Two-world demonstration laboratory (one intervention) |
| `Q` | Cheats: candy food, energy, baby clones, Cozy mode and DNA Spark |
| `E` | Berry Hunt, Speed Detective, or Genome Detective minigames |
| `Space`, `N`, `+`, `-` | Pause, single-step, speed up / slow down |
| `S` | Save a world, notebook and screenshot (requires Pygame) |
| `R` twice | Confirm destructive restart |

**Cheats and sandbox changes are logged** in the checkpoint. Minigame scores do not change ecological fitness. An A/B comparison from an already modified source world is labeled *illustrative only*; a single A/B pair never establishes a general scientific result. The chronicle's replay shows **sampled organism positions**, not a rewind of the entire world.

### The genetics model

- The original neural controller is a fixed `2 × 8` weight matrix (16 weights).
- Genetics-enabled creatures have **12 named loci**, each with a bounded allele and 0–3 copies, plus mutations of the neural weights.
- Biological loci influence size, digestion, maintenance, propulsion, turn rate, sensory reach, sensor gain, maturation, reproductive investment and lifespan. Pigmentation and spots are inherited **visual traits** rather than fitness drivers.
- Genetically inherited mutations and local two-parent recombination can change which genotypes survive and reproduce. There is **no fixed top-half survivor selection**.
- v1.1 adds *new virtual regulatory instructions* and chromosome groups through mutation. Those programs are composed from a predefined set of safe signal inputs, operations, and physiological targets; the ecosystem cannot invent arbitrary new physical interactions or molecular reactions. See [v1.1 gene-regulation guide](docs/GENE_REGULATION_v1.1.md).

### Historical compatibility

The viewer **starts with genetics enabled**, but `Config()` and the `run` command use **legacy neural-only mode** by default to preserve experiments 001–008. Add `--genetics` to headless runs; older checkpoints continue in their original mode. The code and file formats are documented in [architecture](docs/ARCHITECTURE.md).

## Documentation for developers

| Document | Purpose |
|---|---|
| [Engineering audit](docs/ENGINEERING_AUDIT_v1.0.md) | Verified findings, fixes, unresolved risks and reproducibility results |
| [Architecture and contribution guide](docs/ARCHITECTURE.md) | Module responsibilities, control flow and safe extension rules |
| [Feature traceability](docs/FEATURE_TRACEABILITY.md) | Historical feature promises mapped to code, tests and limitations |
| [Evolutionary expansion design](docs/OPEN_ENDED_BIOLOGY_DESIGN.md) | Safe plan for evolvable regulatory architecture and novel combinations |
| [1.0.1 release notes](RELEASE_NOTES_v1.0.1.md) | Exact maintenance changes and QA |
| [Original v1.0 README](docs/README_HISTORY_v1.0.md) | Preserved version-by-version development history |
| [Scientific studies](docs/JOURNAL.md) | Experiments 001–009 and their reporting caveats |
| [Graphical QA guide](docs/GRAPHICAL_QA_v0.8.md) | Automated Windows/Pygame testing |

Results for historical experiments are preserved in the **full research archive**. The separate **lean source ZIP** keeps the two fixture worlds required by existing tests; unpack the research-data ZIP into the project folder to explore the entire historical dataset.

## Important limitations

- GUI/SDL rendering remains unverified on Windows. Automated headless image previews are not real Pygame screenshots.
- Memory-mode archives still grow indefinitely. Add `--disk-archive` for an indexed SQLite-backed archive that reduces runtime RAM use, but complete checkpoint saves still materialize/compress the database.
- `viewer.py` still owns much of the interactive event/render loop and needs further staged decomposition after actual graphical QA.
- Exact numeric reproducibility across NumPy versions/operating systems is **not guaranteed**; the tested state fingerprints apply to the environment recorded in the audit.
- There is no arbitrarily self-inventing physics, new cell types, evolved instruction set, or proven intelligence.

Run `python -m biosphere --help` for the complete CLI. Use a Git repository for new changes: `git init`, `git add .`, and `git commit -m "Baseline 1.0.1 maintenance release"` after unpacking the desired distribution.
