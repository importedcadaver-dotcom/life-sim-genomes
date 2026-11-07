"""Genetics v1.0: inheritance, energy-accounting, mutation, controls & replay."""
import csv
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from biosphere.genetics import LOCI, INDEX, founder_dna, mutate, phenotype_summary, recombine
from biosphere.genomic_experiment import run_study
from biosphere.playful import cheat, creature_color
from biosphere.simulation import Config, World


def small(mode="mixed", **kwargs):
    return World(Config(width=20, height=20, founders=12, max_population=75,
                        genetics_enabled=True, reproduction_mode=mode, **kwargs), seed=17)


def test_fixed_locus_names_are_distinct_and_matched_to_shapes():
    assert len(LOCI) >= 10
    assert len(set(LOCI)) == len(LOCI)
    gen = founder_dna(np.random.default_rng(13), 21)
    assert gen.dna.shape == (21, len(LOCI))
    assert np.all(gen.copies == 1)
    assert np.std(gen.dna) > 0


def test_point_and_copy_mutations_maintain_bounds_and_do_not_modify_parents():
    rng = np.random.default_rng(55)
    base = founder_dna(rng, 70)
    original_dna, original_copies = base.dna.copy(), base.copies.copy()
    mutated = mutate(base.dna, base.copies, rng, point_rate=1., copy_rate=1., strength=.5)
    assert np.array_equal(base.dna, original_dna)
    assert np.array_equal(base.copies, original_copies)
    assert np.all((mutated.copies >= 0) & (mutated.copies <= 3))
    assert (mutated.point_changes == len(LOCI)).all()
    assert (mutated.copy_changes > 0).all()
    assert np.any(mutated.copies == 0) and np.any(mutated.copies == 2)
    assert np.all(np.abs(mutated.dna) <= 2.5)
    with pytest.raises(ValueError):
        mutate(base.dna, base.copies, rng, point_rate=1.1)


def test_recombination_inherits_parental_loci_without_overwriting_parents():
    rng = np.random.default_rng(77)
    a, b = np.ones((4, len(LOCI))), np.full((4, len(LOCI)), -1.)
    ac, bc = np.ones_like(a, dtype=np.int8), np.full_like(a, 3, dtype=np.int8)
    child, copies = recombine(a, ac, b, bc, rng)
    assert np.all((child == 1.) | (child == -1.))
    assert np.array_equal(copies == 1, child == 1)
    assert np.all(a == 1) and np.all(b == -1)


def test_biology_modulates_actual_metabolic_energy_and_body_size():
    w = World(
        Config(width=20, height=20, founders=2, max_population=5,
               genetics_enabled=True, allow_reproduction=False,
               fixed_speed=0., max_bite=0., metabolism=1.), seed=41)
    w.body_dna[:] = 0
    w.gene_copies[:] = 1
    w.body_dna[0, INDEX['metabolic_efficiency']] = 2
    w.body_dna[1, INDEX['metabolic_efficiency']] = -2
    w.body_dna[0, INDEX['body_size']] = 1
    w.body_dna[1, INDEX['body_size']] = -1
    old = w.energy.copy()
    w.step()
    assert w.energy[0] > w.energy[1]
    assert (old - w.energy)[0] < (old - w.energy)[1]
    assert w.biology()['size'][0] > w.biology()['size'][1]


def test_reproduction_is_local_two_parent_and_energy_conserving():
    cfg = Config(width=20, height=20, founders=2, max_population=3,
                 genetics_enabled=True, reproduction_mode='sexual',
                 allow_mutation=False, metabolism=0, food_gain=0, move_cost=0,
                 fixed_speed=0., reproduction_age=1)
    w = World(cfg, seed=7)
    w.x[:] = 9.0
    w.y[:] = 10.0
    w.age[:] = 2
    w.energy[:] = 100
    w.body_dna[0] = -1
    w.body_dna[1] = +1
    w.gene_copies[:] = 1
    before_total = float(np.sum(w.energy))
    w.step()
    assert w.population == 3
    assert w.sexual_births == 1
    assert w.second_parents[2] >= 0
    assert {int(w.parents[2]), int(w.second_parents[2])} == {0, 1}
    assert np.all((w.body_dna[2] == -1) | (w.body_dna[2] == 1))
    assert w.offspring_count[:2].tolist() == [1, 1]
    assert float(np.sum(w.energy)) <= before_total
    assert w.specimen(2)['parent2_id'] in (0, 1)
    assert w.relatives(0) == [2] == w.relatives(1)


def test_mates_must_be_local_and_asexual_fallback_works():
    base = dict(width=20, height=20, founders=2, max_population=3,
                genetics_enabled=True, allow_mutation=False, metabolism=0,
                food_gain=0, move_cost=0, fixed_speed=0, reproduction_age=1)
    for mode, expected in [('sexual', 2), ('mixed', 3), ('asexual', 3)]:
        w = World(Config(**base, reproduction_mode=mode), seed=77)
        w.x[:] = [2, 15]
        w.y[:] = [2, 15]
        w.age[:] = 3
        w.energy[:] = 90
        w.step()
        assert w.population == expected
        if expected == 3:
            assert w.second_parents[2] == -1


def test_checkpoint_continuation_preserves_dna_and_random_mutations(tmp_path):
    w = small()
    for _ in range(60):
        w.step()
    p = tmp_path / 'bio.npz'
    w.save(p)
    resumed = World.load(p)
    for _ in range(32):
        w.step()
        resumed.step()
    for field in ('ids','parents','second_parents','body_dna','gene_copies',
                  'genomes','energy','mutation_count','food'):
        assert np.array_equal(getattr(w, field), getattr(resumed, field))
    assert w.total_body_mutations == resumed.total_body_mutations
    assert w.sexual_births == resumed.sexual_births


def test_legacy_compatibility_and_new_world_genetic_opt_in(tmp_path):
    assert not Config().genetics_enabled
    old = World(Config(width=20, height=20, founders=8), seed=42)
    for _ in range(35):
        old.step()
    old.save(tmp_path / 'legacy.npz')
    read = World.load(tmp_path / 'legacy.npz')
    assert not read.config.genetics_enabled
    assert read.body_dna.shape == (read.population, len(LOCI))
    assert np.all(read.second_parents == -1)
    for _ in range(30):
        old.step();read.step()
    assert np.array_equal(old.genomes, read.genomes)


def test_sexual_mode_no_mutation_records_zero_mutation_events():
    w = small(mode='sexual', allow_mutation=False)
    for _ in range(110):
        w.step()
    assert w.total_body_mutations == w.total_copy_mutations == 0
    assert np.all(w.mutation_count == 0)
    assert w.sexual_births > 0


def test_gene_spark_cheat_mutates_selected_creature_and_is_logged():
    w = small()
    g = w.body_dna[0].copy()
    assert 'DNA Spark' in cheat(w, 'gene_spark', int(w.ids[0]))
    assert not np.array_equal(g, w.body_dna[0])
    assert w.manual_interventions[-1]['action'] == 'gene_spark'
    assert w.total_body_mutations >= 1
    assert creature_color(w.genomes[0], w.body_dna[0], w.gene_copies[0]) in (
        (255, 162, 202), (249, 188, 222), (195, 162, 241),
        (255, 198, 150), (165, 215, 205), (250, 222, 167))


def test_baby_cheat_copies_genetic_dna_without_randomization():
    w = small()
    before = w.population
    cheat(w, 'babies', int(w.ids[0]))
    assert w.population == before + 8
    assert np.array_equal(w.body_dna[before:], np.repeat(w.body_dna[:1], 8, axis=0))
    assert np.array_equal(w.gene_copies[before:], np.repeat(w.gene_copies[:1], 8, axis=0))
    for _ in range(2):
        w.step()


def test_replicated_cpu_study_sequential_matches_parallel(tmp_path):
    kw = dict(seeds=[8, 9], ticks=70, founders=18, capacity=54,
              sample_every=15, compare_mutations=True)
    one = run_study(**kw, output=tmp_path / 'a', workers=1)
    many = run_study(**kw, output=tmp_path / 'b', workers=2)
    assert one == many
    assert (tmp_path / 'a' / 'genomic_timelines.csv').read_bytes() == (
        tmp_path / 'b' / 'genomic_timelines.csv').read_bytes()
    with (tmp_path / 'a' / 'final_populations.csv').open() as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 4


def test_babies_grow_to_inherited_adult_size_without_rewriting_dna():
    w = small(mode='asexual', allow_reproduction=False)
    w.body_dna[:] = 0.
    w.gene_copies[:] = 1
    infant_size = float(w.biology()['size'][0])
    infant_bite = float(w.biology()['bite'][0])
    old_dna = w.body_dna.copy()
    w.age[:] = 400
    assert w.biology()['size'][0] > infant_size
    assert w.biology()['bite'][0] > infant_bite
    assert np.array_equal(w.body_dna, old_dna)


def test_genetic_lineage_csv_supports_two_parents(tmp_path):
    from argparse import Namespace
    from biosphere.cli import simulate
    args = Namespace(founders=16, max_population=60, sensor_mode='normal',
                     no_mutation=False, mutation_strength=.28, growth_rate=.03,
                     patchiness=1., resource_background=None, resource_layout='hills',
                     island_count=8, island_sigma=2.8, island_peak=10.,
                     boundary_mode='wrap', patch_shift_interval=0, move_cost=.065,
                     resume=None, seed=3, steps=70, sample_every=10,
                     events=True, output=str(tmp_path), genetics=True,
                     reproduction_mode='sexual', body_mutation_rate=.06,
                     copy_mutation_rate=.03)
    simulate(args)
    with (tmp_path / 'lineage.csv').open() as file:
        rows = list(csv.DictReader(file))
    assert rows and 'parent2_id' in rows[0]
    assert any(r['kind'] == 'birth' and r['parent2_id'] not in ('', '-1') for r in rows)


def test_pillow_dna_overlay_at_compact_size(tmp_path):
    import subprocess, sys, json
    pytest.importorskip('PIL')
    pic = tmp_path / 'dna.png'
    rep = tmp_path / 'qa.json'
    subprocess.run([sys.executable, 'tools/pygame_preview_stub.py',
                    '--size', '1020x685', '--qa-script', 'tools/qa_scripts/v10_dna.json',
                    '--out', str(pic), '--qa-report', str(rep)], cwd=Path(__file__).parents[1],
                   check=True, capture_output=True, text=True, timeout=30)
    assert pic.is_file() and pic.stat().st_size > 2000
    assert json.loads(rep.read_text())['ui']['active_overlay'] == 'dna'
