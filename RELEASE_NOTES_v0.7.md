# v0.7 — Living Observatory / Experiment 007

## What changed

1. **Pacing for people:** render loop and simulation speed use separate wall-clock timing. Speed presets range from half a tick per second to 600 ticks per second. Single-step and pause remain available. A follow-on speed cap prevents accumulated frame delays from creating long, surprising catch-up sequences.
2. **Events that remain visible:** birth/death map rings now last 4.5 real seconds, not a handful of simulated ticks. The player can toggle pause-on-selected-events (`P`) to stop when the selected organism dies or has offspring.
3. **Persistent individual lives:** every organism's direct offspring, born tick, first food, first offspring, lifetime food harvest, distance traveled, peak energy, age and cause of death are tracked in the simulation and preserved in full NPZ checkpoints. Dead specimens remain inspectable.
4. **Lineage tree and archive:** `A` opens a scrollable/paginated extinct archive; `Y` draws a clickable ancestor/selected/offspring family graph; `U` jumps to a parent, `K` to the latest direct child. A dead specimen remains selected instead of silently disappearing. Factually grounded one-time milestones are recorded and displayed, rather than simulated dialogue or narrative inventions.
5. **Neural microscope:** `O` shows the inherited 2 × 8 controller weights, current sensory inputs (when living), motor outputs, and recorded movement history count. Selecting a specimen starts a bounded saved location/energy trace (12 tracked IDs, up to 240 samples each).
6. **Layout fixes:** action controls now use two rows of seven at narrower widths; world status remains visible while the sidebar switches among specimen, events and lineage tabs instead of hiding its event list at minimum window size. Zoomed-out high populations use a cheaper dot level-of-detail renderer.
7. **Safer sandbox:** changing world layout or restarting requires the same shortcut twice within 6 seconds. Interventions continue to be marked in the checkpoint and the experiment code does not invoke the brush.
8. **Graphical QA instrumentation:** the viewer accepts `--smoke-frames`, `--screenshot`, `--qa-report` to record its *actual* rendered frame times and screenshot when Pygame is installed.
9. **Experiment 007:** full ecological reproduction, energy, harvesting, starvation and life-cycle tests for accurate, missing and mirrored food cues across 96 reproducible colony runs. See `docs/EXPERIMENT_007.md`.

## Compatibility

All original Experiments 001–006 and checkpoints are included. Older v0.6 (and earlier) `.npz` files load and can continue deterministically. Observational lifetime archives and detailed records *cannot be reconstructed retroactively* from a checkpoint that never stored them; history begins at the migration point for surviving organisms. New .npz files serialize the extra data and remain safe to load with `allow_pickle=False`.

The scientific movement, metabolism, resource and reproduction policies were not deliberately changed in v0.7. New counters and history sampling are observational only, with no added random draws. Older motor-only experiments remain available through their original commands.

## Verification status

Headless tests, simulation checkpoint continuity, ancestry persistence, CLI experiment runs, output reproducibility, and toolbar geometry have automated coverage. The viewer is still **not visually verified** on a machine with Pygame installed: this execution environment could not install pygame-ce (network/package index unreachable). The included smoke-command instrumentation can validate a graphical launch on a suitable Windows/Linux machine. Never describe static mockups as actual Pygame screenshots.
