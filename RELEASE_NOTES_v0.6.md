# The Accidental Biosphere v0.6 — Experimental follow-up

## What changed

- Implemented **Experiment 006**, a motor-only, headless counterfactual study of inherited food-cue responses versus generic turning/looping.
- Added `biosphere/trajectory.py` and `python -m biosphere trajectory` with six manipulations: accurate food cues, barren/zero cues, phantom cues, misleading shifted cues, food-input blindness, and straight movement.
- Recorded short-range target acquisition, local occupancy, absolute turning, net displacement, first-step angle changes, first-eight-step radial progress and possible resource exposure without representing it as actual harvesting.
- Ran **384 matched trials** (8 archived independent training seeds × 4 genome groups × 2 starting conditions × 6 interventions; 36 organisms per trial, 90 steps).
- Added paired seed-level contrasts, descriptive bootstrap intervals and evolved-minus-founder difference-in-differences analyses, plus four chart/trajectory figures and an explicit experimental journal.
- Added 11 deterministic regression tests; suite now has **66 tests**.
- Preserved all v0.5 viewer features, the 55 original tests, prior saved worlds and prior experimental evidence. No new visual viewer functionality is claimed in v0.6.

## Key scientific finding

Costly-island-evolved agents reached a nearby patch with accurate food cues in 37.2% of probes, versus 9.4% when the cues were unavailable or spatially misleading (~9.7%). The cue-dependent encounter advantage was greater than in founders in 7/8 independent training seeds. However, straight runners hit nearby patches even more often (85.8%), and barren-condition agents continued circling locally. Food cues can improve near-patch search without making a generally efficient navigator.

## Validation boundary

Code/tests/headless experiments and release archive are verified. The existing Pygame viewer was not graphically launch-tested here (Pygame unavailable), and the Windows launcher was not run on Windows. The sample trajectories and figures are scientifically illustrative static exports, not captured gameplay screenshots.
