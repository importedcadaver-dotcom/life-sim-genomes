# Experiment 003 — Does ecology shape movement strategies?

Date: 2026-11-02 (US Pacific)  
Code: `biosphere/environment.py`, `biosphere/simulation.py`  
Data: `results/experiment_003/`  
Status: **Completed exploratory simulation; not a preregistered confirmatory study**

## Question

Experiment 002 showed that evolved organisms collect more food but can collect **even more** when their steering is overridden to zero. We suspected a world with wraparound boundaries might accidentally reward motion in straight lines. We therefore compared reflection off walls, relocations of food patches, and an increased energy penalty for motion.

The scientific literature emphasizes that effective sensorimotor behavior depends on both internal controller design and environmental dynamics. See [Rañó (2012)](https://pubmed.ncbi.nlm.nih.gov/22585337/) on surprising trajectories of minimal Braitenberg-type agents and [Miras et al. (2020), Environmental influences on evolvable robots](https://pmc.ncbi.nlm.nih.gov/articles/PMC7259730/) for the problem of identifying environmentally shaped controller traits.

## Engine modifications

The **same existing eight-input/two-output linear genome** was retained. No hard-coded food seeking, obstacle avoidance, or social behavior was added.

1. **Wrap (control):** original 72 × 54 toroidal world; crossing an edge re-enters the opposite edge.
2. **Reflect:** a specular boundary flips the direction of motion on impact, and the perceived sample point beyond a wall is geometrically mirrored. Terrain capacity generation is intentionally kept the same as wrap; walls change locomotion/sensing, not the initial resources.
3. **Shifting:** once per 35 ticks, the entire resource-capacity map *and* its stocked food values translate together by a seeded displacement. This conserves total food **at the instant of translation**. It is a deliberately abrupt relocation, not a realistic gradual seasonal migration.
4. **Costly:** increases energy expenditure per unit of movement from 0.065 to 0.75, leaving food physics otherwise unchanged.

### Test design

- **Eight independent evolutionary training seeds:** 401–408, previously unused.
- **Four matched training conditions per seed:** 8 × 4 = **32 trained worlds**, plus founder controls, for 900 ticks.
- **Identical initial genomes, positions, energies and carrying-capacity landscape within each matched seed**; subsequent birth RNG streams legitimately diverge across conditions.
- **All 5 controller groups** (founders and four evolved groups) evaluated in **each of 4 holdout environments**, with new world seed `(training seed + 54,000)`.
- **Common-garden length:** 160 ticks, 160 genomes sampled per group, reproduction disabled, identical random placement/landscape within a paired test.
- **Motor ablations:** for wrap-trained genomes in every holdout environment, overwrite turn with zero, fix speed at 0.60, or remove food sensors. Steering was not replaced by a goal-directed controller.
- **Unit of statistical replication:** evolutionary training seed, **n=8**, not 160 individual organisms or repeated probe steps.
- **Uncertainty:** percentile bootstrap from 4,000 resamples of the eight within-seed differences; intervals reflect this simplified simulation protocol, not general ecological truth.
- Primary readout is food harvested per *starting* organism per simulation tick, with deaths contributing zero thereafter. Other reported values are inherited controller speed under standard synthetic sensory cues, population survival, and net retained energy.

## Results

### Training population (at tick 900)

| World | Average living organisms | Extinction events |
|---|---:|---:|
| Wrap | 900.0 (reached imposed cap) | 0/8 |
| Reflect | 900.0 (reached imposed cap) | 0/8 |
| Shifting | 900.0 (reached imposed cap) | 0/8 |
| Costly | 400.1 | 0/8 |

The population cap of 900 hides differences among highly successful populations; reaching it is **not** equivalent to a measured evolutionary fitness advantage.

### Held-out performance

Rows are the source where genomes were selected; columns are where those genomes were evaluated.

| Origin → / Test ↓ | Wrap test | Reflect test | Shifting test | Costly test |
|---|---:|---:|---:|---:|
| Founders | 0.4599 | 0.4599 | 0.5172 | 0.4782 |
| Evolved on wrap | 0.5974 | 0.5961 | 0.6298 | 0.6248 |
| Evolved on reflect | 0.5932 | 0.5900 | 0.6311 | 0.6163 |
| Evolved on shifting | **0.6319** | **0.6296** | **0.6536** | **0.6616** |
| Evolved on costly | 0.5708 | 0.5640 | 0.5910 | 0.5938 |

Values in food units per initial organism per step. Figures rounded; the CSVs hold full precision.

### Paired differences (bootstrap 95% intervals)

| Contrast | Mean | 95% interval | Positive pairs |
|---|---:|---:|---:|
| Wrap-evolved − founders, tested on wrap | +0.1375 | [+0.1214, +0.1544] | 8/8 |
| Reflect-evolved − founders, tested on reflect | +0.1302 | [+0.1063, +0.1575] | 8/8 |
| Shift-evolved − founders, tested on shifting | +0.1364 | [+0.1207, +0.1504] | 8/8 |
| Costly-evolved − founders, tested on costly (food harvest) | +0.1156 | [+0.0805, +0.1504] | 8/8 |
| Reflect-evolved − wrap-evolved, evaluated with walls | −0.0061 | [−0.0250, +0.0113] | 5/8 |
| Shift-evolved − wrap-evolved, evaluated with shifting food | +0.0238 | [+0.0092, +0.0361] | 7/8 |
| Costly-evolved − wrap-evolved, costly net energy yield | +0.0188 | [−0.0270, +0.0681] | 4/8 |
| Zero-turn − normal wrap-evolved steering, evaluated on wrap | **+0.0808** | [+0.0615, +0.0970] | 8/8 |
| Zero-turn − normal wrap-evolved steering, evaluated with walls | **+0.0785** | [+0.0605, +0.0942] | 8/8 |
| Zero-turn − normal wrap-evolved steering, evaluated with shifting food | **+0.0523** | [+0.0431, +0.0644] | 8/8 |
| Zero-turn − normal wrap-evolved steering, evaluated with costly motion | **+0.0520** | [+0.0320, +0.0692] | 8/8 |

### Evolved controller phenotype

Mean baseline speed on a neutral standardized input: founder **0.4711**, wrap-evolved **0.6432**, reflect-evolved **0.6406**, shifting-evolved **0.6615**, costly-evolved **0.5540**. Increased movement costs apparently select against maximum speed in this setup, but controller weights were not experimentally decomposed in this phase.

## Interpretation

**Supported:** inherited sensorimotor controllers change consistently under selection. Repeated selection in the relocating-food world produced genomes that harvest more than wrap-trained genomes in a relocating world, and they also generalized to multiple other holdouts. It is a candidate **generalist advantage**, not evidence of a shifting-only specialist strategy.

**Not supported:** the prediction that replacing a torus with reflecting boundaries would make evolved steering more useful. With zero steering, wrap-trained agents still harvested more in **all four** holdout ecologies. Also, reflect-trained agents did not reliably outperform wrap-trained agents in reflecting worlds.

**Not supported:** cost-trained controllers outperforming wrap-trained controllers in *net energy yield* on costly holdouts; the eight-seed interval overlaps zero.

**Mechanistic uncertainty:** 'zero turn' is a surgical behavioral intervention. It does not reveal why the inherited turning weights changed; a hardcoded linear controller with short-range sensors may simply be incapable of efficient turning under the model's sampling geometry. Food capacity can be so ample that turning toward food is rarely rewarded. Larger worlds, sparse discrete patches, gradients with directional continuity, or more powerful recurrent controllers may change this.

This experiment **did not** discover cooperation, communication, intelligent navigation, or open-ended innovation. It is a carefully measured artificial-evolution exercise with abundant model-induced constraints.

## Reproducibility

```bash
python -m biosphere environment --seed-start 401 --seeds 8 --steps 900 --probe-ticks 160 --count 160 --output results/reproduction_003
python -m pytest -q
```

All outputs are in `results/experiment_003/`: `summary.json`, `training.csv`, `holdout.csv`, `controller.csv`, 32 exact-loadable world checkpoints, `transfer_matrix.png`, `zero_turn_by_ecology.png`, `controller_speed.png`, and direct-world snapshots. See `README.md` for Windows instructions.

### Next genuine research challenge

Create a **controlled sparse-target task** with varied patch lifetimes and an arena size large enough that random travel is meaningfully expensive, then use a paired evolutionary training and direct stimulus-following test. Avoid manually giving the organisms a steer-toward-food rule. Determine whether their inherited controllers learn useful steering at all, or whether this genome architecture must be revised.
