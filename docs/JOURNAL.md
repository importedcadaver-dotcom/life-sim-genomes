# Research journal

### 2026-11-02 — Background and build decision

Reviewed Tierra (digital self-replicating programs), Avida (controlled digital-evolution studies), and Polyworld (neurally controlled organisms in an ecology). Chose a simpler visible sensorimotor model with NumPy simulation and a separate Pygame window. Aim: make claims only about heritable adaptive controller changes, not synthetic cognitive life.

### 2026-11-02 — First code tests: patch saturation failure

Initial small-world terrain generator used 27 random overlapping resource hills regardless of world size. On a 22×18 test map, practically every cell hit the maximum capacity. Different random seeds became indistinguishable, and a test caught it. **Fix:** scale the number of hills to world area. Also changed sensor readings from percentage of maximum capacity to **absolute food stock**; percentages initially gave identical sensor readings everywhere on a fully replenished map, erasing the very gradient being studied. These are architectural corrections, not evolutionary discoveries.

### 2026-11-02 — Pilot: repeated tests

At 900 training ticks over seeds 1–3, evolved controllers outperformed initial founders in novel landscapes. However, no-mutation groups did better than mutating groups in all three of these short pilot runs. **Action:** explicitly include no-mutation controls and founder-blind trials before the primary six-seed exploratory comparison. Do not assert beneficial mutation just because a system evolves.

### 2026-11-02 — Completed Experiment 001

Ran 6 seeds × 1,200 training ticks, with six matched control treatments evaluated for 180 ticks in fresh landscapes. Average evolved harvest = 0.5873; founder = 0.4621. Removing evolved environmental senses reduced performance to 0.5244. Evolution increased sensor benefit by +0.0286 (paired bootstrap 95% interval +0.0167 to +0.0398). Mutation effect indistinguishable from zero at this scale. An additional observation: average motor speed was 0.488 for founders and 0.713 for evolved genomes across matched common gardens. This supports a simple behavioral interpretation of increased resource access through exploration, not demonstrated food-directed turning. Full methods: `EXPERIMENT_001.md`.

**Interpretation:** selection improved heritable controller behavior in a way useful for collecting resources. More evidence is needed to isolate the strategy; no cooperation or complex intelligence can be inferred.

### 2026-11-02 — Engineering validation

Added tests for deterministic seeding, resource allocation under crowding, reproduction lineage integrity, exact checkpoint continuation, blinding, extinction, mutation-disabled inheritance, invalid config, no-food energy decline, population cap, common-garden repeatability, and saved-observable recovery. Built an actual-state plotting utility. Viewer logic is written and syntax-checked, but **cannot be runtime-smoke-tested here** because Pygame isn't installed and package installation could not reach its repository.

### Open findings and failed expectations

- It was premature to expect beneficial new mutations to reliably outperform standing-variation selection in ~1,200 steps. At this horizon they did not.
- Improvement in total food collection does not tell us *how* organisms move. The next investigation must measure the stimulus-response controller directly and use richer ablations.
- The first pilot showed that simple resource-rich ecologies can quickly reach the simulation's 900-organism cap. This makes demographic selection and crowding important confounders worth manipulating.
- Despite thousands of births, the prototype has not demonstrated communication, distinct social roles or emergent predators. We will not add labels to ordinary movement to make it sound more impressive.

### 2026-11-02 — Experiment 002: mechanism tests correct an overinterpretation

Extended the simulator with reversible *experimental* sensory/motor overrides; added a static artificial-cue assay and effective-gene weight analysis (necessary because food-contrast inputs are linearly redundant). Ran **18 entirely new training seeds**, each under five regrowth conditions for 1,200 ticks; evaluated at 240 ticks on unseen terrain with 0.030/0.006 regrowth. All outcomes are in `results/experiment_002/` and methods are in `EXPERIMENT_002.md`.

**Reproducible improvement**: abundance-trained evolved genomes harvested 0.61958 compared with 0.47610 founders (+30.1%). They also increased standardized speed from 0.4726 to 0.6676, driven in part by larger inherited baseline/energy speed weights. Their motor turn response to synthetic directional cues increased in 16 of 18 seed pairs.

**Surprising negative finding**: disabling steering made evolved genomes harvest *more* (0.70574 versus 0.61958). Therefore we cannot call the evolved responses a successful food-targeting behavior. This is a falsification of the strong navigation interpretation, though not of the observed adaptive harvesting. Mirrored spatial food cues had little effect relative to complete food-sensor removal. Generic locomotor changes dominate.

**Scarcity**: slow replenishment sharply lowered long-run population. All 18 worlds at 0.001 regrowth went extinct, 8/18 at 0.003 went extinct, and all survived at 0.006. Training at 0.006 produced genomes that harvested better than abundance-trained genomes in both scarce and abundant probes; this is general transfer, not a demonstrated specialist tradeoff.

**Next:** test alternative boundary geometries and dynamic resources before broadening to more complicated neural genomes. Such a study should isolate whether rapid straight-line motion is a toroidal-map artifact.

### 2026-11-02 — Experiment 003: geometry, habitat motion, and motor costs

Preserved the inherited 16-weight controller and modified only environmental constraints: wrap versus reflecting edges, seeded relocation of carrying capacity plus stocked food every 35 ticks, and 11.5-fold higher movement-energy expenditure. Eight new training seeds (401–408) independently evolved in each of four worlds for 900 ticks; 32 resulting populations were then evaluated in 160-step holdout gardens across all four ecologies.

**Replication:** All four ecologies independently selected for better food harvesting than founders (positive in 8/8 matched training seeds per ecology). Evolution under moving food patches also produced controllers that generalize: the shifting-trained group harvested 0.6319 in the original stationary holdout, versus 0.5974 for wrap-trained. But this result is **not** a demonstrated navigation policy.

**Unexpected negative result:** Suppressing all turning still increased harvest for wrap-trained genomes in *all four* holdout ecologies, including reflecting walls (mean +0.0785 harvest) and relocated food patches (mean +0.0523). The hypothesis that removing wraparound would make normal turning superior was not supported.

**Cost hypothesis remains uncertain:** High movement costs selected controllers with lower standardized speed (0.5540 versus 0.6432 for wrap-trained genomes) and a smaller training population (400 mean versus capped 900), but a direct matched costly-ecology net-energy comparison was inconclusive. Controlled sparse-resource tasks should come before claiming food-directed behavior.

**Engineering:** Added reflecting boundary physics and reflected food sampling, seeded food/capacity relocation, exact checkpoint continuation including new state, live viewer B/M/C toggles, CLI switches, and nine additional automated tests. Full results in `EXPERIMENT_003.md` and `results/experiment_003/`.

### 2026-11-02 — Experiment 004: sparse resource islands expose beneficial steering

Constructed a second resource generator with seeded, spatially separated Gaussian islands, tiny background capacity and two progressively expensive movement regimes. Preserved the exact inherited 16-weight neural controller; supplied no navigation routine.

The initial multi-seed batch was interrupted by an execution limit, after which we implemented cached complete per-seed replicates and reused deterministic full checkpoints; **partial seed output is not counted as completed evidence**. Finished seeds 701–708 (24 evolved worlds; 180-step paired holdouts and a separate 36-target assay). Island-trained controllers harvested more than founders in sparse worlds, but surprising negative result: dense-trained controllers harvested still more. Thus a specialized-island adaptation claim was falsified in this setup.

**First positive steering result:** turning **is useful** on sparse worlds, unlike earlier smooth-hill worlds. Normal island-trained controls harvested 0.3485 vs 0.2792 with forced zero turning (8/8 positive). With forward speed fixed identically at 0.60, normal turning still outperformed zero turning (0.3428 vs 0.2862; 8/8 positive). Fixed-speed food-blind controls did substantially worse, supporting a real sensory contribution to turning.

**But not precision navigation:** turning agents entered the cores of isolated targets *less often* than straight-line controls (30.6% vs 58.3% for natural motor outputs; 27.4% vs 65.3% at clamped speed). Steering may support localized exploitation of resource halos without maximizing target hits. Mirroring lateral cues at fixed speed did not produce a clear reduction for island-trained genomes. We should not label this experiment proof of purposeful food-directed navigation.

Added island terrain checks, fixed-speed motor interventions, reproducible per-seed caching, direct target challenge tests, a repeatable standalone motor follow-up, viewer `I` key, CLI flags and documentation. All results and confidence intervals in `EXPERIMENT_004.md`.

### 2026-11-02 — Experiment 004: first measurable steering benefit under sparse food

Created separated Gaussian resource islands against a nearly foodless background; varied movement expense; trained 8 fresh seeds in three ecologies for 1,000 ticks, preserving all state checkpoints. Built matched 36-target fixed-start acquisition tests and performed a second, fixed-speed motor-isolation comparison.

**Useful turning emerges under a new condition:** in new sparse worlds, island-evolved genomes collect 0.34281 harvest units per founding organism and tick with their normal steering but 0.28619 when turning is suppressed, **both at speed 0.60**. The gain was positive in 8/8 independent seeds; bootstrap paired interval [0.03460, 0.07690]. Costly-island-trained genomes show an even larger fixed-speed normal-turn advantage of +0.10157 (positive in 8/8).

**But target approach does not emerge:** on isolated cores, fixed-speed zero-turn genomes hit a core much more often (0.6528 versus 0.2743 for island-evolved normal-turn). Higher ecosystem harvest and higher chance of reaching a food island are different outcomes. Mirror-direction experiments show relatively small effects, so accurate food-oriented direction finding is not demonstrated.

**Unfavorable specialization evidence:** dense-environment-evolved brains outperform island-trained brains in the island holdout: 0.3948 versus 0.3485. Stronger resource pressure did not produce a superior sparse-habitat specialist in this experiment. Training density and capped rich-world populations are confounds.

All numbers are exploratory and use **8 independent seeds**, not 288 target organisms as the statistical sample size. See `EXPERIMENT_004.md` and `results/experiment_004/` for precise interventions and limitations.

## 2026-11-02 — Experiment 005 and v0.5 observatory audit

Inspecting the v0.4 visual artifact showed a legible experiment plot but a weak spectator interface: organism dots were difficult to identify, the default pace was 120 simulation steps/second, interacting required keyboard memorization, and no persistent attention was drawn to real life events. I rebuilt the source viewer as an observational control room with selected-organism telemetry, follow camera, zoom, trails, event markers, clickable transport controls and a quarantine-labeled sandbox nutrient brush. A separate Pillow preview is derived from actual checkpoint state; Pygame runtime is **not** verified in this environment. During event-tracking changes I detected and repaired a CSV export break caused by additional x/y event fields.

Experiment 005 reused seed 701–708 v0.4 trained genomes (no retraining). 256 controlled trials explicitly distinguished searching for a resource core from remaining in one. Evolved costly-island controllers entered a core less often than straight movers (33.7% vs 74.3%) but remained in cores much longer once placed inside (80.9% vs 14.7%). Food-blind controllers retained 83.0% core residency, showing the high occupancy need not depend on food-specific cues. This supports evolved local retention/turning as a mechanism, **not** known directed navigation. Next experiment should inspect unconstrained turning radius and bare-patch controls.

### 2026-11-02 — Experiment 006: food-cue effects versus persistent turning

Motor-only trajectory comparisons confirmed that the same evolved controllers move differently with rich, barren or spatially displaced food-sensory signals. At a fixed 0.60 movement speed, costly-island-trained controllers entered near food cores 37.2% of the time with true cues but 9.4% without any cues. The correspondence of `rich` and `ghost` trajectories, and `barren` and `food_blind` trajectories, was exactly as constructed.

Crucial counterevidence: zero-turn controllers still enter more cores in this specific geometry, and barren-cue controllers exhibit strong local loops when initialized inside a patch. The apparent evolved behavior combines generic localized motor bias with some environmentally conditional response; it is not a reliable long-distance food navigator. See `EXPERIMENT_006.md` and the full saved seed rows for controls, provenance and caveats.


## Experiment 007 — Life-cycle sensory interventions (v0.7)

We rebuilt the observer with persistent lifetimes and retained the original motor policy. In 96 complete ecological tests, expensive-island evolved controllers had substantially higher direct-founding reproduction with accurate food cues than in food-blind counterfactuals (eight of eight seed pairs), even at fixed speed. Evolved controllers were more dependent on food cues than founders, but final population advantage was inconclusive and mirroring lateral food cues changed outcomes much less. The negative result matters: this is not yet reliable target-directed navigation or proof of intelligence. A graphical-runtime QA gap remains; tests verify only headless logic and layout calculations.
