# v0.8 viewer quality audit: results and remaining graphical gate

## What was executed here

- Unpacked the shipped v0.7 project and passed its original 76 unit tests.
- The container had **no `pygame` module**; a `pygame-ce` install failed with package-index DNS errors. There was therefore **no real SDL/Pygame window**, GPU performance test, or Windows-specific graphical runtime available here.
- Built `tools/pygame_preview_stub.py`, a **Pillow-based diagnostic adapter** for the subset of drawing calls the real `biosphere.viewer` uses. It runs the actual viewer control-flow/drawing code and records screenshots, **but does not execute the real Pygame drawing backend**.
- Exercised layouts at 1020×685, 1400×880, and 1920×1080 and tested simulated inputs for microscope, archive, historical pedigree, nutrient brushing, clicking the toolbar, and resizing.
- Caught a **confirmed v0.7 crash** with a legacy checkpoint: selecting the family tree for a living specimen whose ancestor biography was never saved dereferenced `None['generation']`. Fixed in v0.8 with an explicit unavailable-record node. A second confusing case—924 historical deaths but zero archived biographies—now explains the missing history rather than showing a blank view.
- Observed truncation of minimum-window labels and the bottom help text. Revised compact buttons, footer text and sidebar headings. New startup auto-selection creates an immediate subject to inspect without changing evolutionary behavior.
- Added a terrain-surface cache and deceased-archive sorting cache, both invalidated on relevant changes; this avoids redundant work in paused/slow-motion frames and repeated sorting of the same death records. **Actual Pygame frame rates are not yet measured.**

## How to complete the REAL graphical tests on Windows

1. Extract this release and double-click `run_graphical_qa_windows.bat`.
2. It launches the real Pygame window at three sizes, drives a small scripted input sequence, and writes actual SDL screenshots and `results/qa_windows/summary.json`.
3. Review the generated screenshots for text clipping, control legibility, heatmap artifacts, and overlay geometry. Inspect mean and p95 frame-work times; they exclude the frame limiter and desktop compositor.
4. Double-click `run_windows.bat` to interact manually: drag/pan/zoom, inspect a specimen, enable event pause (`P`), click the food brush, save (`S`), reload, open archive, and follow the selected organism. Test both a new world and a loaded old checkpoint.

The launcher does not promise to control the user's Windows machine from this session. It runs only once the user executes it on a Windows computer with Python and install access.

## Automated QA scenarios

The real SDL runner uses `python -m biosphere view --smoke-frames 12 --qa-script <scenario.json> --screenshot <file> --qa-report <json>`.

| Scenario | Expected outcome |
| --- | --- |
| Startup 1020×685 / 1400×880 / 1920×1080 | World draws and a living organism is preselected |
| Microscope (`O`) | Real sensor/weight overlay opens |
| Toolbar click | On-screen TREE button opens pedigree without using a key |
| Legacy tree | Old checkpoint with missing ancestor biographies does not crash |
| Sandbox (`T` and map click) | Exactly one intervention logged |
| Resize | Recomputed window and map size remains valid |
| Pause (`Space`) | Clock pauses |
| Restart confirmation (`R` twice) | Confirmation path executes without crashing |

## Remaining risks

- Windows installation and genuine human mouse/resize interactions are unverified **in this authoring environment**. Synthetic events and static diagnostic screenshots cannot close those gaps.
- SDL renderer performance at hundreds of organisms needs the actual Pygame test. Pillow preview timing must **not** be reported as Pygame FPS.
- The viewer is an observatory, not a conventional goal-driven game. Inspecting an individual and choosing experimental conditions are its primary interactions, and it has no scripted creature personalities.
- Legacy checkpoints cannot reconstruct extinct organisms' biographies or samples that were never stored. This is an unavoidable historical data limitation, not a rendering error.
