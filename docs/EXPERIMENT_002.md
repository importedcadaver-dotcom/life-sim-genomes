# Experiment 002 — What evolved, and what happens when food becomes scarce?

**Analysis status:** Exploratory follow-up to Experiment 001. Design and interventions specified before examining the complete Experiment 002 output. Earlier pilot results and the first several scarcity census outcomes were seen while the run was in progress; this is **not** preregistration and there was no blind analysis.

## Questions

1. Does the advantage seen in six initial seeds transfer to 18 *new* evolutionary training seeds (101–118), without changing core default model parameters?
2. Does the advantage remain when speed is held constant in both founder and evolved agents? What remains if agents cannot turn?
3. Does reversing spatial left/right food cues hurt evolved agents more than simply suppressing those signals? Is there a detectable direct directional steering response to side-specific food signals in the genomes?
4. Under progressively reduced resource replenishment, is the ecology viable? Do genomes selected during scarcity collect more food when evaluated at low regrowth than genomes selected during abundance?

## Design

- Train matched initial worlds separately at food-regrowth factors **0.030, 0.012, 0.006, 0.003 and 0.001**, all for 1,200 ticks, on each of 18 independent initial seeds. Each seed uses identical initial terrain, founding genomes and starting organisms across its five ecology treatments. Food regrowth rate is the **only ecological parameter** changed between training conditions; regeneration is `rate × (capacity − stock)` each tick.
- Evaluate sampled genomes in disjoint, novel worlds (`seed + 31000`) for 240 ticks with **no further births or mutations**, a fixed starting energy of 55, and a lifespan longer than the probe. Evaluations occur in both 0.030 and 0.006 replenishment. Agent placement, headings and terrain are matched within every genotype comparison at a fixed probe-regrowth setting.
- Sample **180 genomes per survivor population**. Populations that died out remain extinct. Their missing genotypes are recorded as an explicit empty sample / missing evaluation, not replaced by ancestor genomes and not counted as zero-performing controllers.
- Food intake per original organism per probe tick is the primary performance metric. Additional outcomes are training population, births, starvation deaths, surviving fraction in probe, movement speed, and static controller response.
- For causal analysis of the abundance-trained groups: (a) compare full founder vs evolved, (b) fix both speeds to 0.60, (c) force turns to zero, (d) remove food sensing while retaining crowd sensing, (e) mirror food lateral cues while retaining their magnitudes, and (f) remove crowding sensing. Every intervention is an experimental override, **not** a normal-life adaptation.
- For the static directional assay, provide the same synthetic sensory context to each genome, except lateral food levels are swapped. Compute `(turn when positive-angle side is richer − turn when negative-angle side is richer)/2`; a positive score means turning *toward* the richer side under this convention. No movement, foraging or evolutionary success is directly measured by this assay.
- Aggregate by independent **training seed**. Paired differences use a simple percentile bootstrap of seed-level differences. Those intervals describe sampling uncertainty within this synthetic simulator, not uncertainty about actual biology or other artificial-life worlds.

## Identifiability limitations

- Fixed speed and no steering are interventions that can change energy use and locomotion together, not magically isolate a universal natural behavior.
- Simply zeroing food sensors changes both their environmental information and their average tonic input, so it does not by itself prove navigation. The cue mirroring and synthetic motor-response assays reduce but do not completely eliminate this ambiguity.
- Contrasts 4 and 5 are deterministic functions of food channels 1–3. **Raw gene weights are not individually identifiable.** We therefore also report mathematically combined *effective* weights for ahead/left/right, energy, crowd and bias.
- The default population cap of 900 can constrain demographic response under abundance. At low regrowth, extinction may result from energetic math and crowding regardless of neural controller complexity.
- There is no communication or attack mechanism. Neither cooperation nor predator–prey evolution can emerge in this specific model; those claims are outside the scope of Experiment 002.
- The simulator remains a fixed-architecture 16-parameter brain system, not an open-ended computer-code evolver or demonstration of spontaneous biological life.

## Reproduction

Run the full investigation (will create CSV, JSON, PNG charts and selected NPZ checkpoints):

```bash
python -m biosphere investigate --seed-start 101 --seeds 18 --steps 1200 --probe-ticks 240 --output results/experiment_002
```

All source code for the run is in `biosphere/investigation.py`. Tests of experimental interventions are in `tests/test_investigation.py`.

## Results

Completed outcomes and interpretations are appended below after inspecting the actual files.

## Completed outcomes (18 fresh seeds, 2026-11-02 Pacific)

### Generalization: evolutionary harvesting improvement repeated

In a new abundance-regrowth (`0.030`) garden, sampled founder genomes harvested **0.47610** units per starting organism per tick, versus **0.61958** for evolved genomes (**+30.1%**, paired difference **+0.14348**, percentile bootstrap 95% interval **[+0.12953, +0.15729]**; **18/18** independent evolutionary seeds improved). At low-regrowth (`0.006`) probe conditions, mean harvest was **0.26156** founders vs **0.31550** evolved (**+0.05394**, bootstrap interval **[+0.04659, +0.06129]**, **18/18** seeds improved).

This replicates the *limited* v0.1 finding of adaptive harvesting on new seed IDs, with model architecture unchanged. It does not prove a general-purpose food-navigation or intelligence strategy.

### Mechanism: faster movement is important; steering is not yet beneficial

The standardized synthetic-cue motor assay found that evolved genomes increased their neutral-input speed from **0.47259** to **0.66762**, mean change **+0.19503** (18/18 seeds higher). The effective gene-weight analysis found large mean increases in the speed motor's bias weight (**+0.656**) and energy-fraction weight (**+0.482**); raw contrast weights are redundant, so we report mathematically combined effective food weights as well. These are specific, inherited controller changes associated with selection; their independent causal effects have not been completely identified.

A direct synthetic left-vs-right cue test found the average lateral directional response moved from **−0.00058** radians/tick in founders to **+0.03065** in evolved controllers; paired difference **+0.03124**, interval **[+0.01455,+0.04852]**, positive in **16/18** seeds. The network can thus exhibit stronger cue-correlated turning, although this assay does **not** test successful navigation.

Harvest interventions in the abundant novel gardens:

| Intervention | Mean harvest | Paired difference, where relevant |
| --- | ---: | ---: |
| Founders, normal | 0.47610 | — |
| Evolved, normal | 0.61958 | Evolved − founders: **+0.14348** |
| Founders, fixed speed 0.60 | 0.54840 | — |
| Evolved, fixed speed 0.60 | 0.58286 | Evolved − founders with speed matched: **+0.03446**, 17/18 seeds positive |
| Founders, **zero steering** | 0.60415 | — |
| Evolved, **zero steering** | **0.70574** | Evolved − its own normal steering: **+0.08615**, 17/18 seeds improved by disabling turning |
| Evolved, food sensors zeroed | 0.53923 | Normal − blind: **+0.08035** |
| Evolved, left/right food mirror | 0.61044 | Normal − mirrored: **+0.00914** |
| Evolved, crowding sensor zeroed | 0.62175 | Normal − crowd-blind: **−0.00217** |

**Critical corrective interpretation:** An earlier interpretation could have called the stronger lateral cue response successful evolved navigation. That would not withstand these controls. In fact, removing steering produces a substantial improvement in harvesting. For this map, straight-line traversal of the torus can outperform local motor turning. Zeroing food sensors is also a tonic-input change, so its larger effect cannot be assumed to arise entirely from loss of useful spatial information. Mirroring food direction has only a *small* average effect in the abundant probe and an interval overlapping zero in the scarce probe. The data favor selection of effective locomotion and sensory drive, **not a demonstrated food-targeting navigation policy**.

The result remains interesting: selection changed the inherited controller, and those changes measurably improved fitness-related harvesting, despite a physically simple environment.

### Ecological threshold under food-regrowth scarcity

At the end of 1,200 training ticks:

| Regrowth rate | Mean final population | Populations extinct / 18 | Mean cumulative starvation deaths |
| ---: | ---: | ---: | ---: |
| 0.030 | 895.6 | 0 | 23.9 |
| 0.012 | 444.1 | 0 | 68.4 |
| 0.006 | 236.9 | 0 | 153.9 |
| 0.003 | 47.8 | 8 | 290.8 |
| 0.001 | 0.0 | 18 | 413.0 |

Scarcity here means **slower replenishment**, not an abrupt reduction of the initial food landscape. This is a finite-time extinction boundary, not a mathematically established critical point; the results depend on fixed parameters, ecology size, and initial population density. Populations that survived 1,200 ticks are not guaranteed to survive indefinitely.

Genomes trained at 0.006 rather than 0.030 harvested **+0.04485** units/organism/tick in fresh scarce (`0.006`) probe worlds, a paired bootstrap interval **[+0.03509, +0.05426]**, with **18/18** replicates positive. Importantly, those scarcity-trained genomes *also* did better when evaluated at abundant (`0.030`) regrowth (**+0.08747**, interval **[+0.06381,+0.10982]**, 17/18 positive). This is therefore **not evidence of a scarcity-specialist tradeoff**, only a training-environment effect that transfers to both measured probe conditions. Different population caps, density and selection intensities could contribute; future experiments should isolate these explanations.

At 0.003, ten populations survived, eight were extinct and therefore had no candidate genomes for the common-garden test. Mean performance across *surviving-only* 0.003 populations is selection-biased and must not be treated as comparable to the full 18-seed groups without an explicit missing-data model. At 0.001, every population went extinct, so there are no learned controller probes to report.

### Independent replication and statistical scope

Each point in a comparative interval is **one population-level training seed difference**; we do not pretend that the related individual organisms are independent replicates. Results are exploratory. The experiment includes several related treatment contrasts and no multiplicity adjustment. The bootstrap interval is conditional on model rules and seed distribution; it is not a proof of universal performance.

**Overall finding:** We observed selection for faster locomotion, stronger but not necessarily beneficial sensory turn responses, a reproducible resource-harvesting advantage, and a steep population response to reduced regeneration. We did **not** observe successful spatial steering, social behavior, emergent communication, or evolution beyond the fixed brain architecture.

## Next mechanistic hypothesis

The most useful next scientific question is why high-speed, low-turn agents perform so well: does the toroidal map and constant environment create a simple sweeping bias? Test (a) nonperiodic boundaries, (b) mobile/regenerating food hotspots, (c) movement costs, (d) population density uncapped from 900, and (e) isolated speed/energy motor transplant experiments. Run these as separate paired trials; do not quietly change all physics at once.
