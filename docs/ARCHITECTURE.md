# Architecture and contributor handoff — 1.0.1

The goal of the structure is **one authoritative simulation**, with all the fun features reading its state rather than silently inventing ecological effects. This is a single-user Python game, not an enterprise services project. Prefer small, direct, testable modules over abstract frameworks.

## Dependency map

```text
                       biosphere/cli.py
                    /      |        \
           experiments  viewer.py   simulation.py (World)
                              |         |            |
                  viewer_presentation.py |        state_schema.py
                       |       playful.py  reproduction.py
                       |           |         |            |
                       +-----------+---------+----- genetics.py
```

Actual runtime imports are acyclic. `reproduction.py` and `state_schema.py` refer to `World` only under `TYPE_CHECKING`. Viewer code must never be imported from `simulation.py`.

## Module ownership

| File | Owns | Must not own |
|---|---|---|
| `simulation.py` | Config, global clock, population-aligned arrays, energy/food physics, births/deaths orchestration, organism records, checkpoint API | GUI state, minigame scoring |
| `genetics.py` | Fixed 12-locus names, mutation, copy-number changes, recombination, genotype-to-phenotype mapping | Pygame, world clock, fitness ranking |
| `reproduction.py` | Local two-parent matching or budding, cost accounting, offspring creation | Rendering, cheat actions |
| `state_schema.py` | Canonical live-array names, save version, save/load validation | Mutation, random draw |
| `playful.py` | Explicit interventions, genome-derived colors, minigames, Chronicle, 100-step A/B lab | Changing evolutionary policies without intervention marker |
| `viewer_presentation.py` | Geometry, UI timer, QA input parsing, heatmap and cute organism draw helper | World stepping and genetics |
| `viewer.py` | Input dispatch, overlay integration, selected camera, frame drawing and saved notebook orchestration | Independent ecological rules |
| `experiment.py` etc. | Replicated science assays and raw outputs for experiments 001–009 | Writing to active viewer world |
| `cli.py` | CLI flags, default configuration and command entry points | Core physics |
| `tools/` | Screenshot QA, archive manifest verification, static inventory | Production biology |

`environment`, `investigation`, `navigation`, `residency`, `trajectory`, `fitness`, `selection_008`, `selection_assay` and `genomic_experiment` are historical experiment implementations: do not delete as “unused” without verifying their CLI entry points and earlier paper results.

## From genome to reproduction

```text
founder_dna + neural weights
             |
       step() -> perceive() -> controls() -> move
                  ^                            |
             biology()                  ingest food / spend energy
                                               |
                                         hunger / old age deaths
                                               |
                      reproduce_biological() when energy/maturity permit
                                               |
                             1 or 2 parents -> recombine -> mutate
                                               |
                                 new DNA + neural weights + child ID
```

There is no top-50-percent survivor filter or explicit numerical fitness function in the ecology. Fitness is **realized reproduction and persistence under a shared resource budget**. A gene can affect several phenotype values through `traits()`; pigmentation/spot genes are decorative. Do not call emergent behavior intelligent without independent operational tests.

## Invariants and save format

1. **World is authoritative.** Every living organism's field is aligned by row index, *not* by immutable organism ID. `LIVE_ARRAY_FIELDS` in `state_schema.py` must list any new row-aligned array, and that array must participate in newborn append, death retention, save/load and genotype inspection.
2. **Save/reload determinism.** Checkpoints store RNG bit-generator state, genomes, positions, food, counters and observational archives. Checkpoints use schema version 2. Filepath saves are staged then atomically replaced; in-memory `BytesIO` is preserved for A/B clones.
3. **Observations cannot make decisions.** `World.watch()`, `stats()`, chronicle, GUI rendering and minigames must not consume `World.rng`, modify energy, move creatures or alter genomes. Use separate RNGs for display-only challenges.
4. **Interventions must be visible.** `World.manual_interventions` records cheat, food brush and live-rule changes. Source contamination is exposed in A/B lab reports. An experimental control is a fresh `World` with declared config and no unrecorded user edits.
5. **Science reproducibility is local.** Seeds and RNG state are necessary but not enough for exact cross-dependency, cross-CPU or cross-version replays; record program and library versions along with the experimental protocol.
6. **No dynamic arbitrary code execution.** Later “invented genes” should run inside a fixed, sandboxed instruction interpreter with budgets, not Python `eval`/`exec` built from mutations.

The older checkpoint decoder accepts missing v0.6/v0.9 observation fields; an existing neural-only checkpoint remains neural-only. Unknown newer checkpoint schemas fail closed instead of being silently misread.

## How to add a feature without losing an older one

1. **Define the behavior or measurement precisely.** Ask whether it is physiology, heredity, environment, instrumentation or cheating; choose the owner accordingly.
2. **Write the invariants.** State shape, resource conservation, duration, mutation bounds, backwards compatibility, no RNG effects for observation.
3. **Write a focused test.** Then add one cross-feature test with save/reload, legacy mode, cheat mode or comparative laboratory as appropriate.
4. **Preserve fingerprints** from `test_maintenance_v101.py`. If biology changes on purpose, move changed trajectories into a versioned experimental engine instead of silently changing them.
5. **Check UI separately.** Run Pillow-backed previews for easy clipping regressions and then actual `run_graphical_qa_windows.bat` on Windows. Neither substitutes for a 10–20 minute manual playtest.
6. **Update traceability** and the experiment journal, including negative results. Keep instrumented worlds separate from test controls.

## Developer commands

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/audit_project.py --output results/my_audit.json
python tools/verify_release.py
python -m biosphere run --genetics --steps 100 --output results/my_test
python -m biosphere view --window-width 1020 --window-height 685
```

Ruff, pytest, and formatting should run locally and in CI if available. As of this audit, **Ruff and the native Pygame runtime were not installed in the audit environment**: do not describe them as passed. If adding a Git repository, commit the source, tests and research plans; large generated data should be tracked as release artifacts or external datasets, not duplicated on every commit.

## Known decomposition still needed

`viewer.view` remains a large closure containing input and draw state. The next safe step is to extract **overlay panels** behind thin, tested rendering interfaces after real Pygame QA—not to rewrite all interaction and biology simultaneously. `World.step` retains movement/feeding/death phases together, but reproduction is now separated. Archive persistence should eventually use an indexed on-disk store rather than growing JSON dictionaries forever.
