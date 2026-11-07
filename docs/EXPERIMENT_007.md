# Experiment 007 — Do food cues confer ecological reproductive fitness?

**Status:** Completed exploratory, reproducible experiment. This is not evidence of consciousness, mental planning, or reliable long-distance navigation.

## Why this experiment exists

Experiment 006 demonstrated food-cue-dependent motor changes in brief, energy-clamped trajectories. It could not establish whether those trajectories improved survival or reproduction, since organisms neither ate nor reproduced in that assay. Experiment 007 restores complete ecology, while retaining matched counterfactual interventions.

## Protocol

- **Independent replication:** eight previously evolved training populations (seeds 701–708), originally generated and archived by Experiment 004; this run does not retrain them.
- **Genomes:** 80 drawn per seed from an island-trained, costly-movement checkpoint, compared with 80 unevolved original founders generated with the same source seed. Sampling is deterministic. Evaluation maps are *new* worlds seeded with `training seed + 130000`.
- **Matched treatment blocks:** each group and seed is evaluated under `normal`, `food_blind` (food-related inputs zeroed), and `mirror_food` (lateral food cues reversed, forward cue preserved). Initial maps, coordinates, headings, energy, and exact sampled genomes match among the three treatment arms.
- **Two movement conditions:** (a) neural-controller natural speed and turning, and (b) externally fixed speed 0.60, with turn still controlled by the same genome. The latter tests whether the result persists without a speed difference.
- **Ecology:** 72 × 54 arena, eight separated food islands, wraparound walls, background capacity 0.01, food regrowth 0.012, energy-based food harvesting and reproduction, movement cost 0.75, lifespan 330, cap 450.
- **Inheritance:** offspring inherit parental genes, **mutation disabled during the 350-tick evaluation** to isolate already-evolved genetic variation. Deaths, reproduction, energy expenditures and competition remain active.
- **Sample size:** 8 seeds × 2 genome sources × 2 movement conditions × 3 sensory interventions = **96 full-life colony trials**; 80 initial organisms each. The independent comparison unit is the training seed, *not* each simulated offspring.

The main prespecified-for-this-run outcome is `founder_direct_offspring`, the number of children produced by the 80 original test organisms divided by 80. This avoids counting the success of a few highly prolific descendants repeatedly. Secondary outcomes include total births per initial organism, the fraction of founders surviving through the first 100 ticks, final population, starvation deaths, and food harvested per organism-exposure tick.

## Main results

All values below are means of eight training-seed blocks.

| Training group | Movement | Food cues | Direct children per founder | All births per founder | Final population / founder |
|---|---|---|---:|---:|---:|
| Original founders | Natural | Normal | 0.702 | 2.080 | 1.095 |
| Original founders | Natural | Blind | 0.558 | 1.922 | 0.987 |
| Costly-island evolved | Natural | Normal | **0.800** | **1.650** | **0.852** |
| Costly-island evolved | Natural | Blind | **0.378** | **1.264** | **0.777** |
| Costly-island evolved | Natural | Mirrored | 0.714 | 1.600 | 0.895 |
| Costly-island evolved | Fixed speed 0.60 | Normal | 0.817 | 1.608 | 0.794 |
| Costly-island evolved | Fixed speed 0.60 | Blind | 0.442 | 1.336 | 0.741 |

**Within evolved populations:** normal cues vs blindness increased direct offspring by **0.422 per founder** under natural speed (8/8 seeds positive; exploratory paired bootstrap 95% interval 0.380–0.469), and by **0.375 per founder** with speed fixed (8/8 positive; interval 0.334–0.409). Total births also increased by 0.386 per founder under natural speed (8/8 positive; interval 0.234–0.528).

**Evolutionary differential:** the cue benefit in direct offspring (normal minus blind) was **0.278 per founder larger in evolved organisms than in founders** under natural speed (8/8 positive, exploratory bootstrap 0.186–0.392), and **0.227 larger** with speed fixed (8/8 positive, bootstrap 0.156–0.281). The treatment effects differ across genotypes and are not explained solely by their natural movement speeds.

**Weaker outcomes:** normal-vs-blind difference in final population for the evolved group was just +0.075 organisms per founder (5/8 seeds positive; bootstrap crosses zero). No clear advantage appears for normal-versus-mirrored cues in *total births*, indicating that the food-direction component is less established than the general food-input benefit. Reproduction is not equivalent to sustained population success.

## Interpretation

Food-dependent sensorimotor computation can meaningfully affect reproductive fitness in this artificial ecology. Importantly, the stronger evolved-group response compared with founder controllers supports **selection having favored useful food-cue responses** in the populations we studied.

This does **not** establish purposeful homing, intelligence, planning, or open-ended evolutionary innovation. The task is one simple environment, the controllers have only 16 inherited weights, and behavior may include non-targeted turning and chance encounters. We also cannot infer that this outcome generalizes to every population regime or resource layout.

## Causal strengths and limitations

Strengths: paired within-seed counterfactuals; identical initial evaluation maps, starting conditions and genomes for each sensory comparison; separate fixed-speed arm; real feeding, reproduction, death; archived checkpoints; repeatable random seeds; no manually programmed foraging strategy.

Limitations: training populations were reused from earlier experiments rather than freshly retrained for a preregistered protocol; the comparison is exploratory with only eight independent training seeds; a mutation-free evaluation shows fitness of *existing* genotypes, not novel mutation acquisition in the evaluation; multiple outcomes and contrasts were examined; stochastic competition makes colony outcomes nonlinear; evaluation focuses on one sparse ecological setup and a selected sample of surviving checkpoint genomes; genetically evolved versus founder groups have different histories, so the differential cue benefit supports but does not isolate every cause of the evolutionary change.

Paired-bootstrap intervals are **descriptive exploratory uncertainty**, not definitive hypothesis tests or multiplicity-corrected confidence intervals. The training checkpoint genome samples, not individual offspring, are the independent units.

## Raw evidence and reproduction

- `results/experiment_007/trials.csv`: 96 full-life trial-level records (the source of all means).
- `results/experiment_007/summary.json`: per-condition means, seed-paired contrasts, and differential evolutionary cue benefits.
- `results/experiment_007/offspring_sensory_controls.png`, `evolved_vs_founder_cue_advantage.png`, `final_population_caveat.png`: regenerated charts.
- `biosphere/fitness.py`: complete ecological experiment implementation.
- `experiments/plot_fitness.py`: figure renderer.

From the project root:

```bash
python -m biosphere fitness --seed-start 701 --seeds 8 --ticks 350 --count 80 --trained-results results/experiment_004 --output results/experiment_007_replay
python experiments/plot_fitness.py
python -m pytest -q
```

The plotting script reads the included canonical `results/experiment_007` by default. Use the CSV/JSON outputs to compare to another replay directory byte by byte.
