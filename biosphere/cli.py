"""CLI: python -m biosphere ..."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import shutil
from .run_segments import check_resume_tick, plan_resume
from .simulation import Config, World


def simulate(args: argparse.Namespace) -> None:
    cfg = Config(founders=args.founders, max_population=args.max_population,
                 sensor_mode=args.sensor_mode, allow_mutation=not args.no_mutation,
                 mutation_strength=args.mutation_strength, growth_rate=args.growth_rate,
                 resource_patchiness=args.patchiness,
                 resource_background=(args.resource_background if args.resource_background is not None
                                      else (0.01 if args.resource_layout == "islands" else 0.25)),
                 resource_layout=args.resource_layout,
                 island_count=args.island_count, island_sigma=args.island_sigma,
                 island_peak=args.island_peak, boundary_mode=args.boundary_mode,
                 patch_shift_interval=args.patch_shift_interval, move_cost=args.move_cost,
                 genetics_enabled=getattr(args, "genetics", False) or getattr(args, "regulation", False),
                 regulation_enabled=getattr(args, "regulation", False),
                 regulatory_structure_rate=getattr(args, "regulatory_structural_rate", .04),
                 regulatory_point_rate=getattr(args, "regulatory_point_rate", .08),
                 reproduction_mode=getattr(args, "reproduction_mode", "mixed"),
                 body_mutation_probability=getattr(args, "body_mutation_rate", .045),
                 copy_mutation_probability=getattr(args, "copy_mutation_rate", .008))
    is_resume = bool(getattr(args, "resume", None) or getattr(args, "resume_latest", False))
    if not is_resume and (getattr(args, "overwrite", False) or getattr(args, "segment", None)):
        raise ValueError("--overwrite and --segment require a resumed run")
    plan = (plan_resume(Path(args.output), getattr(args, "resume", None),
                        latest=getattr(args, "resume_latest", False),
                        segment=getattr(args, "segment", None),
                        overwrite=getattr(args, "overwrite", False)) if is_resume else None)
    world = World.load(plan.source) if plan is not None else World(cfg, seed=args.seed)
    if plan is not None:
        plan = check_resume_tick(plan, world.tick)
        out = plan.stage()
    else:
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
    try:
        _write_run(world, args, out)
        if plan is not None:
            plan.publish(out, world.tick)
            print(f"Latest checkpoint: {(plan.target / 'world.npz').resolve()}")
    except BaseException:
        if plan is not None:
            shutil.rmtree(out, ignore_errors=True)
        raise


def _write_run(world: World, args: argparse.Namespace, out: Path) -> None:
    if getattr(args, "disk_archive", False) and not hasattr(world.life_archive, "snapshot_bytes"):
        world.enable_disk_archive(out / "long_life_archive.sqlite")
    with (out / "metrics.csv").open("w", newline="", encoding="utf-8") as metrics, \
         (out / "lineage.csv").open("w", newline="", encoding="utf-8") as lineage:
        writer = csv.DictWriter(metrics, fieldnames=list(world.stats().keys()))
        writer.writeheader()
        lw = csv.DictWriter(lineage, fieldnames=["tick", "kind", "id", "parent_id", "parent2_id", "generation", "cause", "x", "y"], extrasaction="ignore")
        if args.events:
            lw.writeheader()
        writer.writerow(world.stats())
        for _ in range(args.steps):
            stats = world.step()
            if args.events:
                for event in world.last_events:
                    lw.writerow(event)
            if world.tick % args.sample_every == 0 or world.population == 0:
                writer.writerow(world.stats(stats["births"], stats["deaths"]))
            if world.population == 0:
                print(f"Population went extinct at tick {world.tick}.")
                break
    world.save(out / "world.npz")
    report = {"seed": world.seed, "steps_completed": world.tick,
              "config": vars(world.config), "final": world.stats(),
              "death_causes": world.death_causes}
    (out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["final"], indent=2))
    if not getattr(args, "resume", None) and not getattr(args, "resume_latest", False):
        print(f"Files written to {out.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="biosphere", description="An evolving digital ecosystem")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run", help="Headless reproducible evolution")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--steps", type=int, default=3000)
    p.add_argument("--founders", type=int, default=180)
    p.add_argument("--max-population", type=int, default=900)
    p.add_argument("--sensor-mode", choices=("normal", "blind", "food_blind", "crowd_blind", "mirror_food"), default="normal")
    p.add_argument("--no-mutation", action="store_true")
    p.add_argument("--genetics", action="store_true", help="Enable multi-trait inheritable biology")
    p.add_argument("--regulation", action="store_true", help="Enable evolvable gene-regulatory chromosomes (implies --genetics)")
    p.add_argument("--regulatory-structural-rate", type=float, default=.04)
    p.add_argument("--regulatory-point-rate", type=float, default=.08)
    p.add_argument("--reproduction-mode", choices=("mixed", "sexual", "asexual"), default="mixed")
    p.add_argument("--body-mutation-rate", type=float, default=.045)
    p.add_argument("--copy-mutation-rate", type=float, default=.008)
    p.add_argument("--mutation-strength", type=float, default=0.28)
    p.add_argument("--growth-rate", type=float, default=0.030)
    p.add_argument("--patchiness", type=float, default=1.0)
    p.add_argument("--resource-layout", choices=("hills", "islands"), default="hills")
    p.add_argument("--resource-background", type=float,
                   help="Background food capacity (defaults: 0.25 hills, 0.01 islands)")
    p.add_argument("--island-count", type=int, default=8)
    p.add_argument("--island-sigma", type=float, default=2.8)
    p.add_argument("--island-peak", type=float, default=10.0)
    p.add_argument("--boundary-mode", choices=("wrap", "reflect"), default="wrap")
    p.add_argument("--patch-shift-interval", type=int, default=0)
    p.add_argument("--move-cost", type=float, default=0.065)
    resumes = p.add_mutually_exclusive_group()
    resumes.add_argument("--resume", type=Path)
    resumes.add_argument("--resume-latest", action="store_true",
                         help="Resume from the latest completed segment checkpoint")
    p.add_argument("--overwrite", action="store_true",
                   help="Explicitly replace only an existing terminal resume segment")
    p.add_argument("--segment", help="Terminal segment-NNNNNN to replace with --overwrite")
    p.add_argument("--sample-every", type=int, default=25)
    p.add_argument("--events", action="store_true", help="Save every birth/death to lineage.csv")
    p.add_argument("--disk-archive", action="store_true", help="Store deceased organisms in SQLite instead of RAM")
    p.add_argument("--output", default="results/run")
    p.set_defaults(func=simulate)
    v = sub.add_parser("view", help="Pygame ecosystem viewer")
    v.add_argument("--seed", type=int, default=1)
    v.add_argument("--window-width", type=int, default=1400)
    v.add_argument("--window-height", type=int, default=880)
    v.add_argument("--qa-script", type=Path, help="JSON list of reproducible viewer QA inputs")
    v.add_argument("--smoke-frames", type=int, default=0,
                   help="Exit automatically after N rendered frames for graphical QA")
    v.add_argument("--screenshot", type=Path,
                   help="Save a rendered window image at the end of --smoke-frames")
    v.add_argument("--qa-report", type=Path,
                   help="Write real graphical frame-time measurements when the viewer exits")
    v.add_argument("--resume", type=Path)
    v.add_argument("--max-population", type=int, default=900)
    v.add_argument("--legacy-genetics", action="store_true", help="Use the old neural-only ecology")
    v.add_argument("--no-regulation", action="store_true", help="Use fixed 12-locus biology without regulatory genes")
    v.add_argument("--reproduction-mode", choices=("mixed", "sexual", "asexual"), default="mixed")
    v.add_argument("--body-mutation-rate", type=float, default=.045)
    v.add_argument("--copy-mutation-rate", type=float, default=.008)
    v.add_argument("--boundary-mode", choices=("wrap", "reflect"), default="wrap")
    v.add_argument("--patch-shift-interval", type=int, default=0)
    v.add_argument("--move-cost", type=float, default=0.065)
    v.add_argument("--resource-layout", choices=("hills", "islands"), default="hills")
    v.add_argument("--resource-background", type=float,
                   help="Background food capacity (defaults: 0.25 hills, 0.01 islands)")
    v.add_argument("--island-count", type=int, default=8)
    v.add_argument("--island-sigma", type=float, default=2.8)
    v.add_argument("--island-peak", type=float, default=10.0)
    v.set_defaults(func=lambda a: __import__("biosphere.viewer", fromlist=["view"]).view(a))
    va = sub.add_parser("gene-selection", help="Controlled selection-versus-drift ecology assay")
    va.add_argument("--seed-start", type=int, default=12)
    va.add_argument("--seeds", type=int, default=12)
    va.add_argument("--ticks", type=int, default=700)
    va.add_argument("--output", type=Path, default=Path("results/gene_selection"))
    def gene_assay(a):
        from .selection_assay import run_assay
        report = run_assay(seeds=list(range(a.seed_start, a.seed_start + a.seeds)),
                           ticks=a.ticks, output=a.output)
        print(json.dumps(report["conditions"], indent=2))
    va.set_defaults(func=gene_assay)
    g = sub.add_parser("genomics", help="Replicated DNA evolution, mutation controls, local CPU parallelism")
    g.add_argument("--seed-start", type=int, default=1001)
    g.add_argument("--seeds", type=int, default=6)
    g.add_argument("--ticks", type=int, default=900)
    g.add_argument("--founders", type=int, default=75)
    g.add_argument("--capacity", type=int, default=250)
    g.add_argument("--workers", type=int, default=1)
    g.add_argument("--reproduction", choices=("mixed", "asexual", "sexual"), default="mixed")
    g.add_argument("--growth", type=float, default=.008)
    g.add_argument("--sample-every", type=int, default=50)
    g.add_argument("--no-control", action="store_true", help="Skip mutation-disabled matched controls")
    g.add_argument("--output", type=Path, default=Path("results/genetics_study"))
    def genomics_run(a):
        from .genomic_experiment import run_study
        report = run_study(seeds=list(range(a.seed_start, a.seed_start + a.seeds)),
                           ticks=a.ticks, output=a.output, founders=a.founders,
                           capacity=a.capacity, workers=a.workers,
                           compare_mutations=not a.no_control,
                           reproduction=a.reproduction, growth=a.growth,
                           sample_every=a.sample_every)
        print(json.dumps({"mutation_enabled": report["mutation_enabled"],
                          "mutation_disabled": report["mutation_disabled"]}, indent=2))
        print(f"Raw DNA trajectories saved in {a.output}")
    g.set_defaults(func=genomics_run)
    e = sub.add_parser("experiment", help="Multi-seed controlled selection experiment")
    e.add_argument("--seeds", type=int, default=6)
    e.add_argument("--steps", type=int, default=2200)
    e.add_argument("--probe-ticks", type=int, default=260)
    e.add_argument("--output", type=Path, default=Path("results/experiment"))
    e.set_defaults(func=lambda a: __import__("biosphere.experiment", fromlist=["run_experiment"]).run_experiment(a))
    inv = sub.add_parser("investigate", help="Holdout tests of movement and regrowth scarcity")
    inv.add_argument("--seed-start", type=int, default=101)
    inv.add_argument("--seeds", type=int, default=18)
    inv.add_argument("--steps", type=int, default=1200)
    inv.add_argument("--probe-ticks", type=int, default=240)
    inv.add_argument("--output", type=Path, default=Path("results/experiment_002"))
    inv.set_defaults(func=lambda a: __import__("biosphere.investigation", fromlist=["run_investigation"]).run_investigation(
        seeds=list(range(a.seed_start, a.seed_start+a.seeds)), steps=a.steps,
        probe_ticks=a.probe_ticks, output=a.output))
    env = sub.add_parser("environment", help="Experiment 003: boundary conditions and habitat shifts")
    env.add_argument("--seed-start", type=int, default=401)
    env.add_argument("--seeds", type=int, default=8)
    env.add_argument("--steps", type=int, default=900)
    env.add_argument("--probe-ticks", type=int, default=160)
    env.add_argument("--count", type=int, default=160)
    env.add_argument("--output", type=Path, default=Path("results/experiment_003_custom"))
    env.add_argument("--no-checkpoints", action="store_true")
    env.set_defaults(func=lambda a: __import__("biosphere.environment", fromlist=["run_environment_experiment"]).run_environment_experiment(
        seeds=list(range(a.seed_start, a.seed_start+a.seeds)), steps=a.steps,
        probe_ticks=a.probe_ticks, count=a.count, output=a.output,
        save_checkpoints=not a.no_checkpoints))
    nav = sub.add_parser("navigation", help="Experiment 004: separated food islands & navigation ablations")
    nav.add_argument("--seed-start", type=int, default=701)
    nav.add_argument("--seeds", type=int, default=8)
    nav.add_argument("--steps", type=int, default=1000)
    nav.add_argument("--probe-ticks", type=int, default=180)
    nav.add_argument("--count", type=int, default=120)
    nav.add_argument("--output", type=Path, default=Path("results/experiment_004_custom"))
    nav.add_argument("--no-checkpoints", action="store_true")
    nav.set_defaults(func=lambda a: __import__("biosphere.navigation", fromlist=["run_navigation_experiment"]).run_navigation_experiment(
        seeds=list(range(a.seed_start, a.seed_start+a.seeds)), steps=a.steps,
        probe_ticks=a.probe_ticks, count=a.count, output=a.output,
        save_checkpoints=not a.no_checkpoints))
    iso = sub.add_parser("isolate", help="Experiment 004B: steering-only causal ablations at fixed speed")
    iso.add_argument("--seed-start", type=int, default=701)
    iso.add_argument("--seeds", type=int, default=8)
    iso.add_argument("--count", type=int, default=120)
    iso.add_argument("--probe-ticks", type=int, default=180)
    iso.add_argument("--trained-results", type=Path, default=Path("results/experiment_004"))
    iso.add_argument("--output", type=Path, default=Path("results/experiment_004"))
    iso.set_defaults(func=lambda a: __import__("biosphere.navigation", fromlist=["run_motor_isolation"]).run_motor_isolation(
        seeds=list(range(a.seed_start, a.seed_start + a.seeds)), count=a.count,
        probe_ticks=a.probe_ticks, trained_results=a.trained_results, output=a.output))
    res = sub.add_parser("residency", help="Experiment 005: separate search from patch exploitation")
    res.add_argument("--seed-start", type=int, default=701)
    res.add_argument("--seeds", type=int, default=8)
    res.add_argument("--ticks", type=int, default=75)
    res.add_argument("--trained-results", type=Path, default=Path("results/experiment_004"))
    res.add_argument("--output", type=Path, default=Path("results/experiment_005"))
    res.set_defaults(func=lambda a: __import__("biosphere.residency", fromlist=["run_residency"]).run_residency(
        seeds=list(range(a.seed_start, a.seed_start + a.seeds)), ticks=a.ticks,
        trained_results=a.trained_results, output=a.output, progress=True))
    tr = sub.add_parser("trajectory", help="Experiment 006: barren-patch sensory counterfactuals")
    tr.add_argument("--seed-start", type=int, default=701)
    tr.add_argument("--seeds", type=int, default=8)
    tr.add_argument("--ticks", type=int, default=90)
    tr.add_argument("--trained-results", type=Path, default=Path("results/experiment_004"))
    tr.add_argument("--output", type=Path, default=Path("results/experiment_006"))
    tr.set_defaults(func=lambda a: __import__("biosphere.trajectory", fromlist=["run_trajectory_experiment"]).run_trajectory_experiment(
        seeds=list(range(a.seed_start, a.seed_start + a.seeds)), ticks=a.ticks,
        trained_results=a.trained_results, output=a.output, progress=True))
    ft = sub.add_parser("fitness", help="Experiment 007: ecological reproduction under food-cue interventions")
    ft.add_argument("--seed-start", type=int, default=701)
    ft.add_argument("--seeds", type=int, default=8)
    ft.add_argument("--ticks", type=int, default=350)
    ft.add_argument("--count", type=int, default=80)
    ft.add_argument("--growth-rate", type=float, default=.012)
    ft.add_argument("--trained-results", type=Path, default=Path("results/experiment_004"))
    ft.add_argument("--output", type=Path, default=Path("results/experiment_007"))
    ft.set_defaults(func=lambda a: __import__("biosphere.fitness", fromlist=["run_fitness"]).run_fitness(
        seeds=list(range(a.seed_start, a.seed_start + a.seeds)), ticks=a.ticks,
        count=a.count, growth_rate=a.growth_rate, trained_results=a.trained_results,
        output=a.output, progress=True))
    args = parser.parse_args()
    if hasattr(args, "sample_every") and args.sample_every < 1:
        parser.error("--sample-every must be positive")
    args.func(args)

if __name__ == "__main__":
    main()
