"""Gene regulation and out-of-core archive: controlled physics + compatibility tests."""
from __future__ import annotations

from dataclasses import replace
import io
from pathlib import Path
import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.archive_storage import DiskArchive
from biosphere.playful import cheat, MiniGames, PairedLab
from biosphere.regulatory import (MAX_GENES, OP, SOURCE, TARGET, WEIGHT, THRESHOLD,
                                  CHROM, INNOVATION, evaluate, expression_signals,
                                  empty_programs, founder_programs, inherit_programs,
                                  validate_programs, describe)
from biosphere.state_schema import validate_world_state


def small(seed=17, **kw):
    defaults = dict(width=20, height=20, founders=15, max_population=50,
                    genetics_enabled=True, regulation_enabled=True)
    defaults.update(kw)
    return World(Config(**defaults), seed=seed)


def test_conditional_regulation_is_not_merely_a_static_allele():
    p, lens = empty_programs(2)
    p[:, 0, OP] = 0
    p[:, 0, SOURCE] = 1  # local_food
    p[:, 0, TARGET] = 0  # maintenance
    p[:, 0, WEIGHT] = 3
    p[:, 0, INNOVATION] = [1, 2]
    lens[:] = 1
    low = expression_signals(food=np.array([0., 0.]), energy=np.ones(2),
                             crowd=np.zeros(2), maturity=np.zeros(2), asymmetry=np.zeros(2))
    rich = low.copy(); rich[:, 1] = 1
    a, b = evaluate(p, lens, low), evaluate(p, lens, rich)
    assert (b[:, 0] > a[:, 0]).all()
    assert np.array_equal(evaluate(p, lens, low), a)
    assert not np.any(np.isnan(b))


def test_multiple_genes_form_order_dependent_regulatory_circuit():
    p, lens = empty_programs(1)
    # gene 1 creates regulator A from the constant signal; gene 2 reads A
    p[0, 0] = [0, 0, 9, 2, 0, 0, 1]
    p[0, 1] = [0, 6, 1, 2, 0, 0, 2]
    lens[0] = 2
    signals = np.array([[1, 0, 1, 0, 0, 0]], dtype=float)
    first = evaluate(p, lens, signals)[0, 1]
    p[:, :2] = p[:, :2][:, ::-1]
    second = evaluate(p, lens, signals)[0, 1]
    assert first > second


def test_founder_innovations_and_structural_mutations_are_bounded_and_inherited():
    rng = np.random.default_rng(11)
    p, lens, next_id = founder_programs(rng, 40)
    validate_programs(p, lens)
    assert len(set(lens.tolist())) > 1
    original = p.copy()
    novel = 0
    for _ in range(180):
        i, j = map(int, rng.choice(len(p), size=2, replace=False))
        child, count, next_id, counters = inherit_programs(
            p[i], lens[i], p[j], lens[j], rng, next_id,
            mutate_enabled=True, point_rate=1, structural_rate=1)
        validate_programs(child[None], np.array([count]))
        assert count <= MAX_GENES
        novel += counters['insertions'] + counters['duplications']
    assert novel > 0 and next_id > 150
    assert np.array_equal(p, original)


def test_gene_program_changes_ecological_physiology_and_uses_actual_inputs():
    w = small(founders=2, max_population=4, allow_reproduction=False,
              max_bite=0, metabolism=1, fixed_speed=0, move_cost=0)
    w.body_dna[:] = 0
    w.gene_copies[:] = 1
    w.regulatory_lengths[:] = 1
    w.regulatory_programs[:] = 0
    w.regulatory_programs[:, 0, OP] = 0
    w.regulatory_programs[:, 0, SOURCE] = 0 # bias
    w.regulatory_programs[:, 0, TARGET] = 0 # maintenance
    w.regulatory_programs[:, 0, WEIGHT] = [3, -3]
    w.regulatory_programs[:, 0, INNOVATION] = [1, 2]
    old = w.energy.copy()
    w.step()
    assert (old - w.energy)[0] > (old - w.energy)[1]


def test_regulation_blindness_ablation_changes_expression():
    w = small(founders=1, max_population=4)
    w.regulatory_lengths[:] = 1
    w.regulatory_programs[:] = 0
    w.regulatory_programs[0, 0] = [0, 1, 2, 3, 0, 0, 1]
    w.x[:] = 9; w.y[:] = 9
    w.food[:] = w.capacity
    normal = w.regulation()[0, 2]
    blind = World.load(_snapshot_with_mode(w, 'food_blind'))
    assert normal > blind.regulation()[0, 2]


def _snapshot_with_mode(world, mode):
    world.config = replace(world.config, sensor_mode=mode)
    f = io.BytesIO(); world.save(f); f.seek(0); return f


def test_regulation_checkpoint_replay_and_inherited_growth(tmp_path):
    w = small(seed=99, founders=35, max_population=90,
              regulatory_structure_rate=.75, regulatory_point_rate=.7)
    for _ in range(115): w.step()
    assert w.total_births > 0
    assert w.regulatory_mutations > 0
    assert w.next_gene_innovation > 1
    validate_world_state(w)
    path = tmp_path / 'regulation_world.npz'; w.save(path)
    restored = World.load(path)
    assert np.array_equal(w.regulatory_programs, restored.regulatory_programs)
    assert np.array_equal(w.regulatory_lengths, restored.regulatory_lengths)
    assert w.next_gene_innovation == restored.next_gene_innovation
    for _ in range(65):
        w.step(); restored.step()
    for name in ('x','y','age','ids','energy','regulatory_lengths','regulatory_programs','food'):
        assert np.array_equal(getattr(w,name), getattr(restored,name)), name


def test_legacy_save_load_remains_regulation_off(tmp_path):
    w = small(regulation_enabled=False)
    assert not w.regulatory_lengths.any()
    w.save(tmp_path/'legacy.npz')
    loaded = World.load(tmp_path/'legacy.npz')
    assert loaded.config.regulation_enabled is False
    for _ in range(20):
        w.step(); loaded.step()
    assert np.array_equal(w.energy, loaded.energy)


def test_cheats_minigames_cloning_and_twin_lab_keep_new_dna_aligned():
    w = small()
    one = int(w.ids[0])
    original = w.regulatory_programs[0].copy()
    cheat(w, 'babies', one)
    assert np.array_equal(w.regulatory_programs[-1], original)
    assert w.regulatory_lengths[-1] == w.regulatory_lengths[0]
    mini = MiniGames(); ch = mini.create(w, 'genes')
    assert len(ch.labels) == 3
    mini.answer(0)
    assert mini.attempts == 1
    lab = PairedLab(w, 'half_growth')
    lab.advance(2)
    assert np.array_equal(lab.control.regulatory_lengths, lab.changed.regulatory_lengths)
    assert len(w.manual_interventions) == 1
    validate_world_state(w)


def test_disk_archive_is_out_of_core_queryable_and_portable(tmp_path):
    w = small(seed=31, founders=25, max_population=45, lifespan=38,
              initial_energy=9, reproduction_threshold=47)
    for _ in range(43): w.step()
    assert len(w.life_archive) > 0
    expected = {k: w.life_archive[k] for k in list(w.life_archive)[:3]}
    w.enable_disk_archive(tmp_path/'history.sqlite')
    assert isinstance(w.life_archive, DiskArchive)
    assert len(w.life_archive) > 0
    for id_, record in expected.items(): assert w.specimen(id_)['id'] == record['id']
    assert len(w.life_archive.recent(2)) == 2
    checkpoint = tmp_path / 'portable.npz'
    w.save(checkpoint)
    # Verify that the in-memory v1.1 checkpoint *contains* the SQLite data.
    with np.load(checkpoint, allow_pickle=False) as z:
        assert 'archive_database' in z.files
    restored = World.load(checkpoint)
    assert isinstance(restored.life_archive, DiskArchive)
    assert len(restored.life_archive) == len(w.life_archive)
    for id_, record in expected.items(): assert restored.specimen(id_)['id'] == record['id']
    for _ in range(12):
        w.step(); restored.step()
    assert np.array_equal(w.energy, restored.energy)
    assert len(w.life_archive) == len(restored.life_archive)


def test_disk_archive_refuses_mixed_histories(tmp_path):
    a = small(seed=2, lifespan=15)
    for _ in range(18): a.step()
    path = tmp_path / 'occupied.sqlite'
    a.enable_disk_archive(path)
    a.life_archive.flush()
    b = small(seed=3)
    with pytest.raises(ValueError, match='already contains'):
        b.enable_disk_archive(path)


def test_falsified_checkpoint_program_rejected(tmp_path):
    w = small();p = tmp_path / 'okay.npz'; w.save(p)
    with np.load(p, allow_pickle=False) as z:
        arrays = {k: z[k].copy() for k in z.files}
    arrays['regulatory_programs'][0, 0, OP] = 999
    bad=tmp_path/'bad.npz'; np.savez_compressed(bad, **arrays)
    with pytest.raises(ValueError, match='Regulatory checkpoint'):
        World.load(bad)


def test_noncoding_instructions_are_neutral_until_modified():
    p, lengths = empty_programs(1)
    p[0, 0] = [4, 0, 0, 3, 0, 0, 1]  # noncoding
    lengths[:] = 1
    inputs = np.array([[1., .9, .2, .4, .5, -.1]])
    assert not evaluate(p, lengths, inputs).any()
    p[0, 0, OP] = 0
    assert evaluate(p, lengths, inputs)[0, 0] > 0


def test_new_chromosomes_can_be_created_and_inherited():
    rng = np.random.default_rng(845)
    p, lengths, next_id = founder_programs(rng, 10)
    found = 0
    for _ in range(350):
        child, count, next_id, changes = inherit_programs(
            p[0], lengths[0], None, None, rng, next_id,
            mutate_enabled=True, point_rate=0., structural_rate=1.)
        found += changes['chromosome_births']
        if changes['chromosome_births']:
            assert len(set(int(x) for x in child[:count, CHROM])) > 2
            break
    assert found > 0
