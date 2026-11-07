# Pink Living Observatory v0.9 — Play and research separation

The cute organism appearance uses **real genome values only as a decorative color choice**. Pink, lavender, peach and mint bodies have ears, eyes, blush, a nose and a small heading marker. Pink color is not a new phenotype, fitness advantage or evolved body structure. Changing the renderer does not change the controller or biological update loop.

## How to play

| Input | Feature |
|---|---|
| **Q** or CHEATS | Open Sugar-Rush cheats: Candy Rain (refill all food); Cupcake (+40 energy to selected creature); Baby Parade (up to eight cloned offspring); Cozy Forever (disable aging and passive energy costs). Keys **1–4** apply the corresponding cheat. |
| **E** or GAMES | Choose Berry Hunt or Speed Detective, then press **1–3** or click a candidate. A correct answer earns one observer star. Repeated answers cannot earn extra credit. |
| **D** or CHRONICLE | Bookmark a selected specimen, examine recent factual birth/death events, replay a sampled movement trace; exported with `S` save. |
| **W** or A/B LAB | Start two *separate cloned worlds*, one with unchanged rules and one with half regrowth, doubled motion cost or food sensors disabled. Choose with keys **1–3**. Read the descriptive differences after 100 cloned ticks. The original habitat does not advance while the modal is open. |
| **Y** or TREE | Browse direct family connections; paginate past the first nine children. |
| **S** | Save the complete `.npz` world, screenshot, and `.npz.observer.json` file. If an A/B lab exists, its descriptive report is saved too. |

**Scientific integrity:** Every cheat changes a saved world and adds a `manual_interventions` entry, prominently marking it as **INTERVENED — not a control run**. No cheats are applied to Experiment 001–008 datasets. The games use real food-stock or controller-speed measurements at the moment the challenge starts. They use a separate random generator and cannot change the source-world simulation or its RNG state. The A/B lab clones and advances two independent worlds with paired starting conditions, never edits the source habitat and is **not** a statistically replicated scientific experiment.

**Observational replay is not time travel.** The Chronicle follows saved positions of bookmarked creatures. It cannot rewind the original world, undo deaths, edit history or reconstruct unknown life histories from checkpoints made before v0.7. Up to 16 bookmarked creatures, 2,000 recent track samples per creature (sampled every 3 world ticks), and 8,000 recent event entries are retained in the observer sidecar. The simulation's built-in life archive remains separately preserved in the world checkpoint and is not silently fabricated when historical records are unavailable. Old events beyond the observer cache limit are *not* available as an infinite journal, so large-run archival export is future work.

**Graphical caveat:** The PNG previews in `results/v09_preview/` execute the actual Python viewer drawing logic through a Pillow-backed surrogate. They are **not screenshots from an installed Pygame window**. Use `run_graphical_qa_windows.bat` on a Windows machine with Pygame installed to measure actual SDL rendering. Viewer performance, device font behavior and genuine mouse interaction remain unverified on Windows.

## v1.0 Genetic Life

Fresh viewer worlds now have active inheritable biological DNA. Click a specimen and press **G** to open its genome lab. The locus values, copy numbers, adult-size modifiers and ancestry are measured from the simulation, not fabricated personalities. Press **Q**, then **5** for **DNA Spark**, an explicitly logged edit to the selected living genome. Pastel coat colors, spots and juvenile growth reflect the DNA. The headless research engine keeps neural-only history as its default unless `--genetics` is enabled. See `docs/GENETICS_v1.0.md`.
