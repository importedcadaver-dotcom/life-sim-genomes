"""Maintenance gate: checkpoint integrity and old/new feature interoperability.

These tests intentionally span the existing engine, v0.9 sandbox and v1.0
biology; they do not add new evolutionary functions or optimize for outcomes.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
from io import BytesIO
import json
from pathlib import Path

import numpy as np
import pytest

from biosphere.playful import Chronicle, MiniGames, PairedLab, cheat
from biosphere.simulation import Config, World
from biosphere.state_schema import LIVE_ARRAY_FIELDS, SCHEMA_VERSION, validate_world_state
from biosphere.viewer import layout_for, SimulationClock


def world(*, genetics: bool = True) -> World:
    return World(Config(width=20, height=20, founders=20, max_population=75,
                        genetics_enabled=genetics, reproduction_mode="mixed"), seed=42)


def _tampered_checkpoint(source: Path, dest: Path, name: str, replacement) -> None:
    with np.load(source, allow_pickle=False) as data:
        arrays = {key: data[key].copy() for key in data.files}
    arrays[name] = replacement
    np.savez_compressed(dest, **arrays)


def test_atomic_world_save_does_not_overwrite_on_failure(tmp_path, monkeypatch):
    w = world()
    path = tmp_path / 'world.npz'
    w.save(path)
    original = path.read_bytes()
    def broken_writer(*args, **kwargs):
        raise OSError('simulated out-of-space failure')
    monkeypatch.setattr('biosphere.simulation.np.savez_compressed', broken_writer)
    with pytest.raises(OSError, match='out-of-space'):
        w.save(path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_v101_versioned_checkpoint_and_legacy_schema_fallback(tmp_path):
    w = world()
    for _ in range(30): w.step()
    path = tmp_path / 'world.npz'
    w.save(path)
    with np.load(path, allow_pickle=False) as data:
        assert json.loads(str(data['state']))['schema_version'] == SCHEMA_VERSION
        entries = {key: data[key].copy() for key in data.files}
    state = json.loads(str(entries['state']))
    del state['schema_version']
    entries['state'] = np.array(json.dumps(state))
    old = tmp_path / 'legacy.npz'
    np.savez_compressed(old, **entries)
    restored = World.load(old)
    for _ in range(20):
        w.step(); restored.step()
    assert np.array_equal(w.body_dna, restored.body_dna)
    assert np.array_equal(w.gene_copies, restored.gene_copies)
    assert np.array_equal(w.energy, restored.energy)


@pytest.mark.parametrize('array,replacement_kind', [
    ('body_dna', 'short'), ('gene_copies', 'invalid_copies'),
    ('ids', 'duplicate'), ('food', 'wrong_shape'), ('genomes', 'wrong_shape'),
])
def test_malformed_checkpoints_are_rejected(tmp_path, array, replacement_kind):
    w = world()
    source, output = tmp_path / 'ok.npz', tmp_path / 'broken.npz'
    w.save(source)
    value = getattr(w, array).copy()
    if replacement_kind == 'short': value = value[:-1]
    if replacement_kind == 'invalid_copies': value[0, 0] = 99
    if replacement_kind == 'duplicate': value[0] = value[1]
    if replacement_kind == 'wrong_shape': value = value[..., :-1]
    _tampered_checkpoint(source, output, array, value)
    with pytest.raises(ValueError, match='Checkpoint'):
        World.load(output)


def test_future_unknown_checkpoint_version_fails_closed(tmp_path):
    w = world()
    source, output = tmp_path / 'ok.npz', tmp_path / 'future.npz'
    w.save(source)
    with np.load(source, allow_pickle=False) as data:
        entries = {key: data[key].copy() for key in data.files}
    state = json.loads(str(entries['state']))
    state['schema_version'] = 999
    entries['state'] = np.array(json.dumps(state))
    np.savez_compressed(output, **entries)
    with pytest.raises(ValueError, match='schema version'):
        World.load(output)


def test_world_alignment_after_cheats_births_deaths_and_resumption(tmp_path):
    w = world()
    organism = int(w.ids[0])
    observe = Chronicle()
    assert observe.toggle(w, organism)
    original_genome = w.body_dna[0].copy()
    cheat(w, 'gene_spark', organism)
    assert not np.array_equal(w.body_dna[0], original_genome)
    cheat(w, 'babies', organism)
    assert w.population == 28
    validate_world_state(w)
    games = MiniGames()
    rng_snapshot = json.dumps(w.rng.bit_generator.state, sort_keys=True)
    games.create(w, 'berries'); games.answer(0)
    assert json.dumps(w.rng.bit_generator.state, sort_keys=True) == rng_snapshot
    for _ in range(42):
        w.step(); observe.observe(w)
    validate_world_state(w)
    path = tmp_path / 'genetics_and_cheats.npz'
    w.save(path)
    notebook = tmp_path / 'book.json'
    observe.save(notebook, games)
    w2 = World.load(path)
    observe2, games2 = Chronicle.load(notebook)
    assert observe2.bookmarks == observe.bookmarks
    assert games2.attempts == games.attempts
    assert w2.manual_interventions == w.manual_interventions
    # An A/B test operates on cloned worlds, never on the actively observed one.
    before = np.copy(w2.food)
    lab = PairedLab(w2, 'food_blind')
    lab.advance(5)
    assert np.array_equal(w2.food, before)
    assert lab.control.config.sensor_mode == 'normal'
    assert lab.changed.config.sensor_mode == 'food_blind'
    for _ in range(80):
        w.step(); w2.step()
    validate_world_state(w)
    validate_world_state(w2)
    for field in LIVE_ARRAY_FIELDS:
        assert np.array_equal(getattr(w, field), getattr(w2, field)), field


@pytest.mark.parametrize('field,value', [
    ('max_bite', -1.0), ('max_bite', float('nan')),
    ('initial_energy', float('inf')), ('sensor_distance', -5.),
    ('lifespan', 0), ('reproduction_age', -1),
])
def test_nonsensical_configurations_are_rejected(field, value):
    with pytest.raises(ValueError):
        Config(**{field: value})


@pytest.mark.parametrize('mode,expected', [
    ('legacy', '609b1d16d6346bd34fea464616a30b3c1b333339c373c1b42a1de45b22ccea3d'),
    ('genetic', '91b8ebbfcfccc18dbc04141227bd3dac95be5710e0ee4e63048532ff72f7d7c2'),
    ('paired', 'd6bb1daca7ba275417437178dd72ddd9637bd0e4ff30804d0adc0272174bf233'),
])
def test_v10_behavior_fingerprint_is_unchanged(mode, expected):
    w = World(Config(width=20, height=20, founders=26, max_population=65,
                     genetics_enabled=mode != 'legacy',
                     reproduction_mode='sexual' if mode == 'paired' else 'mixed'), seed=90)
    for _ in range(140): w.step()
    digest = hashlib.sha256()
    for name in ('x','y','angle','energy','age','ids','parents','second_parents',
                 'generation','genomes','body_dna','gene_copies','mutation_count',
                 'food','capacity'):
        digest.update(np.ascontiguousarray(getattr(w, name)).tobytes())
    digest.update(json.dumps(w.rng.bit_generator.state, sort_keys=True).encode())
    assert digest.hexdigest() == expected


def test_viewer_layout_pacing_remain_headless_and_compatible():
    assert layout_for(1020, 685).map_rect[2] > 100
    c = SimulationClock()
    assert c.steps(.05) >= 0
    c.change(2)
    assert c.steps(.2) >= 0


def test_observer_sidecar_belongs_to_checkpoint_and_preserves_old_books(tmp_path):
    w = world()
    w.save(tmp_path / 'one.npz')
    other = world()
    other.step()
    other.save(tmp_path / 'two.npz')
    book = Chronicle()
    games = MiniGames()
    book.toggle(w, 0)
    sidecar = tmp_path / 'one.observer.json'
    book.save(sidecar, games, checkpoint=tmp_path / 'one.npz')
    check, _ = Chronicle.load(sidecar, checkpoint=tmp_path / 'one.npz')
    assert check.bookmarks == [0]
    with pytest.raises(ValueError, match='different world checkpoint'):
        Chronicle.load(sidecar, checkpoint=tmp_path / 'two.npz')
    old_sidecar = tmp_path / 'old.observer.json'
    book.save(old_sidecar, games)
    old_book, _ = Chronicle.load(old_sidecar, checkpoint=tmp_path / 'two.npz')
    assert old_book.bookmarks == [0]


def test_paired_lab_labels_a_cheated_start_as_illustrative():
    w = world()
    assert PairedLab(w, 'half_growth').report()['scientific_status'] == 'single_pair_not_replicated'
    cheat(w, 'feast')
    report = PairedLab(w, 'half_growth').report()
    assert report['source_interventions'] == 1
    assert report['scientific_status'] == 'illustrative_only'
