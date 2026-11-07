# Research foundation and provenance

These are **external primary or scholarly sources**, not claims that we implemented these systems directly. Accessed for this project on 2026-11-02.

## 1. Tierra — code as a digital organism

**Thomas S. Ray**, *An Approach to the Synthesis of Life* (1991), Artificial Life II. Author's publication list: <https://www.tomray.me/pubs/>. A 1995 technical report by Agnès Charrel at ATR explains Tierra's virtual instruction set and self-replicating programs: <https://results.atr.jp/35th/techreport/TR-H-0145/index_e.html>.

**What matters:** Tierra's organisms consist of programs executed in a virtual machine. Replication is computationally implemented by those digital programs. It provides a much stronger platform for studying code-level parasites and ecological computation than a fixed neural-weight genome can. Our organisms do not self-copy their own code; the engine implements inheritance, so we should **not** claim to reproduce Tierra's open-endedness.

## 2. Avida — controlled evolution experiments

**Charles Ofria and Claus O. Wilke**, *Avida: a software platform for research in computational evolutionary biology* (2004), Artificial Life; record at Caltech: <https://authors.library.caltech.edu/records/2h3br-gvn73>.

**Michigan State University**, ICER research highlight, *The Study of Evolution in Artificial Organisms*: <https://icer.msu.edu/research-services/folder-of-research-highlights/the-study-of-evolution-in-artificial-organisms>.

**Avida-ED** website: <https://avida-ed.github.io/>.

**What matters:** controlled random seeds, manipulations of evolutionary conditions, actual heritable change and comparable measurable outcomes. We therefore store restorable random states and evaluate evolved genomes in **fresh common gardens**, including sensory and mutation controls. Avida's instruction-based self-replicators remain substantially more general than our fixed-size linear brains.

## 3. Polyworld — sensors, movement and ecological neural evolution

**Larry Yaeger / Steven Williams**, *Evolution of Neural Dynamics in an Ecological Model*, Geosciences 7(3), 49 (2017): <https://www.mdpi.com/2076-3263/7/3/49>.

**Yaeger's Polyworld architecture** described in peer-reviewed work: <https://pmc.ncbi.nlm.nih.gov/articles/PMC2801533/>.

**Gary R. Greenfield**, *Graphical Evolution Experiments in Artificial Life* (1993), technical report describing early Polyworld: <https://scholarship.richmond.edu/mathcs-reports/10/>.

**What matters:** let animal-like agents process sensory information with an inherited controller and compete within a shared ecology. Our implementation uses only a **single linear layer plus nonlinear output functions**, not Polyworld's configurable group-based networks or within-life synaptic learning. We also do **not** explicitly code behavior-specific motor channels such as attack or mate; only turn and movement magnitude are evolvable.

## 4. Evolutionary neural agents and emergent networks

**Adami Lab**, Michigan State University, research description: <https://adami.natsci.msu.edu/lab-research>. It describes evolution of behavior and intelligence in simulations and ecological specialization. A peer-reviewed Avida example is **Evolving Digital Ecological Networks**, PLOS Computational Biology (2013): <https://doi.org/10.1371/journal.pcbi.1002928>.

**What matters:** improvements in task performance can be measured, but counterfactuals are essential. It is not enough that an agent appears to navigate toward something. We tested whether genomes transferred into new environments acquire more resources than ancestors and whether removing their senses reduces that performance.

## Architectural choice

For a self-contained first build aimed at visible behavior and repeatable experiments, we chose:

- NumPy vectorized arrays for ecology and evolution: fewer dependencies and faster headless runs than starting with a complex 3D engine.
- Fixed-weight, inherited 8-to-2 neural controllers: elementary interpretable capacity but not open-ended programming.
- Pygame as a **thin optional viewer**; no simulation rules depend on a window's frame rate.
- Counterfactual common-garden trials: six independent evolutionary seeds and paired new landscapes.

The central scientific risk is **mistaking a controller capacity designed by us for a behavior discovered by evolution**. We *did* design egocentric food sensors, directional contrasts, energy gates and food patches. What is unprogrammed is **which movement response** each genome will use, and whether natural selection increases the success of its response. That narrow point is what Experiment 001 addresses.
