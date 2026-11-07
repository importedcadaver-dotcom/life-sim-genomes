# Visual, interaction, and game-design audit — v0.4 → v0.5

**What was inspected:** `biosphere/viewer.py`, an actual v0.4 evolved-world screenshot (`results/experiment_004/ecosystem_islands_seed701.png`), simulation/event/checkpoint implementation, and recorded experiment/QA files. **Pygame runtime is not available in this container**; the new screen has been assessed through code, headless geometry/color tests and a Pillow-based static layout preview made from a real world checkpoint. These are not substitutes for Windows GUI acceptance testing.

## Findings and targeted fixes

| Severity | Finding from v0.4 audit | v0.5 change | Verification |
| --- | --- | --- | --- |
| High | Actual entities were tiny undifferentiated dots; motion and direction hard to follow | Directional triangular micro-organisms with dark tails, contrast against dark terrain, pulsing birth/death rings, highlighted tracked individual and historical trail | Source review, palette tests, static preview; window not run |
| High | Default speed was 3 ticks/frame × 40 fps (120 ticks/second) | 1 tick/frame × 35 fps default; 0.25×–25× selectable pacing, pause and single-step | Source review; window not run |
| High | No zoom/pan/follow | Scroll zoom, right-drag pan, click-to-select, L to follow, selected trajectory trail | Source review; window not run |
| High | Direct interaction mostly unavailable, so it felt like a static dashboard | Clickable action strip for transport, heatmap, follow, sandbox brush, and save; editable habitat in clearly marked sandbox mode | Brush conservation and checkpoint tests; GUI not run |
| High | Minimal inspector lacked any behavior feedback | Live per-organism food intake, motor speed, turning command, energy meter, parent ID, generation, lifespan | Deterministic engine tests; GUI not run |
| High | Fixed sidebar position/metric spacing could clip on window resize | Layout geometry derived from screen/world size, minimum effective window size and optional compact event feed | Automated 4-resolution geometry tests |
| Medium | Save action stored screenshot during input handling, showing previous frame rather than completed frame | Screenshot is taken after drawing/flipping; microsecond-unique filenames and visible success/failure toast | Code review only |
| Medium | Birth/death records carried no positions; couldn't animate real events | Full position fields added to events; CLI event CSV schema updated to accept them | Event export and deterministic tests |
| Medium | There were no visible tasks or discoveries for spectators | Optional J field-notes overlay with six factual milestones computed directly from the simulation | Source review only |
| Low | Duplicated v0.4 README sections and inconsistent controls | Consolidated README and a v0.5 UI field guide | Documentation review |

## Design principles

- **Research mode:** every visual effect is noncausal; no artificial organism drama or scripted predator/prey behavior is introduced.
- **Sandbox mode:** clicking terrain adds food carrying capacity and stocked food via a bounded Gaussian brush; the resulting world is flagged **SANDBOX EDITED** and stores a persistent intervention log in checkpoints (also recording live ecology toggles). Observations in manipulated worlds must not be presented as unmanipulated experimental findings.
- **Observation as gameplay:** selecting, following, noticing lineage changes, recording a field note, testing scarcity, and saving states constitute a modest active loop. It is not yet a full strategy game.
- **Scientific integrity:** the renderer neither gives food coordinates to an agent nor changes the decision controller. Manual brush actions are quarantined from the headless experiment runner.

## Unresolved design problems and honest limitations

1. No gameplay win/lose structure beyond natural extinction, no detailed long-lived lineages panel, no replay timeline, and no isolated specimen microscope with actual brain-weight diagrams yet.
2. Observer must still learn keyboard shortcuts for advanced ecology controls; the user-facing help overlay and clickable primary action bar mitigate but do not remove the learning curve.
3. There is no sound design or dynamic multi-hour documentary camera. Rendering 900 creatures at high zoom still needs FPS profiling on real target hardware.
4. The static preview is made by Pillow to approximate this code's map palette, layout, and HUD; it is not a verified Pygame runtime screenshot or a guarantee of exact glyph placement across platforms.
5. Older research PNGs use the original light style because they are experimental evidence and should **not** be retroactively recolored.

## Next UX acceptance test on a computer with Pygame

Launch `py -3 -m biosphere view --resume results/experiment_004/checkpoints/seed_701_islands.npz`; resize to 1020×685, 1200×760 and 1400×880; check no panels overlap, save screenshots, click a creature and follow, zoom and pan, use each action-bar control, create a sandbox patch, save and reload the marked checkpoint, verify the screenshot shows the actual current tick, and test 900-organism performance at the fastest speed. **This has not been performed here.**

Reference UX research consulted:
- [Lenia scientific viewer](https://wartets.github.io/Lenia/docs/index.html) (display modes, inspector/presets, live controls)
- [Patch World](https://floatingpragma.io/demos/patch-world/) (inspect an organism, examine its brain, pan and zoom)
- [LifeLabs](https://lifelabs.online/en/) (distinct observe/pilot modes and an experimental journal)
