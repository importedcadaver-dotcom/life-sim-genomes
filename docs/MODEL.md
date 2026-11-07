# Model specification, v0.2

## State and update schedule

A world holds a stationary food **capacity** map `K[y,x]` and a mutable **stock** map `F[y,x]`. The map is a torus: crossing any edge wraps around to the opposite edge. Capacity is created by adding smooth periodic Gaussian patches to a positive baseline. The grid has `72 × 54` cells by default.

Each individual has ID, parent ID, x/y position, heading, energy, age in ticks, generation number and a floating-point `2 × 8` weight genome. ID is unique during one world's history. Individuals are diploid? **No.** They inherit asexual cloned parameters, with independent mutations, and are genetically haploid in this simplified computational sense.

At each tick:

1. Perceive food at three points, 3 world units away, in front and ±60°; compute two contrasts, own energy fraction, and crowding (0–8 neighbors occupying same cell).
2. Calculate `turn = max_turn × tanh(Wturn · inputs)` and `speed = max_speed × (0.05 + 0.95 × sigmoid(Wspeed · inputs))`.
3. Turn and move in the toroidal plane, while aging by one tick.
4. Compete for the food stocked in the current grid cell. Uptake is at most `max_bite` and the available food is shared fairly when agents overlap. Food removal is simultaneous and cannot make stock negative.
5. Add `uptake × food_gain` to energy, subtract resting metabolism and a speed-proportional movement cost.
6. Remove starvation deaths (`energy ≤ 0`) and old-age deaths (`age ≥ lifespan`). Extinction is permanent unless the user restarts.
7. If an individual exceeds the **age** and **energy** thresholds for reproduction, spend `reproduction_cost` energy and create a newborn close to the parent. Up to one offspring per individual per tick; if capacity is full, candidate parents are randomly shuffled before admission. Newborn starts with energy `newborn_energy`, which is less than reproduction cost. The genome is cloned with sparse independent Gaussian point mutations. Newborns do not act until the next tick.
8. Regrow food by `growth_rate × (K − F)`, a bounded first-order recovery rule.

## Neural input ordering

| Index | Sensor | Range/meaning |
| ---: | --- | --- |
| 0 | Bias | exactly 1 |
| 1 | Food ahead | local food stock / 12, clipped [0,1] |
| 2 | Food left | local food stock / 12, clipped [0,1] |
| 3 | Food right | local food stock / 12, clipped [0,1] |
| 4 | Forward contrast | front − average(left,right) |
| 5 | Left-right contrast | left − right |
| 6 | Energy fraction | energy / reproduction threshold, clipped [0,2] |
| 7 | Crowding | other agents in current cell / 8, clipped [0,1] |

One weight vector produces heading change. A second vector produces movement magnitude. There is **no recurrent state, cognitive map, memory, behavior tree, hand-coded foraging routine, or reward-driven training inside an individual**. The decision is a deterministic transformation of current sensor values and genes.

In the blind condition, columns 1–5 and 7 are zeroed; bias and energy remain. This is an intervention on external sensing, not on genetic variation itself.

### Experiment 002 interventions (not evolutionary mechanisms)

The underlying update schedule is unchanged from v0.1. To distinguish generic speed selection from spatial steering, the new experiment-only configuration may set `fixed_speed` (override motor output with a constant speed) or `fixed_turn` (e.g., set steering to zero). The optional `sensor_mode` now also supports `food_blind` (set columns 1–5 to zero, retain crowding), `crowd_blind` (zero column 7 only), and `mirror_food` (swap lateral food readings and reverse the left/right contrast). These modes never create or change inherited genome parameters.

**Coordinate convention:** Positive angular rotation is toward the side sampled with the `+π/3` sensor offset. The code calls that sensor *left*, though a screen with its y axis pointing downward depicts positive rotation as clockwise. Consequently, "left" and "right" are internal lateral-channel labels rather than literal screen-left/screen-right. Positive cue steering in the experimental assay means matching the sign of rotation to the *richer sensed lateral channel*, regardless of display handedness.

## Default energy and heredity constants

| Variable | Default |
| --- | ---: |
| Founders | 180 |
| Population cap | 900 |
| Founding energy | 32 |
| Resting cost | 0.20 / tick |
| Speed-proportional cost | 0.065 × speed / tick |
| Maximum intake | 1.45 food / tick |
| Energy conversion | 1.75 energy / food |
| Food regrowth factor | 0.030 / tick |
| Max lifespan | 330 ticks |
| Minimum reproductive age | 15 ticks |
| Reproduction energy threshold | 47 |
| Reproduction parent energy cost | 27 |
| Newborn's starting energy | 22 |
| Weight mutation probability | 0.14 per weight per birth |
| Mutation noise std. dev. | 0.28 |
| Motor max speed | 0.90 world units / tick |
| Motor max angular change | 0.60 rad / tick |

These are model parameters, **not calibrated biological measurements**.

## Limits of the model

- **Complexity ceiling:** fixed 16-weight genome and no brain structure mutations; sophisticated multistage behavior is unlikely.
- **Engine-imposed physics:** organisms do not implement energy uptake, reproduction, inheritance or death by themselves. Thus it is agent-based Darwinian evolution, **not synthetic origin of life**.
- **Pre-engineered sensors:** food information and orientation are provided; only the reaction is evolved.
- **Static resource capacities:** regions remain fertile even as local stocks fluctuate, potentially encouraging patch residence.
- **Automatic reproduction:** there is no mating decision, sexual selection or breeding strategy.
- **Global cap:** the limit is a compute-budget constraint that can influence selection at maximum occupancy.
- **Unmodeled interactions:** no attacks, toxins, construction, communications, parasites, predators or niche construction.
- **Independent random seeds:** the model uses the same NumPy pseudorandom generator for its stochastic events; deterministic restarts are tested but different NumPy versions may produce floating-point differences.

These limitations are intentional for the first stage. A next version should relax them **one at a time**, with carefully paired experimental comparisons.

## Experiment 003 environment variants (v0.3)

The default world remains compatible with v0.2: `boundary_mode="wrap"`, `patch_shift_interval=0`, `move_cost=0.065`. Two new environment settings do **not** add any genome input/output channels or explicitly scripted agent decisions.

- `boundary_mode="reflect"`: a step crossing a wall is reflected geometrically; the heading is reflected around the wall normal. For sensory rays beyond the border, the coordinates are reflected into the same grid, rather than sampling food on the far side of a torus. Infant placements near the wall are also mirrored. Large steps are handled with period-2L coordinate folding; speed remains bounded by the config.
- `patch_shift_interval=N`: after each Nth tick's increment but before the organisms sense food, the carrying capacity matrix and current food stock matrix shift together by seed-determined offsets. The shift preserves stocked food mass exactly at that moment, although eating and growth subsequently change the total. This is not realistic seasonality; it is a controlled change in the correspondence between resources and position.
- `move_cost`: controls the per-tick energy debit `movement_speed * move_cost`, in addition to basal metabolism. The `costly` experiment sets it to `0.75` instead of `0.065`.

The scientific treatment of turning remains unchanged: linear weighted sensor values pass through `tanh`, speed through a logistic squashing function, and the genome mutates during cloning. Fixed-speed, zero-turn, and food-blind options are **experimental interventions**, not abilities held by organisms. They are used to measure whether evolved behavior improves ecological outcomes compared with controlled alternatives.

## Version 0.4 additions — sparse, separated resource islands

The original neural controller and reproduction model are unchanged. `Config.resource_layout="islands"` selects a seeded collection of eight Gaussian food-capacity peaks rather than the original many overlapping hills; default standard deviation 2.8 cells and peak capacity 10. The capacity field remains stationary unless the pre-existing patch-shift option is selected. Resource harvesting and regrowth are unchanged. Food sampling still consults only egocentric local grid readings; island coordinates are never passed to controllers.

A synthetic *target-acquisition assay* (not part of organism evolution) replaces the resource map with 36 isolated Gaussians and places test organisms at equally distant, randomized starting points to measure acquisition and residence. The `isolate` experiment externally clamps forward speed to 0.60 to distinguish steering-related sensor effects from speed-neuron effects. These are scientific interventions, not new genome or organism capabilities.
