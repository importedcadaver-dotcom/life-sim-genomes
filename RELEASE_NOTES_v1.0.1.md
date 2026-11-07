# 1.0.1 — Pre-expansion engineering audit and maintenance

**Scope:** software quality, consistency, legibility and scientific reproducibility. **No experimental biology enhancements introduced.**

## Changes

1. Extracted the entire local-mating/sexual-asexual reproductive routine into `biosphere/reproduction.py`. `World` retains a backwards-compatible `_reproduce_biological` wrapper. Neural-only and genetics engines retain their original trajectory behavior.
2. Extracted GUI geometry, wall-clock pacing, QA-script validation, terrain color mapping and cute creature rendering into `biosphere/viewer_presentation.py`. Previous imports from `biosphere.viewer` still work.
3. Introduced `biosphere/state_schema.py`, with a single list of 21 organism-aligned arrays used for both death-retention and checkpoint saving. Checkpoints are versioned and validated before save and after load.
4. Checkpoint writing to a filesystem path now uses same-directory temporary files and an atomic `os.replace`, reducing partial-save corruption. Existing in-memory `BytesIO` cloning still works.
5. Invalid NaN/infinite and negative physical model configuration values are rejected; malformed checkpoint array shapes, ID duplicates, gene-copy values and unsupported future checkpoint schema versions fail with explicit errors.
6. Preserved older checkpoint formats and their default-missing data arrays. A missing or older death-causes field now defaults safely to a valid dictionary.
7. New observer notebooks can carry a hash of their paired checkpoint. Opening a notebook from another world is refused; older notebooks without a hash stay readable. GUI warns when the notebook is ignored.
8. Twin-world comparisons started from a cheated/intervened source world are explicitly marked illustrative; a single paired comparison is not a replicated scientific result.
9. Added `requirements-viewer.txt` to avoid installing the plotting dependency merely to launch the Windows viewer. Original full requirements remain available.
10. Rewrote the top-level README as a short current reference; archived the long historical README in `docs/README_HISTORY_v1.0.md` to avoid mixing outdated version promises with current controls.
11. Added `tools/audit_project.py`, cross-feature regression tests and handoff/expansion documentation.

## Verified / not verified

- All original 113 tests plus new maintenance tests pass in this environment.
- Four simulation modes (legacy, asexual, mixed, sexual islands) produce exactly the same 320-tick fingerprints as v1.0 under the same Python/NumPy environment.
- Headless CLI commands (`run`, `genomics`, `gene-selection`) completed short smoke runs.
- Runtime Pygame QA **not performed** here; remains a release gate.
- `pytest` source coverage does not establish the GUI event loop is fully covered.

## Unresolved engineering debt

- The main Pygame view function is still large and heavily stateful. Avoid sweeping changes until real graphical playback and interaction verification.
- The entire deceased-organism archive remains resident and grows without bound. Long-run archival indexing, snapshot/trajectory compression and quota policy are future work.
- Versioned simulation data schemas are still fundamentally fixed-width; evolvable gene types/chromosomes require a new model and a migration plan.
- Mixed default modes are intentional for history, but must be labeled in experiments: viewer starts genetics-on; headless `run` defaults genetics-off.
- Python, NumPy and graphical dependency versions are broadly bounded, not locked, so exact cross-environment replay is not promised.
