# Experiment 010 — Does evolvable regulation improve reproduction?

**Status: exploratory, 8 matched founder seeds, no statistically established advantage.** The protocol and complete data are in `experiments/run_regulatory_study.py` and `results/experiment_010/`.

## Question

Do organisms equipped with variable-length regulatory circuits produce more offspring than organisms possessing only the older fixed biological loci? Do available food cues matter when regulation is enabled?

## Protocol

Seed pairs 2401–2408; 420 world ticks; 40 initial organisms; cap 120; world 28×24; growth rate 0.008; movement cost 0.11; mixed reproduction; regulation point-mutation probability 0.10 and structural-mutation probability 0.12. Initial landscapes, physical positions, neural genomes and original 12 biological loci are generated with the same seeds before optional regulatory founders are sampled. Because regulation consumes additional RNG draws during initialization, stochastic trajectories are **not** an exact common-random-number coupling once ecology diverges.

Three conditions: old fixed biology (no regulation), inherited regulation with ordinary food sensing, and inherited regulation with food sensing blinded. Births are the primary exploratory outcome; population size, death counts, gene innovations and regulatory lengths are secondary. No individual organisms are assigned an artificial fitness score or forcibly culled.

## Results

| Condition | Mean cumulative births | Mean population | Mean new regulatory instructions | Mean active regulatory genes |
|---|---:|---:|---:|---:|
| Fixed biology | 120.375 | 57.5 | 0 | 0 |
| Inherited regulation | 124.375 | 57.875 | 8.5 | 3.054 |
| Regulation, food-blind | 122.750 | 56.5 | 9.25 | 2.926 |

Eight of eight populations survived in each condition. Regulation produced +4.0 average births relative to older biology, but **only five of eight seed pairs** showed a positive difference. In the blinded comparison, regulation yielded +1.625 mean births, with **four of eight positive pairs**. This is weak, mixed evidence; neither hypothesis has robustly passed.

Our analysis supports a **mechanistic** result: variable-length genes mutate, form chromosomes, and alter measurable physiology. It does not establish improved overall fitness, discovered photosynthesis, emergent intelligence or open-ended evolution. Larger replications, null controls, isolate-trait ablations and multiple-habitat tests are needed before stronger claims.

## Reproduce

```bash
python -m experiments.run_regulatory_study --seeds 8 --steps 420 --seed-start 2401 --output results/experiment_010_replay
```

Expected outputs: `trials.csv`, `timelines.csv`, `summary.json` and optional `births.png` if Matplotlib is installed. Compare outputs with saved `results/experiment_010/trials.csv` and `summary.json`. The engine is deterministic in the tested environment; cross-platform bitwise reproducibility is not guaranteed.
