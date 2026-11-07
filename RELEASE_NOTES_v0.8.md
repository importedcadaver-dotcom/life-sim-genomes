# v0.8 — Living Observatory QA and interaction repairs

## Scope

Focused quality release based on v0.7. **No new evolutionary mechanism or experiment is claimed.** The scientific engine and original experimental CSVs/checkpoints remain intact. Viewer code was revised after running a Pillow-backed execution of the drawing logic at common sizes and with scripted input events. That is **not** a genuine Pygame/Windows runtime certification.

## Confirmed fixes

1. **Legacy family-tree crash:** older checkpoints may include a live organism with a parent ID whose biography was never archived. The pedigree previously dereferenced missing record data and crashed. Those ancestor nodes now say *unknown*, and the parent shortcut explicitly explains why the ancestor cannot be opened.
2. **Misleading empty archive:** pre-v0.7 checkpoints may report historical deaths with no stored death biographies; the archive now explains this limitation, and newly recorded deaths will appear as the world continues.
3. **Min-window truncation:** compact toolbar descriptions, shorter footer and sidebar headings now fit the 1020×685 diagnostic preview. Hovered toolbar buttons offer fuller explanations in a tooltip.
4. **Blank initial inspector:** the viewer automatically highlights one existing living organism on startup and restarts, activating real observational trace capture without new RNG draws. Event pausing is opt-in so this does not immediately interrupt a new run.
5. **Unclear lifetime labels:** founders are identified as founders, unrecorded first-meal ticks are described as *not observed*, and legacy family displays show known linked offspring rather than contradictory zero-count claims.
6. **Short sidebar overflow:** a child selection button is hidden when the available panel height is too small to contain it.
7. **Resize path:** a single resize handler clamps both dimensions to the minimum supported layout.
8. **Redundant rendering work:** terrain surfaces are cached while simulation ticks, environmental interventions, zoom and resource view remain unchanged; archive sorting is reused while deaths are unchanged. Pygame frame-rate gains are **not quantified** here.

## New QA tools

- `--window-width` / `--window-height` to start at a specific screen size.
- `--qa-script tools/qa_scripts/<name>.json` to replay bounded mouse/keyboard/resize input scenarios. Results include current UI state and intervention count in `--qa-report` JSON.
- `run_graphical_qa_windows.bat`: one-click **actual Pygame** SDL smoke-test suite for Windows; saves screenshot files and a JSON pass/fail summary.
- `tools/pygame_preview_stub.py`: development-only, Pillow-rendered visual diagnostic that exercises the same viewer drawing path but **is not** the real Pygame backend.
- `docs/GRAPHICAL_QA_v0.8.md`: exact checks performed, limits, and Windows testing instructions.

## Verification and caveats

- All prior v0.7 tests remained passing. The additional tests cover minimum-window geometry, QA scripts, microscope render path, old checkpoint family tree, toolbar click, sandbox intervention and resize events.
- Real Pygame was unavailable here because `pygame-ce` could not be installed over the blocked package network. Real frame rate and genuine Windows mouse/event handling therefore remain unverified.
- Original `biosphere/simulation.py` was not modified and all experiment 001–007 data are retained.
