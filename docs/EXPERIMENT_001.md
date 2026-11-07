# Experiment 001 — Can resource-harvesting behavior evolve?

Status: **Completed exploratory analysis** (2026-11-02). Raw data: `results/experiment_6seed/`.

## Research question

Will competing agents with inherited random sensorimotor parameters evolve policies that harvest more food when evaluated on unseen resource landscapes? Will disabling external senses disproportionately hurt evolved agents?

The experiment is **exploratory**, not preregistered. Model calibration occurred before this six-seed run. Avoid attaching a confirmatory statistical claim to these results.

## Experimental design

- **Training:** 6 runs, seeds 1–6, each 1,200 ticks. Start with 180 independently randomized genomes, a 72×54 toroidal landscape, evolution through differential reproduction, and mutation enabled.
- **Standing-variation comparison:** repeat the same initial seeds and landscapes with mutations disabled. Natural selection among founder genotypes is still possible; this is *not* a no-selection control.
- **Genotype sampling:** sample 220 controller genomes each from (a) founders at tick 0, (b) mutating population survivors at tick 1,200, and (c) no-mutation population survivors. Sampling is random with replacement only if fewer than 220 individuals remain. The same sampled genomes are reused for their blinded counterparts.
- **Common garden:** test all six treatments on new terrain seed `11000 + training_seed`, with the **same starting positions, angles, energy and environmental rules**, and 180 ticks of exposure. No reproduction, mutation or old-age death in this evaluation. The same genome can perform differently with and without sensory access.
- **Measurement:** summed food intake divided by 220 original organisms and 180 ticks. This counts zero intake from organisms after their death. Also record survival, mean remaining energy, movement speed and directional correlation. No composite arbitrary 'intelligence' score.
- **Repeated measures:** pair contrasts by training seed. Report mean differences and a percentile nonparametric bootstrap over the 6 paired-seed differences (4,000 resamples). This is exploratory uncertainty, and six seeds cannot reliably establish universal generalization.

## Raw outcomes (food units / organism / tick)

| Treatment | Seed-averaged harvest |
| --- | ---: |
| Founder, senses active | 0.46206 |
| Founder, external senses disabled | 0.42765 |
| Evolved, senses active | 0.58734 |
| Evolved, external senses disabled | 0.52436 |
| Evolution without further mutations, senses active | 0.59210 |
| Evolution without further mutations, senses disabled | 0.52442 |

## Paired comparisons

| Comparison | Mean paired difference | Bootstrap 95% interval | Positive differences |
| --- | ---: | ---: | ---: |
| Evolved − founders | +0.12528 | [+0.11242, +0.14023] | 6/6 |
| Evolved − evolved blinded | +0.06299 | [+0.05096, +0.07693] | 6/6 |
| Founders − founders blinded | +0.03441 | [+0.02563, +0.04353] | 6/6 |
| **Increase in sensory benefit** | **+0.02858** | **[+0.01672, +0.03980]** | **6/6** |
| Mutating evolved − nonmutating evolved | −0.00476 | [−0.01541, +0.00635] | 2/6 |

Full per-seed numbers are recorded in `probe_trials.csv`. The plotted raw outcomes are `common_garden.png`; population dynamics are in `population_dynamics.png`.

## Additional observable phenotype: greater movement speed

Mean speed in the novel common gardens increased from **0.488 world units / tick in founders** to **0.713 in evolved organisms** (approximately **46% faster**). Speed increased in **all six seed pairs**. The sensory-blind evolved group still moved at approximately 0.711, implying much of the speed gain is a general evolved motor tendency rather than a dynamic sensing response. Increased movement may itself help agents reach fresh cells. This is an observable selection response, **not** proof of goal-directed food-patch navigation. A direct stimulus-response assay is still necessary.

## What this does support

1. Within this model and these tested environments, selection produced controllers with **better average resource-harvesting performance** than random founders. Relative gain: `(0.58734/0.46206 − 1) × 100 ≈ 27.1%`.
2. External environmental sensors matter to both ancestors and evolved agents, but **their utility increases after evolution**. This supports adaptation of sensorimotor control—potentially a combination of sensing, movement magnitude and turning under changing resource conditions.
3. Improvement does **not require new mutations within this experiment's 1,200 ticks**: the no-mutation population also improves over founders. This is consistent with selection amplifying advantageous standing genetic variation.
4. The small negative mutating-versus-nonmutating difference, with its interval crossing zero, does **not** establish a mutation cost or benefit.

## What this does NOT show

- It **does not** isolate a specific spatial strategy such as steering toward the left-hand food patch. Direct directional steering was not independently proven by these harvest tests.
- It does not prove intelligence, sentience, agency, animal emotions, cooperation, predation, or open-ended evolutionary complexity.
- Selection can favor generic physical changes, including speed and residence time, not necessarily higher-level decision-making.
- The founder population already contains diverse random controllers, some of which may exploit food gradients by chance. The experiment tests evolutionary improvement, **not the spontaneous invention of perception**.
- Stationary food patches and fixed neural sensors are modeling choices and therefore cannot be described as emergent.
- Effective sample size for treatment contrasts is **six independent evolutionary seeds**, not 220 organisms × 180 ticks. The 220 descendants in one run are related, and treating them as independent statistical replicates would be pseudoreplication.
- No formal multiplicity correction or holdout was applied. The tests and result should be treated as a proof-of-mechanism requiring replication under new environments and model variants.

## Next experiments

1. Run **20–30 additional unseen seeds** with model parameters frozen in advance. Hold out varied land-scale parameters.
2. Conduct **sensor-permutation** trials that preserve each sensor's marginal distribution but scramble its spatial correlation.
3. Probe 25 individually saved lineages to characterize controller responses to isolated controlled input differences, not only total harvest.
4. Repeat with varied carrying-capacity patch sizes, resource regrowth and population density. A robust behavior should transfer beyond a single ecology.
5. Study mutation on longer horizons rather than declaring it useless from short runs.
6. Add flexible program or recurrent neural genome structure to expand behavioral expressivity, **then** ask whether novel interaction networks emerge.

## How to repeat

```bash
python -m biosphere experiment --seeds 6 --steps 1200 --probe-ticks 180 --output results/reproduction
```

Expected numerical agreement requires similar NumPy behavior and the same code revision; a seeded RNG is not a guarantee of strict bitwise equality across library versions and hardware.
