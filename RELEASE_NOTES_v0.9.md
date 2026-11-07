# v0.9 — Pink Living Observatory

## Built

- **Cute expressive creatures:** genome-derived pastel pink/lavender/peach/mint palette, rounded ears, blush cheeks, eyes, directional nose markers; high-density simplified renderer retained for performance.
- **Pink/plum interface:** warm dark theme, four persistent discoverable top-of-map navigation buttons for new features.
- **Sugar Rush cheats:** refill habitat food, boost selected organism's energy, spawn up to 8 artificial clone offspring, disable metabolism and aging. Every non-scientific manipulation is saved as an intervention; a full habitat remains subject to its population limit.
- **Two mini-games:** Berry Hunt (guess the food-rich cell from approximate visual clues) and Speed Detective (read authentic controller-speed bars). One observer star per correctly answered challenge; independent RNG, no effect on evolution.
- **Persistent Chronicle:** bookmarks, finite recent-event log, sampled movement tracks, read-only replay, sidecar save/load that accompanies a world checkpoint. No claim of complete simulation rewind.
- **Paginated children** in family tree and correct last-child navigation.
- **Matched twin-world laboratory:** clone the exact current simulation twice, then alter just one parameter in the second cloned run. Results saved to a JSON sidecar; source not modified.
- **Experiment 008:** 12 training seed pairs × 4 common-garden ecological evaluations = 48 ecological transfer records with a precommitted primary comparison, raw data and report. Mean paired advantage +0.082 births per founder but just 5/12 seeds positive: the evolutionary-training benefit is *not robust* in this ecology.

## Verification boundaries

Headless tests and image-based render-path checks run without Pygame. No claim of a verified SDL/Pygame window or Windows graphical performance. The motor/sensor energy loop and the causal experiments do not use the new UI or cheat functions. The only change in `simulation.py` is paginated offspring lookup.
