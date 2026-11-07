# Experiment 008 — Does sensor-aware training reliably improve descendants' reproduction?

## Preregistered comparison

The final methods and primary endpoint were written to [`EXPERIMENT_008_PLAN.md`](EXPERIMENT_008_PLAN.md) before the full 12-seed run. The two-seed, short-duration implementation smoke check was conducted separately and is not included in the results. The final study used seeds **1101–1112** without tuning after viewing the results.

Twelve pairs began from identical founding genomes, positions, environment and initial RNG states. In each pair, one training population received real food input and the other had the food-input channels disabled. They evolved for **550 ecology ticks**, with reproduction, mutation, birth, death and feeding operating naturally. The model uses a 300-organism population limit and isolated food islands.

From each surviving evolved population, a separately seeded RNG sampled 60 genomes with replacement. Those genomes were then tested in a new, fixed common-garden habitat for **280 ticks**, with **mutation disabled**. Both trained conditions were tested with accurate food cues and, as a secondary intervention, with food cues disabled.

The preregistered primary outcome was total births per starting test organism in accurate-cue common gardens, compared within each paired training seed. A source-world cheat, minigame or UI intervention was not used.

## Results

| Training | Common garden senses | Mean births per starting organism | Mean final population |
|---|---|---:|---:|
| Food sensing enabled | Accurate cues | **3.035** | 166.2 |
| Food sensing disabled | Accurate cues | **2.953** | 159.0 |
| Food sensing enabled | Food blind | **2.808** | 147.5 |
| Food sensing disabled | Food blind | **2.997** | 157.5 |

The primary paired difference was **+0.0819 births per founder**, but just **5/12 paired seed contrasts were positive** and **7/12 negative**. All twelve matched training arms survived to common-garden transfer.

The result **does not support a robust, consistently positive evolutionary benefit from training with food sensors** in this new design. The small positive average is sensitive to heterogeneous seed-level outcomes, notably one large positive difference. Differences between direct food-cue utility and *evolutionary selection for cue-sensitive genotypes* should not be conflated.

The secondary transfer results are also heterogeneous. A food-blind-trained population can achieve high reproductive output in blind evaluation. These results are simulation-specific; no claim about intelligence, consciousness or life outside this model is warranted.

## Limitations and interpretation

- This is one pre-specified parameterization with 12 independent evolutionary seed pairs. It is not a broad generalization over food topologies, larger genetic models or hundreds of repeated trials.
- The transfer samples genotypes from *living* survivors; extinction would have led to a missing transfer and an explicitly conditional estimate. No extinction occurred in the final training data.
- Samples are with replacement, and the evaluation population begins in a new landscape. The comparison estimates performance of sampled survivors, not cumulative historical fitness of every extinct ancestor.
- The 280-tick evaluation is finite and capped at 300 simultaneous organisms. Endpoint births and population density can behave differently.
- The positive Experiment 007 sensory ablation in previously evolved populations is not contradicted by this finding: the questions differ. Experiment 007 evaluated the **immediate effect of food cues** within a fixed evolved controller, while this experiment compared **evolutionary training histories** and subsequent transfer.

## Reproduce and inspect

```powershell
python -m biosphere.selection_008 --seeds 12 --train-ticks 550 --eval-ticks 280 --output results/my_experiment_008
```

See `results/experiment_008/trials.csv` (48 trial records), `results/experiment_008/summary.json` (all twelve paired contrasts), and `results/experiment_008/paired_contrasts.png` (the individual paired differences).
