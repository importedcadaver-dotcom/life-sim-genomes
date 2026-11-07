# v0.7 — Graphical QA protocol and honest coverage

## Environment limitation

Pygame Community Edition was not installed in the execution environment; a package installation attempt failed due to package-repository DNS access. The **graphical viewer has not been runtime-verified** by this release author. Layout geometry, pygame-independent logic, checkpoint compatibility and headless simulation **are** tested. Actual window screenshots or render-FPS observations cannot be asserted here.

## Reproduce the graphical smoke test

Install dependencies in a Windows terminal within the extracted project:

```powershell
py -3 -m pip install -r requirements.txt
py -3 -m biosphere view --seed 701 --smoke-frames 120 --screenshot results/viewer/qa_startup.png --qa-report results/viewer/qa_startup.json
py -3 -m biosphere view --resume results/experiment_004/checkpoints/seed_701_islands_costly.npz --smoke-frames 120 --screenshot results/viewer/qa_evolved.png --qa-report results/viewer/qa_evolved.json
```

If using Linux with pygame-ce installed but no display, run with `SDL_VIDEODRIVER=dummy` for a headless SDL rendering smoke test; it is not equivalent to verifying real mouse or resize behavior. The JSON report measures actual frame work excluding the frame limiter and the desktop compositor, not guaranteed end-user FPS.

## Manual visual/gameplay checklist (requires real graphical runtime)

- Open a 1020 × 685 window: all 14 toolbar actions should be clickable in two rows, sidebar specimen/event/lineage tabs visible, no overlap with terrain.
- Resize to 1400 × 880 and 1920 × 1080; inspect terrain clipping and map-hit accuracy at each size.
- Select a moving specimen, press `L` to follow, `O` for the neural microscope, `Y` for the pedigree graph, `A` for extinct-specimen archive and wheel/PageDown to browse older deaths.
- Press `P` to enable pause-on-selected-events, fast-forward until that specimen dies or has offspring, and verify the viewer pauses and still shows the dead specimen's history.
- Press `R` once: no loss of population. Press `R` again within six seconds: confirms reset. Repeat for `I` (terrain switch).
- Run at 200–600 ticks/sec and look for skipped or misaligned event rings. Event markers should last approximately 4.5 wall-clock seconds, independent of sim rate.
- Save with `S`; restart from `python -m biosphere view --resume <saved.npz>`; check restored archive, genealogy, population history and selected traces (selection itself must be re-established).
- Select the FOOD BRUSH; click terrain; verify it is visibly labeled INTERVENED; save and reload to verify manipulation recorded.
- Open microscope for a living creature and an archived dead one; real sensory values are only available for the living specimen.
- Inspect large-population rendered frame times with `--qa-report` and compare zoomed out versus zoomed in. At high populations the zoomed-out renderer switches to simpler dots.

## Measured headless engine performance (not frame rate)

On this particular container's Python 3.13.5 environment, a 500-tick, 900-founder run with reproduction disabled averaged approximately **0.58 milliseconds per simulation tick**, ending in extinction at lifespan; a 1,200-tick ordinary growing run averaged **0.88 milliseconds per tick**, with a 900-organism final population. Timings include new life-history logging and are **not** measurements of GUI rendering or Windows performance. Always retest locally.

## Remaining known limitations

- Graphical launch/resize/mouse QA cannot be certified until pygame-ce is installed in a graphical environment.
- The archived event feed stores the most recent 3,500 events while full dead-individual lifetime summaries remain in the archive. This is deliberate to avoid unbounded event UI history.
- Detailed per-step positions are tracked only **after an organism is selected**, for at most 12 specimens with 240 samples each. The simulation does not claim to reconstruct trajectories it never recorded.
- Long simulations accumulate lifetime archive entries. Population control limits living entities, not the total lifetime archive; output files will grow with births/deaths. Future work should add an optional archival export/segmentation policy for million-generation runs.
- The viewer is a scientific 2D observatory and sandbox, not a dialogue-driven strategy game; behaviors are not labeled as intelligent unless supported by experiments.
