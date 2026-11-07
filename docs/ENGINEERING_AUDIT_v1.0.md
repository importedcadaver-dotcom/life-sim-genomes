# Accidental Biosphere v1.0 — Independent-style code, design and continuity audit

**Audit target:** the actual v1.0 source ZIP and the conversation’s promised functionality. The audit and repairs were performed on a separate copy, delivered as maintenance release **1.0.1**. Original v1.0 and its datasets are preserved. Date: November 4–5, 2026 (UTC/audit environment). The exact machine and dependency versions should accompany any scientific reproduction.

## Executive verdict

**A functional but research-prototype-grade game/simulator.** It is **not spaghetti throughout**: the engine, genome translation, science assays, cheats/minigames and viewer are already in separate modules, with no runtime import cycles. However, two central files accumulated too many responsibilities across rapid versions, and the scientific claims outpaced graphical verification. v1.0.1 fixes high-value state/checkpoint risks and documents boundaries while preserving all tested evolutionary trajectories. Some risk is intentionally unresolved.

There is **no evidence of lost historical scientific functionality** in this audit, but many legacy experiment modules depend on fixtures and archived data. Deleting them to make the file tree shorter would be incorrect. The program is still Python source, not a compiled Windows executable.

## Audit scope, evidence and methods

1. Extracted and inspected v1.0: 17 production Python modules, test modules, all experiment entrypoints, requirements, screenshots and README.
2. Ran the **original 113 pytest tests**; they passed. Measured line coverage using `coverage.py` instead of treating a green suite as complete coverage. Original project coverage was **72% of the files included in the measurement**, `biosphere.simulation` **94%**, `biosphere.genetics` **89%**, `biosphere.viewer` **9%**, `biosphere.cli` **18%**. The overall figure includes test files and therefore is **not exclusively production coverage**.
3. Inspected the AST import graph, large functions, save format, death/mutation arrays, playful actions and graphical QA stub. No runtime circular imports were present in the original or maintained code.
4. Created baseline deterministic fingerprints from v1.0 for four different ecological modes and repeated the same seeds, settings, 320 ticks and RNG state from the maintained source. **4/4 SHA-256 fingerprints matched exactly**.
5. Ran direct CLI smoke tests for `biosphere run --genetics`, `biosphere genomics` and `biosphere gene-selection`. These succeeded.
6. Benchmarked 650 headless ticks in three conditions (not a graphical FPS measurement). See `results/audit/benchmark.json`. Observed on this audit machine: **0.58 s** for 900-cap legacy, **1.14 s** for 900-cap mixed-genetics, **0.74 s** for sparse sexual ecology at 118 survivors. These timings are machine-specific and not general performance guarantees.
7. Compared the evolution of project promises from v0.1 to v1.0 against current code and test/QA visibility. See `FEATURE_TRACEABILITY.md`.
8. Researched Python packaging and pytest layout, maintainability/lint tools, simulation verification, deterministic RNG streams and evolvable topologies. References at end.

### Quantitative architecture inventory

Original production modules (`biosphere/*.py`): **17**; original `viewer.py`: **1,318 lines**, original `simulation.py`: **889 lines**. `results/` contains approximately **22–25 MB** of historical checkpoints/images and CSVs versus about **0.3 MB** of core Python source. This is distribution clutter rather than necessarily bad or dead code. Version 1.0.1 offers separate slim source and full research-data artifacts.

## Defects, risks and dispositions

| ID | Severity | Finding with code evidence | Status / action |
|---|---|---|---|
| QA-01 | High release gate | Native Pygame window, real event loop and Windows input were **never launch-tested** in this environment. Source: `viewer.py` and `tools/run_graphical_qa.py`. Pillow preview does not run SDL. | **Unresolved.** Included Windows QA script; requires manual target-platform verification. |
| ARCH-02 | High maintainability | Main viewer function encloses UI state, input dispatch, layout, overlays, saving and rendering in >1,100 lines; earlier top-level helpers also in same file. | **Partially fixed.** Extracted geometry/render helpers to `viewer_presentation.py`. Full event-loop decomposition deferred until native UI QA. |
| ARCH-03 | High extensibility | Biological mating, crossover, energy debits, newborn arrays and lineage append lived inside `World` (original `simulation.py:534–682`). | **Fixed.** Extracted to `reproduction.py`; kept stable `World` wrapper. Four modes unchanged. |
| STATE-04 | High data integrity | 20+ organism-aligned arrays were repeated in several literal append/remove/save lists (`_retain`, `save`, `load`, cheats). A future new-gene array could be omitted from a death mask, corrupting row identity. | **Partially fixed.** Shared `LIVE_ARRAY_FIELDS` and save/load validator; newborn append & cheat code still require deliberate changes when adding fields. |
| STATE-05 | High data integrity | `World.save` previously overwrote target NPZ directly; process interruption/disk exhaustion could leave a truncated prior save. No explicit schema version. | **Fixed.** Version 2 metadata, same-directory atomic file replacement, failure regression test; in-memory clones still supported. |
| STATE-06 | High data integrity | Loader accepted wrong-sized arrays without checking population/IDs/gene shapes. Corruption could surface much later as misleading behavior. | **Fixed.** Rejects malformed ID, resource, gene-copy, neural and population shapes, missing arrays and unsupported schema versions. Old compatible versions still load. |
| STATE-07 | Medium | Viewer observation notebook saved separately without a binding to its world; a copied/misnamed sidecar could show the wrong specimen timeline. | **Fixed.** Optional checkpoint SHA-256 in new sidecars; warning and fallback if wrong, backward-compatible old sidecars. |
| CONFIG-08 | Medium | NaN values bypass ordinary comparisons (`nan < 0` is false), and negative bite, sensing, newborn energy or nonsensical lifespan were not uniformly rejected. | **Fixed.** Additional finite/nonnegative guards and tests. |
| SCI-09 | High methodology | A single A/B lab run can start with world already changed by cheats. The lab description “one rule changed” obscured source contamination. | **Fixed label.** Reports show `source_interventions` and `scientific_status=illustrative_only`; source still unmodified by lab. |
| SCI-10 | High scientific limitation | Genome still has 16 fixed controller weights and **12 predefined biological loci, 0–3 copies**. Duplicating a locus does not generate an arbitrary new functional gene. | **Unresolved by design.** See `OPEN_ENDED_BIOLOGY_DESIGN.md`; new genotype interpreter requires separate engine release. |
| SCI-11 | Medium | Body-pigment and spot loci affect visuals only. Calling all 12 genes direct fitness determinants would be inaccurate; previously documented wording was mixed. | **Documentation corrected.** Actual physiology and cosmetic genes distinguished. |
| GAME-12 | Medium UX | “Replay” is a sampled track of one organism rather than re-simulating former world states; “immortal/Cozy” cheat uses lifespan of 1,000,000 ticks, not true immortality. | **Documented.** An exact world rewind and truly uncapped age are future gameplay features, not current capabilities. |
| GAME-13 | Medium | High population density and many overlays remain difficult to parse, and cosmetic bug art has not been native playtested. | **Unresolved.** Requires target-machine 10–20 minute observation sessions, resize, mouse, overlay and persistence QA. |
| PERF-14 | Medium long-run | `life_archive` holds full dead genomes and records indefinitely in memory; checkpoints serialize the archive as a single JSON metadata blob. Observation log and traces are bounded independently and can discard older event detail. | **Unresolved.** Need indexed disk archive, retention/export policy, random-access lineage records, save-size scaling benchmarks. |
| PERF-15 | Medium | Reproduction uses repeated NumPy concatenations and Python loops for mate matching; good at current cap, not engineered for tens of thousands of organisms or variable-length chromosomes. | **Unresolved for future scale.** Benchmark before optimization; avoid premature rewrites. |
| QA-16 | Medium | The original 113 tests include science and geometry but don't exercise the full actual Pygame draw/event loop. `viewer` line coverage was 9%; `cli` 18% in baseline coverage run. | **Improved, not closed.** Added integration tests for cheats + DNA + notebook + save/reload + A/B. Need real graphical QA and CLI coverage expansion. |
| DIST-17 | Medium usability | Windows viewer launcher installed full plotting requirements although only NumPy and Pygame are necessary for play. Large result archives clutter the install. | **Fixed in packaging.** Separate viewer requirements and lean source ZIP; full history remains available. |
| DOC-18 | Medium continuity | 19 KB README stacked historical version descriptions, sometimes presenting old controls and past cosmetic statements as current. A new contributor had to reconcile history manually. | **Fixed.** New concise README, architecture, trace matrix, historical README archived, release notes. |
| QA-19 | Medium | No bundled Git history/version-control metadata; Ruff and Pygame unavailable in audit environment, so no honest passing linter or real SDL certification. | **Open.** Use local Git init and run Ruff/Windows QA; add CI gate when repository is established. |
| SCI-20 | Medium | Viewer starts genetics-enabled, but headless `run` and bare `Config()` preserve old neural-only experiment defaults. Same seed does not imply same model. | **Intentional, documented.** Run `--genetics` explicitly and record full Config. Changing default now would compromise history. |
| QA-21 | Low | Static AST scanner originally counted type-checking imports as runtime circular imports; this was a false positive. | **Fixed.** `tools/audit_project.py` ignores `TYPE_CHECKING` blocks and reports no actual package import cycle. |

## Cross-feature verification added in v1.0.1

New maintenance tests exercise all of these in one flow: select and bookmark a genetics-enabled organism → DNA Spark → baby-clone cheat → test a minigame without consuming the ecology RNG → advance actual births/deaths → save world and notebook → load both → clone an A/B lab → ensure control world remains unchanged → resume the same deterministic evolution → check organism-array alignment. Additional tests reject malformed checkpoint data, failed atomic writes and notebook/checkpoint mismatches.

A brief test failure occurred while consolidating the array lists: `last_intake` was filtered twice on death. **The existing tests detected it immediately; the duplicate filtering was removed before the release.** This is a concrete example of the integration risks of broad refactoring and why one shared schema plus regression tests matters.

## Reproducibility evidence

| v1.0 baseline mode | 320-tick SHA-256 state fingerprint | 1.0.1 outcome |
|---|---|---|
| Legacy neural-only | `59426807f44404e982ecb4c64281eadb2664e8e83d5e9e985357dc8fac233692` | Exact match |
| Genetic asexual | `13a5218738c5b41499e2d0b85f85bdb32c84d489dc72b51a06e5906132aa9496` | Exact match |
| Genetic mixed | `9db94b367e127c5330faa75cfda39bf99fd7123ff699534caf77e8a9dd928f52` | Exact match |
| Genetic sexual islands | `05c368cba66076fa1e4bf23f2c4d3affb42c5d45c0ddcfca2d214986a91b5424` | Exact match |

The digest combines organism positions, angles, energies, ages, IDs, parent IDs, generation, neural genomes, biological loci/copies, mutation counts, food/capacity arrays and RNG bit-generator state. Matches apply to the **same environment and parameters**; they are not cross-version universal hashes.

## Recommended release gates BEFORE adding new genetic functions

1. Run native `run_graphical_qa_windows.bat` successfully and inspect real screenshots. Also perform a sustained 900-organism run and a 10–20 minute human playtest with UI/keyboard controls.
2. Introduce indexed/archive-on-disk persistence and a migration strategy for existing `life_archive` JSON if indefinite evolutionary simulations are planned.
3. Keep v1.0.1 as a stable baseline. Design a versioned variable-length genome format with an interpreter/runtime budget; don't bolt arbitrary gene strings onto the fixed 12-column `body_dna` matrix.
4. First evolve only **regulatory combinations** of known loci, then neutral variable-length genes, then bounded functional modules. Test new structure separately from genotype-to-phenotype effects.
5. Verify ecological resource conservation, genotype-to-phenotype interpretation, mutation boundedness, save/resume determinism, and replication across independent seeds. Add a human-readable “genome diff” to the chronicle only when the new representation is stable.
6. Improve viewer module decomposition incrementally: targeted event dispatch, saved-world workflow, overlays and draw components, each with graphical smoke tests. No simultaneous all-at-once rewrite.

## Research sources used to judge code quality

- Python Packaging User Guide, `pyproject.toml` metadata and flat/src layout discussion: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ and https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ . A flat layout is valid for a small single-app project; a `src` migration is not by itself a quality improvement.
- pytest, *Good Integration Practices*: https://pytest.org/en/stable/explanation/goodpractices.html . Test organization, installed-code testing, and meaningful import-mode rules are more useful than raw test count alone.
- Ruff documentation (safe fixes, unused imports, complexity rules) and FAQ (Ruff is not a type checker): https://github.com/astral-sh/ruff/blob/main/docs/linter.md and https://github.com/astral-sh/ruff/blob/main/docs/faq.md . **Ruff wasn't available in this environment**: no passing Ruff result is claimed.
- NumPy, *Random Generator* and *Parallel random number generation*: https://numpy.org/doc/stable/reference/random/generator.html and https://numpy.org/doc/stable/reference/random/parallel.html . Save exact generator state and use reproducible independent experiment streams.
- NASA Software Engineering Handbook, verification planning / traceability and target-environment testing: https://swehb.nasa.gov/spaces/7150/pages/16450576/SWE-028%2B-%2BVerification%2BPlanning . Test counts are not substitutes for requirements coverage and real deployment validation.
- Stanley & Miikkulainen, *Evolving Neural Networks through Augmenting Topologies* (2002): https://pubmed.ncbi.nlm.nih.gov/12180173/ . Structural growth, alignment and novelty protection are relevant future design concepts, but do not automatically yield open-ended chemistry or intelligence.

## Final verdict

**Do not add arbitrary new genes/chromosomes to the current fixed-array model yet.** The most dangerous outcome would be to replace deterministic, measured evolution with a large opaque framework that generates decorative new genome labels while silently breaking saves, energy accounting and historical experiments. v1.0.1 creates a clearer foundation and better release gates; it deliberately leaves the fundamental open-ended representation for the next independently tested development phase.
