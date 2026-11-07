# Experiment 008: Do food senses change evolutionary outcomes?

Pre-specified before running the final study (v0.9 authoring session).

**Primary contrast:** For each independent training seed, evolve two populations from exactly the same founding brains and world, with food sensors respectively enabled and disabled. After 550 ecological ticks, sample 60 genomes (with replacement if fewer than 60 survive) from each surviving training population using a separate sampling RNG. In an independently seeded, common-garden world, evaluate descendants with food sensors enabled, reproduction and mortality active, mutation **disabled**, for 280 ticks. Primary outcome: total births / 60 starting organisms. Report the paired difference (sensor-trained minus blind-trained) over 12 seeds.

**Secondary contrast:** In the same common-garden environment also evaluate both trained genome groups with food sensors disabled. This estimates a train-condition × evaluation-condition difference. Report final population as a descriptive outcome. Do not call any single seed or endpoint definitive.

**Training:** 96 founders, max population 300, 7 static isolated food islands, world 72x54, island width 3, growth 0.012, background 0.01, movement cost 0.45, mutation enabled. Training seed IDs 1101–1112. Common garden seeds 91101–91112, 60 founders, max population 300, same habitat parameters, mutation off, fixed founder sample from each training condition. Use deterministic initial states and independent sampling RNG. Do not use any cheat or UI interventions.

**Failure policy:** If a training arm goes extinct, record extinction as missing evaluation and report it without silently substituting founder genomes or dropping the seed from a survival claim. The primary paired contrast is conditional on both training arms surviving, and will be labeled accordingly. If too few pairs survive, do not claim an evolutionary difference.

**Inference:** Report all 12 seeds, outcome means and individual paired contrasts, not just a positive mean. A positive sign alone does not establish general intelligence or open-ended adaptation. A selection advantage should be inferred only if consistent replicated ecological outcomes support it. Run the experiment once without selecting a favorable set of seeds or retuning ecology based on results.
