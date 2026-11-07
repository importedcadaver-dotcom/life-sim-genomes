# Feature traceability and conversation-history reconciliation

**Method:** mapped each major promise in the conversation through v1.0 against current source, tests and available outputs. `Implemented` means code exists and relevant headless behavior can be tested; it does **not** imply real Windows GUI operation has passed. `Partial` means a simplified implementation or a meaningful caveat. `Not implemented` is not a bug if the feature was only proposed for the future.

| Feature first requested / announced | Implementation location | Verified status and caveat |
|---|---|---|
| v0.1 world: moving organisms, food, energy, death | `simulation.World.step`, `patch_landscape` | **Implemented.** Headless regression and deterministic replay tested |
| v0.1 evolving 16-weight sensorimotor controller | `simulation.perceive`, `.controls`, `World.genomes` | **Implemented.** Fixed network topology |
| v0.1–v0.4 spatial islands, walls, moving patches, scarcity | `Config`, `patch_landscape`, `simulation.step` | **Implemented.** Historical experiments retained |
| v0.2–v0.8 controlled sensory and steering ablations | `investigation`, `navigation`, `trajectory`, `fitness` | **Implemented.** Interpret claims as specific to each assay |
| v0.5 explorer controls/selection/magnifier | `viewer`, `viewer_presentation` | **Implemented in code; native SDL/Pygame runtime unverified** |
| v0.7 chronicle, death archive and ancestry | `World.life_archive`, `specimen`, `relatives`, `playful.Chronicle` | **Partial.** Long archive grows unbounded; sampled replay only, no world rewind |
| v0.7 neural microscope | `World.controls`, viewer overlay | **Implemented in code; native GUI unverified** |
| v0.7 event pause, paced simulation, restart confirmation | `SimulationClock`, viewer event dispatcher | **Implemented and headlessly tested; manual GUI interaction still needed** |
| v0.8 compact toolbar and legacy-tree crash repair | `viewer_presentation.layout_for`, viewer tree | **Implemented; older checkpoint QA fixture included** |
| v0.9 pink/lavender/peach/mint berry bugs | `playful.creature_color`, `viewer_presentation.draw_cute_organism` | **Implemented in code; PNG previews generated via stub** |
| v0.9 Sugar Rush cheats | `playful.cheat` | **Implemented.** Marked as interventions; baby clones generate energy intentionally |
| v0.9 Berry Hunt and Speed Detective | `playful.MiniGames` | **Implemented.** Two games, not a larger minigame collection; no RNG effects on ecology |
| v0.9 Twin-world A/B demonstration | `playful.PairedLab` | **Implemented.** One 100-step pair, not replicated science; original world stays unchanged |
| v0.9 saved notebook and stars | `playful.Chronicle.save/load`, viewer | **Implemented.** v1.0.1 adds checkpoint hash validation; older sidecars still accepted |
| v1.0 genes: 12 body loci, copy number 0–3 | `genetics`, `simulation.body_dna`, `.gene_copies` | **Implemented.** Fixed vocabulary, not new gene classes |
| v1.0 juvenile growth | `World.biology` | **Implemented.** Generic age-dependent scaling modulated by maturation locus |
| v1.0 one-/two-parent reproduction | `reproduction.reproduce_biological` | **Implemented.** Local pair matching, mixed/sexual/asexual modes |
| v1.0 mutation, crossover and natural selection | `genetics.mutate/recombine`, `reproduction` | **Implemented.** Selection via food/energy/survival, not deterministic fitness pruning |
| v1.0 mutation-vs-no-mutation and neutral drift studies | `genomic_experiment`, `selection_assay` | **Implemented.** Data archived, historic interpretation bounded |
| v1.0 DNA inspector and DNA Spark cheat | viewer DNA overlay, `playful.cheat` | **Implemented in code; GUI not native-verified** |
| New chromosomes or spontaneously new biochemical functions | No implementation | **Not implemented.** Requires new genotype/execution model; see expansion design |
| Predators, parasites, sex differentiation, rich social communication | No implementation | **Not implemented.** Future ideas, not silently missing features |
| World rewind with full past ecological state | No implementation | **Not implemented.** Current replay is only sampled selected-specimen movement |
| Native Windows packaged executable `.exe` | No implementation | **Not implemented.** Windows launcher runs Python source |
| Full Windows graphical QA | `tools/run_graphical_qa.py`, .bat launcher | **Not verified here**; requires actual SDL/Pygame on Windows |

## Important corrections to our earlier descriptions

- The historical v0.9 README described pretty inherited colors as cosmetic. In v1.0 some biological traits became functional, but **the pigment and spots loci remain cosmetic**. The current README now distinguishes those facts explicitly.
- Naming a fixed-locus copy-number change “gene duplication” is technically a structural mutation **within a preprogrammed gene family**; it does not invent a new function.
- A selected-creature chronicle replay is **not a reversible world simulation**.
- Cozy mode called “immortality” extends lifespan to 1,000,000 ticks and eliminates passive metabolic costs; it is not mathematically infinite life. This could be made a truly uncapped age switch in a later explicitly gameplay-changing release.
- “Science + cheats” works only because modified worlds are labeled. Cheat-assisted selection must never be presented as natural ecological evidence.
- A single A/B pair is an educational counterfactual demonstration, not a robust replicated evolutionary effect. v1.0.1 marks modified starting worlds as illustrative.
- Viewer and headless-run defaults differ deliberately for historical compatibility. Compare configs, not just seed numbers, across those modes.
- Test counts validate implemented source paths, not graphical polish or entire project correctness. The headless/Pillow QA adapter is not Pygame.

## What the conversation changed over time

1. **v0.1–0.4:** moved from a vague AI-life idea to measured resource competition and controlled movement/sensor experiments. The early “food seeking” interpretation was subsequently narrowed.
2. **v0.5–0.8:** introduced observation, archives, lineage, pacing, visuals and UI diagnostics. This increased the size and coupling of the viewer before native graphical runtime testing became possible.
3. **v0.9:** introduced cute pink visual identity, cheats, two games and a comparative lab. These are intentionally separated from the science engine but add integration risk and save-state complexity.
4. **v1.0:** added physiology, bounded biology loci, gene dosage, mutating juvenile phenotypes and mating. Genetics-enabled viewer defaults changed while preserving old headless experiments.
5. **v1.0.1:** reconciles the architecture, save format, observer pairing and docs **before** expanding into new gene types.

## Release gate for the next genetics milestone

The next version must pass every row above that affects persistence, selection, legacy mode and reproducibility, plus actual Windows graphical smoke/playtesting. Do not silently retire historical experimental entrypoints or interpret cosmetic markers as adaptations.
