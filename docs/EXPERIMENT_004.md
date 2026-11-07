# Experiment 004 — When does evolved turning improve sparse-world harvesting?

**Status:** completed exploratory experiment and a follow-on fixed-speed causal probe. 2026-11-02.

## Question and hypotheses

Earlier experiments found evolution of faster, more effective locomotion in rich environments, but agents forced to move in straight lines often harvested *more* than normally steering agents. Experiment 004 changes only the **ecology** and adds independent evaluation interventions. Can evolution exploit directional sensing when food is rare and spatially clustered? Can we distinguish a useful turning controller from merely fast movement or lucky island encounters?

- **H1 — Sparse-world adaptation:** selection in isolated-food landscapes improves harvesting over founder genomes under matched new sparse conditions.
- **H2 — Steering utility:** removing turning reduces harvest for evolved sparse-world genomes, including when all agents' speeds are experimentally held constant.
- **H3 — Directed target acquisition:** turning improves the probability that agents starting outside a particular food-rich region reach a food-core radius.
- **H4 — Local ecological specialization:** genomes evolved in sparse worlds outperform genomes evolved in the original rich world when both are tested in the sparse world.

These are *exploratory*, post-development hypotheses, not a preregistered test. None imply cognition or true environmental understanding.

## Implementation

- Reused the original inherited **2 × 8 = 16-weight** controller: the engine does not encode a seek-food rule or a reward function tied to directional navigation.
- Added `Config.resource_layout="islands"`: a reproducible array of narrow resource islands against a nearly empty resource background. Default island count = 8, Gaussian island sigma = 2.8 cells and peak carrying capacity = 10.0.
- Trained each seed in three worlds for **1,000 simulation ticks**: default food-rich world (`dense`), island world with `move_cost=0.20` (`islands`), and island world with `move_cost=0.50` (`islands_costly`). The baseline engine uses `move_cost=0.065`. All share matched *founding organisms*; the ecological maps differ by treatment.
- Eight independent seeds **701–708** per treatment: **24 separately evolved populations**. A founding `founder` comparison was sampled separately, but was not trained. This is *not* 1,000 biological generations: ticks are model update steps, and observed maximum generation depth is far smaller.
- Sampled 120 surviving genomes for each training group and each seed. Evaluated them in reproduction-free, mutation-free, **180-tick common gardens** with unseen world seed and identical ecological settings for each condition within a replicate. Harvest is total food collected divided by original organism count and number of ticks; death therefore cannot inflate the denominator.
- Experiments first compared normal motion with steering disabled, food sensors blinded and left/right food cues mirrored. A second set of interventions **held translational speed fixed at 0.60 for *every* condition**, independently modifying turning or the food sensors. This eliminates evolved speed differences as an explanation for fixed-speed *between-intervention* contrasts.
- An independent **55-tick target assay** placed 36 isolated agents per seed at equal radial distance (6.15 cells) from 36 marked food islands, with random headings. Each intervention uses matched genomes, starting positions, headings and resource map. Outcomes: ever-entered-radius-3 `hit_fraction`, fraction of organism-ticks within radius 3, and harvested food. Targets are not disclosed to organisms.
- For population-level comparisons, **seed, not organism or target, is the replication unit**. Means and paired bootstrap intervals in the JSON summaries use eight independent training seeds. Intervals are descriptive; the methods were chosen after earlier experimental feedback.

## Key results

### Training populations (end of tick 1,000)

| Training condition | Mean surviving population | Extinctions (out of 8) |
| --- | ---: | ---: |
| Rich/default | 900.0 (at cap) | 0 |
| Sparse islands | 424.1 | 0 |
| Sparse islands, costly motion | 302.4 | 0 |

The sparse landscape retained populations but created stronger demographic pressure than the default. Populations reach the hard maximum of 900 in the rich environment, so cap/crowding are possible confounds in cross-ecology comparisons.

### Generalization: normal motion (unseen common gardens)

| Evolved group | Rich evaluation | Sparse evaluation | Sparse + costly evaluation |
| --- | ---: | ---: | ---: |
| Founders | 0.5131 | 0.2993 | 0.3064 |
| Rich-trained | **0.6554** | **0.3948** | **0.4058** |
| Sparse-trained | 0.5839 | 0.3485 | 0.3582 |
| Sparse-costly-trained | 0.5378 | 0.3600 | 0.3740 |

Values are **mean harvest / starting organism / evaluation tick**, averaged across eight independently trained populations. Sparse-trained versus founders in sparse evaluation: **+0.04922** (paired bootstrap 95% interval **[+0.03699,+0.06167]**, positive in 8/8 seeds). However, sparse-trained versus rich-trained in sparse evaluation: **−0.04624** (interval **[−0.07233,−0.02278]**, positive in 0/8 seeds). **H1 supported in this narrow test; H4 contradicted.** More harvesting by rich-trained genomes is consistent with generally effective locomotion and selection intensity, not ecology-specific optimization.

### Fixed-speed steering intervention: the most important result

| Evolved genomes / evaluation ecology | Normal turning at speed 0.60 | Zero turning at speed 0.60 | Food-blind at speed 0.60 | Left/right cues mirrored at speed 0.60 |
| --- | ---: | ---: | ---: | ---: |
| Sparse-trained / sparse | **0.34281** | 0.28619 | 0.21722 | 0.33249 |
| Costly-sparse-trained / costly sparse | **0.38482** | 0.28325 | 0.23870 | 0.36801 |

For sparse-trained organisms in sparse gardens, **normal − zero-turn = +0.05662** harvest units / starting organism / tick, with paired seed-bootstrap 95% interval **[+0.03460, +0.07690]**, positive in **8/8** seeds. For costly-sparse-trained organisms in costly sparse gardens, **+0.10157**, interval **[+0.07582,+0.12999]**, positive in **8/8** seeds. **H2 supported** for this fixed-speed ecological metric.

Food blinding is more damaging: sparse-trained normal − blind **+0.12559** in sparse gardens, positive in 8/8 seeds. However, **blinding removes all food input channels**, not just orientation; it cannot alone establish that the animal is *turning toward* food. Mirroring cues yields only small changes (+0.01032 in sparse and +0.01681 in costly sparse), with the sparse comparison interval including zero. Those contrasts make **precise compass-like food guidance inconclusive**.

### Target acquisition reveals an important contradiction

In the fixed-speed target assay, sparse-trained genomes achieved:

| Mode | Ever hit any food core | Fraction of agent-ticks in core | Harvest / starting agent / tick |
| --- | ---: | ---: | ---: |
| Normal turn, fixed speed | 0.2743 | 0.1095 | 0.5159 |
| Zero turn, fixed speed | **0.6528** | 0.1061 | 0.4872 |
| Food-blind, fixed speed | 0.1111 | 0.0213 | 0.3500 |
| Mirrored food cues, fixed speed | 0.2569 | 0.0958 | 0.4894 |

Normal − zero-turn core-hit fraction **−0.37847** (paired seed-bootstrap 95% interval **[−0.48264,−0.25347]**, positive in 0/8 seeds). Core occupancy was essentially tied (+0.00341, interval spanning zero). In a 55-tick target assay, normal − zero-turn harvest was +0.02872 with an interval spanning zero. For the costly-trained group, the same qualitative contrast persisted: normal core hit 0.2639, zero-turn core hit 0.6528. **H3 contradicted.** Straight-line exploration can intersect more targets even though adaptive turning helps harvesting in a continuing sparse ecosystem. High target entry does not necessarily indicate target retention or efficient foraging.

## Interpretation and limitations

**Supported:** Selection changes inheritable motor controllers; sparse-trained populations improve relative to founding controllers in the sparse holdout; with movement speed fixed, their normal turning yields higher common-garden harvest than forced straight movement. This is **useful, evolved turning under a specific environmental metric**.

**Not supported:** Reliable target-directed approach, purposeful planning, social cooperation, open-ended innovation or intelligence. A food island can be intersected by chance. A neural controller can turn in response to sensory changes and produce higher overall harvest without intentionally aiming at a target. Direction inversion has a weak effect compared to food blinding, leaving open whether forward food sensing, generalized speed-independent turning, or genuine lateral gradients drive the advantage.

**Important potential confounds and limitations:**

1. **Eight seeds** provide limited power and coarse intervals; seeded replicates are not an independent real-world sample. Multiple comparisons were explored without preregistration or multiplicity adjustments.
2. The rich environment's 900-agent cap and different resource supply can change selection strength. Rich-trained transfer superiority may be a consequence.
3. The common-garden metric is ecosystem harvesting, **not** direct navigation accuracy or net energy profit. Equal speed is imposed in speed-controlled comparisons, but all agents still experience energy costs and potential differential survival.
4. The target assay initially starts agents at 6.15 cells from an island with random heading and reports reaching *any* core, not guaranteed approach to the original island; motion is bounded to a 55-tick period.
5. The controller includes sensing of local food, crowding and stored energy; removing food channels can change both motor outputs in the original comparison. The fixed-speed follow-up isolates turning from translational speed, but not all other state-mediated effects.
6. Artificial-life complexity is modest: 16 weights, asexual reproduction, no memory neurons, no ecology of reproduction strategies and no explicit cooperative action channel.
7. Fixed-speed results use the **same genomes** under each intervention, making this a causal test of intervention performance but **not** an experiment on how genomes would evolve if steering were absent throughout selection.
8. Numerical exactness is confirmed for the tested Python/NumPy environment, not across all operating systems or versions. Pygame and Windows launcher still lack a runtime smoke test in this container.

## Reproduce and inspect

From the project root:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m biosphere navigation --seed-start 701 --seeds 8 --steps 1000 --probe-ticks 180 --count 120 --output results/experiment_004
python -m biosphere isolate --seed-start 701 --seeds 8 --count 120 --probe-ticks 180 --trained-results results/experiment_004 --output results/experiment_004
```

The eight-seed study is computationally substantial; individual completed seed results are cached atomically in `results/experiment_004/seed_parts/`, and trained full-state checkpoints are retained in `checkpoints/`.

- `results/experiment_004/summary.json` — overview of training, transfer, initial ablations and target outcomes.
- `results/experiment_004/motor_isolation_summary.json` — fixed-speed comparisons and seed-level paired-bootstrap intervals.
- `results/experiment_004/training.csv`, `holdout.csv`, `target_assay.csv`, `controller.csv` — primary source measurements.
- `results/experiment_004/motor_isolation.csv`, `motor_isolation_targets.csv` — fixed-speed source measurements.
- `results/experiment_004/` figures show transfer, motor ablation, target acquisition, fixed-speed harvest and fixed-speed target hits, plus independently generated screenshots of real simulation state. Regenerate the latter two with `python -m experiments.plot_navigation_results`.
- `tests/test_navigation.py` — determinism, sparse-terrain configuration, checkpoint continuation, target reproducibility and fixed-speed override tests.

**Proposed next experiment (005):** replace the 55-tick target probe with explicit time-to-first-entry and post-entry retention assays, balance spatial reachability across headings, vary island radius and intervention length, and compare with zero-turn **during evolution**, not only after evolution. The aim is to discriminate resource-oriented steering from stochastic local circling, without adding a hardcoded foraging policy.

### Independent outcome replay

A fresh execution of seed 701 using the saved trained worlds produced **32/32 identical fixed-speed garden rows** and **16/16 identical fixed-speed target rows**, including all numeric fields. This checks independent recomputation of the evaluation but is **not** independent training from founders.
