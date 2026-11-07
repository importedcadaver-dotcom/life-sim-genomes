# Release v0.5 — The Field Observatory

**Scope:** Visual/game-design audit and UI overhaul **first**, then completed controlled Experiment 005.

## What changed from v0.4

- Redesigned Pygame viewer with scientific dark food heatmap, distinguishable directional creatures, lineage generation color, selected-specimen tracking trail, birth/death location ripples and event feed.
- Clickable action strip, four zoom levels, right-drag pan, follow-camera mode, adjustable pacing (now defaults to 1 tick/frame), single-step, specimen motor telemetry, live intake and energy meter.
- Optional field journal with factual observations and separate nutrient sandbox brush.
- Viewer's in-run modifications (food brush, food regrowth, boundaries, shifting patches, movement cost) are recorded as interventions. Restart from a seed creates an unmodified new world.
- Fixed old screenshot-timing problem (now saved after current frame is drawn), mitigated sidebar clipping at supported screen sizes and timestamp collisions for rapid saves.
- Fixed headless event CSV compatibility with enriched birth/death x/y positions.
- Original v0.4 checkpoints remain loadable (optional new inspection array defaults to zero).
- Experiment 005: 256 search/residence probes, eight independent training seeds, motor/sensor ablations; reproducible CSV, JSON and figures.
- Updated Windows launcher fallback for Python installations without the `py` launcher.
- Automated tests increased from 41 to 55, all passing headlessly.

## Core finding

Costly-island-trained controllers with fixed speed entered a food core in 33.7% of search trials compared with 74.3% for straight movers. Given an initial position inside a core, the evolved controllers stayed inside 80.9% of ticks compared with 14.7% for straight movers. Blinding food sensors still produced 83.0% residence. This is evidence for a search-versus-local-retention tradeoff, **not** demonstrated food-specific navigational intelligence.

## Verified and not verified

**Verified:** Python source syntax, 55 regression tests, deterministic saved-world continuation, packaged headless CLI, CSV exporter and 32/32 independent seed-701 evaluation rows. **Not verified:** actual Pygame rendering/input behavior or Windows launch, because Pygame installation is blocked in this container. The screenshot-style image in `results/experiment_005/observatory_visual_preview.png` is a *static Pillow-based design preview generated with authentic checkpoint organism data*, not a Pygame screenshot.

Full detail: `docs/VISUAL_AUDIT.md`, `docs/EXPERIMENT_005.md`, `docs/QA.md` and the fresh `README.md`.
