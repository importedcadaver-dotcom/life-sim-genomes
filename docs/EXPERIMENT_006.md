# Experiment 006 — Is the local looping conditional on food cues? (v0.6)

**Status:** Completed exploratory follow-up on 2026-11-02, using the archived eight Experiment 004 training seeds. This is a controlled **motor-only** analysis; it does **not** establish intelligence or new evolution during the 90-step probes.

## Question and competing explanations

In Experiment 005, inherited controllers frequently circled in food cores even with the food-sensing channels turned off. One explanation is **unconditional turning**: a genetic motor bias that retains an organism wherever it happens to start. Another is **conditional steering**: the same controller changes its trajectory when the local food-sensory pattern changes, perhaps improving short-range patch encounter or exploitation.

These are not exclusive mechanisms. Experiment 006 specifically holds movement speed, starting conditions, and energetic feedback constant. It also shifts food cues to decoy locations without moving the cores used for scoring.

## Exact protocol

- **Eight independent training seeds** 701–708 (archived, no retraining). Four genome sources per seed: founders, dense-evolved, island-evolved, and costly-island-evolved.
- **Two starting geometries:** Search: each of 36 agents begins 6.15 world units from a food center (core radius 3); residence: 1.1 units from the center. Same randomly sampled genomes, starting positions, and headings per source/seed across interventions.
- **Six causal conditions:** `rich` accurate resource-sensory cues; `barren` no nutrients and zero food cues; `ghost` accurate sensory cues but zero nutrients; `decoy` spatially offset cues with scoring cores unchanged; `food_blind` normal resource field with food sensory inputs disabled; `straight` true resource field with turn forcibly set to zero.
- **Arena:** Reflecting 96×96 square; 36 Gaussian cores on a regular 6×6 grid; cores at coordinates from 10 to 86, fixed Gaussian width 2.35, core-scoring radius 3.0.
- **Controller:** The production `World.controls()` function with the original inherited 16 weights, food-ahead/left/right sensory readings and normal feedback from other inputs. No foraging, homing, or stay-in-patch rule is coded.
- **Controlled motion:** 90 ticks, every agent moves at precisely 0.60 units/tick. Only the real motor output and boundary-reflection kinematics are applied. Feeding, caloric uptake, reproduction, food regrowth, metabolism, and death are deliberately suppressed; the internal energy signal remains constant. This is **not a lifetime ecology test**. Trajectories therefore report the motor response rather than food-driven energetic feedback.
- **Quantities:** Fraction entering any scored core, core occupancy, longest streak, absolute turn, displacement/path length, first-step motor response to cues, radial progress toward the initially assigned core over 1 and 8 steps, and *potential* food exposure in the specified reward field (which is not actual food consumption).
- **Counts:** 8 training seeds × 4 genome groups × 2 starts × 6 conditions = **384 trials**; each contains 36 trajectories × 90 steps. The **independent units are training seeds (n=8)**, not the 13,824 organisms/trajectories.
- **Statistics:** Paired differences within a training seed, descriptive percentile bootstrap intervals over the eight seeds (4,000 draws). Evolved-minus-founder difference-in-differences compares how much accurate food cues help both groups. All follow-up analyses are exploratory and not adjusted for multiple comparisons.

### Study outcomes: search starts

| Controller source | Accurate cues: entered core | Absent cues | Misleading cues | Straight-line baseline | Accurate cue benefit vs absent |
| --- | ---: | ---: | ---: | ---: | ---: |
| Founder | 29.2% | 16.7% | 17.4% | 85.8% | +12.5 pp |
| Dense evolved | 38.5% | 15.6% | 14.9% | 85.8% | +22.9 pp |
| Island evolved | 29.9% | 9.4% | 7.3% | 85.8% | +20.5 pp |
| Costly-island evolved | **37.2%** | **9.4%** | **9.7%** | **85.8%** | **+27.8 pp** |

The mean **within-seed accurate-minus-absent difference** for costly-island evolution was +27.78 percentage points (positive in 8/8 seed pairs; descriptive bootstrap interval +22.21 to +34.72 points). The **difference-in-differences against founders** was +15.28 percentage points, positive in 7/8 seeds (descriptive interval +7.64 to +22.22). This supports acquired cue-use changes among these existing evolutionary populations, but the original founders already displayed some cue-dependent behavior.

Misleading cues approximately eliminate the improvement, suggesting that the **location** of the cue matters and not merely the presence of some stimulation. However, straight-running organisms still reach far more cores in this particular regular, short-range geometry. This is **local resource-conditioned movement**, not efficient general navigation.

### Is the approach itself directional?

We measured movement toward the *original assigned* center over the first eight steps, rather than only whether the agent entered *some* core at any time. For costly-island controllers, mean radial progress was **−0.023 world units with accurate cues**, compared with **−0.308 without food cues** (a **+0.285** world-unit relative improvement). The paired cue improvement was positive in 8/8 training seeds (descriptive bootstrap interval +0.170 to +0.435 units). Both absolute means are still negative: the typical organism did **not** move closer to its target over eight steps. The correct inference is *less initial drift away*, not reliable target homing.

The average absolute difference in the initial turn command between accurate and absent cue conditions was about **0.043 radians** for costly-island controllers in the search assay. Since exactly the same positions, headings, genomes, internal energy, and crowd configurations were used at time zero, this is direct evidence that **their motor commands depend on environmental food signals**. It does not show that the dependence is always beneficial.

### Study outcomes: residence starts

| Controller source | Accurate-cue occupancy | Barren-cue occupancy | Straight-line occupancy |
| --- | ---: | ---: | ---: |
| Founder | 64.0% | 72.3% | 14.5% |
| Dense evolved | 66.2% | 71.3% | 14.5% |
| Island evolved | 80.1% | 81.7% | 14.5% |
| Costly-island evolved | **75.4%** | **79.0%** | **14.5%** |

**Persistent local looping survives in a barren arena**, and food cues often *decrease* residency when agents are placed at the center. For costly-island controllers the accurate-cue minus absent-cue occupancy difference was **−3.61 percentage points**; the sign varied by seed (positive in only 3/8). This supports the idea that the evolved agents have a strong generic turning/retention component alongside their food-contingent responses.

The `ghost` condition produced **identical movements** to the `rich` condition for the same genome and initialization; the hypothetical resource exposure was zero because no nutrients were available. Conversely, `food_blind` trajectories were **identical** to `barren` trajectories under constant energy, though actual resource exposure fields differed. These are **constructed internal controls** for stimulus/reward isolation, not independent natural observations.

## Conclusions and limitations

1. **Confirmed in these controlled assays:** inherited food-sensory inputs causally change motor outputs and the paths traveled; accurate local cues improve near-patch encounters relative to absent or displaced cues.
2. **Supported but exploratory:** costly-island evolution strengthened the patch-encounter advantage from those cues compared with founders. There are only eight training replicates, reused post hoc.
3. **Still supported:** baseline looping persists without food cues and is sufficient to maintain local occupancy when initialized inside a core.
4. **Not demonstrated:** a general-purpose long-range navigator, intentional foraging, within-lifetime learning, cognition, intelligence, or a lifetime fitness advantage in a realistic ecology.
5. The 6×6 regular patch arrangement, proximity of starts, lack of food depletion, fixed-speed clamp, and linear controller are substantial limitations. The exercise isolates mechanism rather than reproducing the full population ecology.
6. First-step alignment, core encounter, residency, potential nutrient exposure and evolutionary fitness are **distinct quantities**. A cue-sensitive trajectory is not automatically better for survival.

## Files and reproducibility

- Code: `biosphere/trajectory.py`, CLI: `python -m biosphere trajectory`.
- Raw trial data: `results/experiment_006/trials.csv` (384 records), raw illustration trajectories: `sample_trajectories.csv`, seed-paired contrasts and descriptive confidence intervals: `summary.json`.
- Figures: `search_cues.png`, `barren_residence.png`, `selection_cue_response.png`, `single_controller_paths.png` (single trajectory selected for illustration only).
- Exact replay, from the extracted project root:

```bash
python -m biosphere trajectory --seed-start 701 --seeds 8 --ticks 90 \
  --trained-results results/experiment_004 --output results/experiment_006_replay
python experiments/plot_trajectory.py
python -m pytest -q
```

`plot_trajectory.py` plots the **included canonical** `results/experiment_006` files, rather than the optional separately named replay directory; point the script at another directory if you want different data visualized. Numerical reproducibility is verified on the local NumPy runtime and does not imply cross-runtime bit-exactness.

## Next experiment suggestion (not yet implemented)

Test **food placement uncertainty** on larger, irregular landscapes, compare first-contact and persistent exploitation in a complete evolving ecosystem, and evolve a controller with additional memory or a changed sensor range **only as a new, explicitly separate experimental condition**. This would distinguish whether food-cue dependence improves whole-life reproductive success, not just near-patch entry in a synthetic arena.
