# The Accidental Biosphere — Digital Biology v1.0

This is an **artificial evolutionary system**, not a molecular or medically realistic DNA simulator. Its gene names describe a defined mathematical genotype-to-phenotype mapping. Complex behaviors are **not hardcoded**. The organisms have inherited controllers and individual biological traits, and their lineages rise or fall through feeding, energy costs, survival, and reproduction in a shared ecosystem.

## What is inherited?

Each new organism has:

- **16 neural-controller parameters** (two motor channels × eight inputs), inherited from one or two parents.
- **12 biological loci** (floating-point alleles, bounded -2.5 to +2.5), including size, metabolism, digestion, propulsion, turning, sensor range, sensory gain, longevity, maturation, reproductive investment, pigment and spots.
- **A structural copy number for every biological locus (0–3)**. Duplications and deletions are heritable; the expressed value is allele × copy number, clamped within safe limits. A lost copy (0) silences that gene's deviation from neutral. Extra copies increase or decrease the contribution of the allele according to its sign.
- **Parent A and optional Parent B IDs**, birth generation, and the number of mutations acquired at birth. These are preserved in living and death archives and in checkpoints.

Consequently the modeled **genome site count** is `16 + sum(gene_copies)`. It starts at 28 and can change from 16 to 52. This is bounded gene-copy evolution, **not unlimited new gene discovery**. The number of named gene functions remains fixed at 12 in v1.0.

## The 12 loci and actual effects

| Locus | Biological effect | Trade-off / consequence |
|---|---|---|
| `body_size` | Adult body radius, maximum bite size | Larger bodies have higher maintenance and movement costs |
| `metabolic_efficiency` | Reduces baseline energy expenditure | No added explicit trade-off; used to validate selection |
| `digestion` | Energy gained from each food unit | Raises metabolic maintenance |
| `propulsion` | Changes active motor speed | Faster locomotion spends more energy |
| `turning` | Scales controller-driven turning | Interacts with body size and trajectory geometry |
| `sensor_range` | Changes food sampling distance | More sensitive systems cost more energy |
| `sensor_gain` | Scales food sensor channels | Can amplify helpful *or misleading* food cues |
| `longevity` | Alters maximum age | Increases maintenance overhead |
| `maturation` | Changes the tick at which reproductive maturity is reached | Controls the duration of juvenile growth |
| `investment` | Changes reproduction energy threshold and parent cost | Larger investments give newborns more energy |
| `pigment` | Selects inherited pastel coat color | Decorative; deliberately neutral |
| `spots` | Selects inherited cheek/body markings | Decorative; deliberately neutral |

All phenotype multipliers use bounded continuous exponential mappings; there is no universal absolute “fitness score.” Organisms' outcomes are counted from *actual births, starvation deaths, and age-related deaths*. A newborn physically grows from 55% toward its inherited adult size; juvenile feeding capacity and locomotion also mature over time. These developmental changes **do not modify its DNA**.

The math lives in `biosphere/genetics.py`; the ecological coupling is in `biosphere/simulation.py` (`World.biology`, `World.perceive`, `World.controls`, `World.step`, `World._reproduce_biological`). Editing these changes what evolution is capable of producing, so experimental results require a new software-version label.

## Reproduction, selection, and mutation

Organisms must obtain enough food energy and reach their inherited maturity age to reproduce. They cannot reproduce freely when the habitat is full. There is **no scripted elimination of the weakest 50%**, no manual gene rankings, and no promise that evolution always improves a chosen metric.

The new habitat offers three reproduction modes:

- **Asexual:** One parent, inherited controller/body DNA, optional mutations.
- **Sexual:** Two eligible parents must be within 4 world units; each contributes half of the reproductive energy. Every neural parameter and biological locus is inherited randomly from one parent, including locus copy counts. Each parent can participate at most once per tick.
- **Mixed (default):** Tries local two-parent reproduction first, but can reproduce asexually if no suitable partner is nearby. This maintains births in sparse landscapes and permits recombination when local ecology supports it.

All creatures are abstract simultaneous-hermaphroditic organisms—there are no sex chromosomes, gametes, anatomical reproductive systems, mate preferences, or populations of fixed biological species. Do not interpret one shared cell as literal real-world mating.

Offspring may receive three kinds of mutation:

1. Neural-weight copying error (the original mechanism).
2. Biological allele copying error, changing a quantitative parameter.
3. Gene-copy duplication or deletion (copy count from 0 to 3).

Mutations are random, sometimes harmful, sometimes neutral, occasionally beneficial in a particular ecology. The code has no notion of what “good” means; performance emerges from realized reproduction and survival.

## Keep research clean

The v0.9 historical scientific engine is preserved as `Config(genetics_enabled=False)`, the default for standalone `Config` and `biosphere run` without `--genetics`. All previous checkpoint files remain loadable. New viewer worlds enable biology by default. Do **not** silently enable genetics on a historical v0.9 research checkpoint; the original runs would no longer be comparable.

Genetics-enabled save files include all biological genotypes, copy counts, two-parent relationships, mutation counters and RNG state. `World.load` refuses to load a declared biology-enabled save that is missing its DNA arrays rather than inventing DNA.

Cheats still mark worlds as interventions. `DNA Spark` changes the selected creature's alleles and copy numbers and records the edit. An intervened world is useful for play, but **not** an unmodified scientific control.

## Commands

Start the cute genetic sandbox: extract the archive, run `run_windows.bat`, click an organism, then press **G** or click **DNA** at the top. The DNA lab displays 12 alleles, copy numbers, parent links, modeled genome length, and adult phenotype multipliers. `Q` opens the cheats; **5** applies `DNA Spark` to your selected living creature.

```bash
# An actual scientific run with biology enabled:
python -m biosphere run --genetics --reproduction-mode mixed --steps 5000 --seed 19 --events --output results/dna_19

# Run many independent seed pairs in parallel on your own CPU:
python -m biosphere genomics --seeds 12 --ticks 1600 --workers 4 --output results/genetics_study

# Compare one causally functional gene to a neutral inherited color marker:
python -m biosphere gene-selection --seeds 12 --ticks 700 --output results/gene_selection

# Constrain reproduction to local two-parent crossover:
python -m biosphere view --reproduction-mode sexual

# Replay a saved DNA world exactly:
python -m biosphere view --resume results/dna_19/world.npz
```

The `genomics` command writes per-seed time series for all 12 alleles and gene copy counts, every population's reproduction and extinction history, a summary report, and matched mutation-on/off conditions. It uses *local* Python processes; it does not require a cloud account, hijack devices, or promise billions of evaluations.

## Next honest science steps

- Test rarer and more heterogeneous ecological conditions that force stronger trade-offs rather than simply favoring one obvious gene.
- Validate selection against drift using preregistered replicates and trait-specific environment changes.
- Add a true variable-topology regulatory/controller network if the goal becomes unbounded neural architecture evolution.
- Add species-level reproductive isolation, ploidy, dominance and recombination linkage only after their consequences can be measured.
- Keep static color/spot loci neutral for control comparisons; do not pretend decorative inheritance proves useful adaptation.

## Research context

Avida demonstrates that replication, heritable variation, and differential success can drive evolution of digital programs. Its genome instructions and complexification differ substantially from this simulator's bounded quantitative alleles; this implementation must not be described as replicating Avida's full open-ended evolution.

- https://pmc.ncbi.nlm.nih.gov/articles/PMC10492814/
- https://pmc.ncbi.nlm.nih.gov/articles/PMC9470259/
