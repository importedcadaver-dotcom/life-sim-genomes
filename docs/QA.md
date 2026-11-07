# QA and verification

**Historical QA register (v0.5–v0.6). For current v0.7 evidence, see the addendum below.**

| Check | Status |
| --- | --- |
| Python modules syntax check | PASS (`compileall`) |
| Identical seeds replay identically | PASS |
| Different seeds generate different terrain | PASS |
| Resource cell never becomes negative under many overlapping agents | PASS |
| Birth uses valid parent IDs and generation increment | PASS |
| Simulated reproduction cannot push above population cap | PASS |
| Checkpoint continuation equals uninterrupted simulation | PASS |
| New checkpoint preserves aggregate measurements | PASS |
| Senses can be removed for intervention | PASS |
| Extinct population remains extinct | PASS |
| Mutations disabled means genome copies are exact | PASS |
| Unphysical/invalid configurations rejected | PASS |
| No food plus metabolism reduces energy | PASS |
| Repeated common-garden evaluation with same seed is deterministic | PASS |
| Full headless CLI run and CSV/NPZ export | PASS |
| Six-seed common-garden experiment outputs data and charts | PASS |
| Independent Experiment 002: 18 seeds × 5 scarcity levels | PASS |
| Synthetic cue-response assay with known genome signs | PASS |
| Effective collapsed genes exactly reproduce raw neural dot products | PASS |
| Mirroring lateral food signals preserves all non-lateral channels | PASS |
| Independent food and crowding sensor ablations | PASS |
| Fixed speed/turn overrides preserve inherited genomes | PASS |
| Experimental motor overrides survive deterministic checkpoint continuation | PASS |
| Scarcity treatments share exact initial conditions before divergence | PASS |
| Empty/extinct training populations not silently resurrected in tests | PASS |
| Deterministic replay reproduces 57 recorded seed-101 CSV rows exactly | PASS |
| Real saved-world snapshot rendering | PASS |
| Reflecting boundary causes correct wall bounce rather than wrap | PASS |
| Food perception at walls is bounded and finite | PASS |
| Resource/capacity patch moves preserve both stocks when no eating/growth | PASS |
| Reflecting world plus moving patches checkpoint-replays exactly | PASS |
| Existing v0.2 checkpoint JSON without new keys still loads | PASS |
| New invalid boundary, shifting interval and negative cost are rejected | PASS |
| New Experiment 003 probe and causal interventions are repeatable | PASS |
| Complete miniaturized Experiment 003 emits expected files and seed contrasts | PASS |
| Headless CLI with combined walls, relocation, costly movement | PASS |
| 8 seeds × 4 training ecologies and 4 novel holdout ecologies | PASS |
| Pygame viewer actually launches and accepts B/M/C controls | **UNVERIFIED**: Pygame package unavailable here; package install blocked by DNS/network |
| Windows .bat actually launches on Windows | **UNVERIFIED**: Linux runner cannot reproduce Windows environment |
| Distribution as a precompiled Windows `.exe` | **NOT PROVIDED** |
| External review by domain scientist | **NOT DONE** |

**The original v0.4 suite had 41 passing tests; v0.5 expands this to 55 tests (see addendum below).** Tests are in `tests/test_simulation.py`, `tests/test_investigation.py`, and `tests/test_environment.py`, and `tests/test_navigation.py`. Run `python -m pytest -q` after extracting. In addition, seed 101 of Experiment 002 was rerun with identical parameters: all five training outcomes, 26 probe outcomes, two controller-response rows and 24 effective-gene rows were identical to the original run.

### Notes

- Deterministic tests are for the same code/runtime environment. Numerical results may vary across NumPy versions.
- Long runs reached the cap of 900 individuals; more tests are needed to quantify any cap-induced evolutionary effect.
- Stored checkpoints include NumPy arrays and serialized JSON RNG state; loading uses `allow_pickle=False`.
- Results are exploratory; six seeds in Experiment 001, 18 in Experiment 002, and eight in Experiment 003 are independent units of replication within their respective experiments.
- The first tested terrain issue is described transparently in `JOURNAL.md`.

### Experiment 003 repeatability check

After the primary eight-seed run, independent execution of seed 401 at exactly the same parameters reproduced **all 41 data rows exactly**: 4 training outcomes, 32 holdout evaluations (including ablations), and 5 controller-phenotype rows. The original and rerun CSV row values matched as strings. The runnable viewer was not tested in this environment because `pygame-ce` was unavailable and installation failed because DNS/network access was disabled.

### Experiment 004 verification

- `python -m pytest -q`: **41 tests passed** (original 30 plus 11 new rare-island, exact restart, intervention, targeted assay, invalid config and cache tests).
- `python -m compileall -q biosphere tests experiments`: **passed**.
- Headless CLI successfully ran `--resource-layout islands --island-count 8 --island-sigma 2.8 --island-peak 10 --move-cost .5` and wrote checkpoint/metrics.
- Full Experiment 004 training: **8 seeds × 3 training ecologies = 24 saved trained worlds** at tick 1,000.
- All 8 independent training seeds completed each of the 3 held-out garden evaluations and the 36-target assay; raw seed-level rows saved.
- A post-hoc speed-matched motor isolation study loaded the **same trained checkpoints**, without retraining.
- `Pygame` is **not available in this runtime**; viewer's `I` hotkey has been code-reviewed and syntax-checked, but the window was not actually launched.
- The Windows launcher is included but untested on Windows in this Linux runtime.
- Seed bootstrap intervals are exploratory and **not confirmatory**. See `EXPERIMENT_004.md` for the method and all limitations.

- Independent clean rerun of seed **701** reproduced **59 original recorded experiment rows exactly** (3 training, 36 holdout, 16 direct-target, 4 controller); no cached replicates or trained checkpoints were reused in this check.

### Experiment 004 QA

- 8 fresh seed pairs × 3 ecological regimes (24 evolved worlds), with matched founders across regimes.
- All 24 trained `.npz` full-state worlds saved and reloadable.
- New automated tests cover sparse-island deterministic terrain, bounded reflecting boundaries, invalid configuration, sparse checkpoint deterministic continuation, matched-garden deterministic interventions, target deterministic probes, per-seed comparison logic, miniaturized 2-seed end-to-end experiment, fixed-speed override behavior, and incompatible seed-cache rejection.
- A subsequent set of 8-seed fixed-speed causal comparisons is preserved in `motor_isolation.csv`, `motor_isolation_targets.csv`, and `motor_isolation_summary.json`.
- Pygame GUI remains **not runtime-verified** in this environment; Windows launcher remains **not Windows-verified**.
- Ruff not installed in this runtime; tests and `compileall` executed.

### v0.4 independent fixed-speed seed replay

Recomputed seed 701 from saved training checkpoints with `python -m biosphere isolate --seed-start 701 --seeds 1 --count 120 --probe-ticks 180 --trained-results results/experiment_004 --output <fresh directory>`. All **32 common-garden rows and 16 target-assay rows** matched the original full-study CSV records exactly, field for field. This checks the fixed-speed intervention evaluation, *not* that training was independently rerun from a bare founder seed.

### v0.5 audit and Experiment 005 verification

- New functional unit tests cover layout at four sizes, terrain coloring, bounded sandbox fertilization, exact checkpoint restart after a manual intervention, aligned per-organism intake when populations change, coordinates on birth/death events, deterministic search/residency probes, genome-neutrality under fixed speed and fixed zero-turn interventions, paired seed-level comparison logic, and a miniature end-to-end Experiment 005 run.
- **55 automated tests passed** (41 pre-existing and 14 additional), `python -m pytest -q`.
- **256 measured assay rows** for 8 training seeds, 4 genome groups, 2 start conditions and 4 motor controls, 75 ticks each. Records in `results/experiment_005/trials.csv` and computed contrasts in `results/experiment_005/summary.json`.
- The enriched event CSV output was run headlessly and its `x`, `y` columns verified. Interventions are stored in JSON checkpoint state and their food/capacity bounds and deterministic replay are tested.
- Source compiled cleanly with `python -m compileall -q biosphere tests experiments`.
- **UNVERIFIED:** actual Pygame application window, all interactive click handling, FPS and layout rendering on Windows. Pygame is not installed here and `pip install pygame-ce` failed due to DNS/network restrictions. The preview PNG is a Pillow mock using authentic saved-world entities, **not** a screenshot of the live viewer.
- Unmodified v0.4 research evidence retained in the release. Original full v0.4 experimental training was **not** rerun here.

### v0.6: trajectory counterfactuals and controls

- Added 11 tests for exact counterfactual equivalences (rich=ghost movement; barren=food-blind movement), initial turn response, misleading cues, deterministic trajectory replay, input-checkpoint nonmutation, valid and invalid starts, and end-to-end small-seed output. Full suite: **66 tests passed**.
- Eight independent archived training seeds, 384 counterfactual trials and four groups of 36 organisms each in each of two starts/six motor-sensory conditions.
- Data in `results/experiment_006/trials.csv`, paired seed-level comparisons in `summary.json`; rendered chart source in `experiments/plot_trajectory.py`.
- Velocity, energy signals, arena geometry, initial positions and headings are identical in matched conditions; differences in cue presence and direction are experimental treatments. No food consumption is simulated.
- Full original evolutionary training was NOT rerun or independently revalidated; v0.6 reuses v0.4 checkpoint genomes. The Pygame viewer and Windows launcher are still **graphically unverified** in this runtime.


### v0.7 Living Observatory and Experiment 007 addendum

- The new headless tests cover 2-row toolbar hit-target geometry at four window sizes, real-second simulation pacing independent of frame count, persistent archive and family relationships, parent-offspring milestones, opt-in and persisted movement histories, deterministic observation neutrality, old v0.6 checkpoint load, full-life ecological assays, seed-level contrasts and end-to-end miniature fitness trials.
- Headless engine profile with 900 initial organisms (reproduction off): ~0.58 ms per simulation tick for 500 ticks. Ordinary growing 180-founder world: ~0.88 ms per tick for 1,200 ticks, 2,702 archived deaths. These timings do not include GUI drawing and are machine-specific.
- Real graphical Pygame window: **UNVERIFIED** in the authoring runtime; attempted `pip install pygame-ce` was blocked by DNS/network. `--smoke-frames`, `--screenshot`, `--qa-report` provide a reproducible GUI QA command for a machine with Pygame installed. See `GRAPHICAL_QA_v0.7.md`.
- Experiment 007: 96 full-life ecologies with births, starvation, death and energy costs; mutation off; normal/missing/mirrored food cues; natural and fixed motor speed. Recorded source CSV and seed-level contrasts in `results/experiment_007`. See `EXPERIMENT_007.md`.
- Existing Experiments 001–006, archived checkpoints, and their prior evidence remain in the release. Old motor outputs and reproduction mechanics are not intentionally modified by the observational instrumentation.

- v0.7 validation count: **76 automated tests** passed, including observation-event milestone persistence and full-experiment contrast computation. Full on-machine Pygame startup remains **unverified**.
