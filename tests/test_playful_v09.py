"""Pink living observatory: cheats, games, record-keeping and cloned A/B runs."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.playful import Chronicle, MiniGames, PairedLab, cheat, creature_color

ROOT = Path(__file__).resolve().parents[1]


def small(seed=42, **updates):
    return World(Config(founders=14, max_population=70, width=24, height=20, **updates), seed=seed)


def test_cute_pigment_is_stable_from_genes_and_does_not_change_state():
    w = small()
    g = w.genomes.copy()
    c = creature_color(g[0])
    assert len(c) == 3 and c == creature_color(g[0])
    assert np.array_equal(w.genomes, g)


def test_cheats_tagged_and_saves_replay(tmp_path):
    w = small()
    initial = w.population
    old_gene = w.genomes[0].copy()
    assert 'cupcake' in cheat(w, 'energy', int(w.ids[0]))
    assert w.energy[0] == pytest.approx(72)
    assert 'baby clones' in cheat(w, 'babies', int(w.ids[0]))
    assert w.population == initial + 8
    assert np.array_equal(w.genomes[initial], old_gene)
    assert w.next_id == initial + 8
    assert w.total_births == 8
    assert w.offspring_count[0] == 8
    assert len(w.manual_interventions) == 2
    assert all(v['kind'] == 'cheat' for v in w.manual_interventions)
    p = tmp_path / 'cheated.npz'
    w.save(p)
    read = World.load(p)
    assert read.population == w.population
    assert read.manual_interventions == w.manual_interventions
    assert read.relatives(0, limit=1, offset=-1) == [initial + 7]
    for _ in range(8):
        w.step()
        read.step()
    assert np.array_equal(w.ids, read.ids)
    assert np.array_equal(w.genomes, read.genomes)


def test_full_food_and_cozy_mode_are_explicitly_interventions():
    w = small()
    w.food[:] = 0
    assert 'Candy rain' in cheat(w, 'feast')
    assert np.array_equal(w.food, w.capacity)
    cheat(w, 'immortal')
    assert w.config.metabolism == 0 and w.config.move_cost == 0
    assert w.config.lifespan == 1_000_000
    assert len(w.manual_interventions) == 2
    with pytest.raises(ValueError):
        cheat(w, '__magic__')


def test_invalid_cheat_does_not_tag_world():
    w = small()
    assert 'Select a living creature' in cheat(w, 'energy', 999999)
    assert w.manual_interventions == []


def test_minigames_use_real_data_and_never_consume_world_rng():
    w = small()
    checkpoint = w.rng.bit_generator.state
    g = MiniGames()
    c = g.create(w, 'berries')
    assert c.kind == 'berries' and len(c.values) == 3
    for label, val in zip(c.labels, c.values):
        x, y = map(int, label.split('(')[-1].strip(')').split(','))
        assert val == pytest.approx(w.food[y, x])
    assert w.rng.bit_generator.state == checkpoint
    first = g.answer(c.winner)
    assert first and g.correct == 1 and g.attempts == 1
    g.answer(c.winner)
    assert g.correct == 1 and g.attempts == 1  # no score farming
    c2 = g.create(w, 'speed')
    speeds = w.controls()[1]
    for label, value in zip(c2.labels, c2.values):
        creature_id = int(label.split('#')[1].split(' ')[0])
        idx = int(np.flatnonzero(w.ids == creature_id)[0])
        assert value == pytest.approx(speeds[idx])
    assert w.rng.bit_generator.state == checkpoint
    with pytest.raises(ValueError):
        g.create(w, 'unknown')


def test_saved_observational_bookmarks_survive_death_and_reload(tmp_path):
    w = small()
    journal = Chronicle()
    assert journal.toggle(w, 0)
    for _ in range(30):
        w.step()
        journal.observe(w)
    assert journal.traces['0']
    g = MiniGames()
    g.create(w, 'berries')
    g.answer(g.challenge.winner)
    p = tmp_path / 'world.npz.observer.json'
    journal.save(p, g)
    loaded, loaded_games = Chronicle.load(p)
    assert loaded.bookmarks == [0]
    assert loaded.traces['0'] == journal.traces['0']
    assert (loaded_games.attempts, loaded_games.correct) == (1, 1)


@pytest.mark.parametrize('mode', ['half_growth','double_cost','food_blind'])
def test_paired_lab_clones_without_touching_source(mode):
    w = small(71)
    for _ in range(20):
        w.step()
    initial_file_state = (w.tick, w.population, w.energy.copy(), w.genomes.copy(),
                          w.rng.bit_generator.state.copy())
    lab = PairedLab(w, mode)
    assert lab.control.tick == w.tick == lab.changed.tick
    assert np.array_equal(lab.control.genomes, lab.changed.genomes)
    for _ in range(10):
        lab.advance(12)
    assert lab.done and lab.steps == 100
    assert lab.report()['mode'] == mode
    assert w.tick == initial_file_state[0] and w.population == initial_file_state[1]
    assert np.array_equal(w.energy, initial_file_state[2])
    assert np.array_equal(w.genomes, initial_file_state[3])
    assert w.rng.bit_generator.state == initial_file_state[4]
    assert w.manual_interventions == []


def test_family_child_pagination_more_than_32():
    w = small()
    # Deterministically generate enough cheat children in multiple batches.
    w.config = __import__('dataclasses').replace(w.config, max_population=80)
    for _ in range(6):
        cheat(w, 'babies', 0)
    assert len(w.relatives(0)) == 32
    assert len(w.relatives(0, limit=9, offset=36)) == 9
    assert w.relatives(0, limit=1, offset=-1)[0] == int(w.ids[-1])


def test_diagnostic_real_viewer_draws_new_overlays(tmp_path):
    pytest.importorskip('PIL')
    for panel in ('cheats','games','chronicle','lab','cheat_refill','game_answer','chronicle_bookmark'):
        pic = tmp_path / (panel + '.png')
        report = tmp_path / (panel + '.json')
        cmd = [sys.executable, 'tools/pygame_preview_stub.py', '--size', '1020x685',
               '--qa-script', f'tools/qa_scripts/v09_{panel}.json', '--out', str(pic),
               '--qa-report', str(report)]
        subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        assert pic.stat().st_size > 15000
        data = json.loads(report.read_text())
        expected = panel if panel in ('cheats','games','chronicle','lab') else (
            'cheats' if panel == 'cheat_refill' else 'games' if panel == 'game_answer' else 'chronicle')
        assert data['ui']['active_overlay'] == expected
        if panel == 'cheat_refill':
            assert data['ui']['interventions'] == 1
        if panel == 'game_answer':
            assert data['ui']['mini_attempts'] == 1
        if panel == 'chronicle_bookmark':
            assert data['ui']['bookmarks'] == 1


def test_experiment_008_reproducible_small_paired_training(tmp_path):
    from biosphere.selection_008 import run
    a = run(seeds=range(1101,1103), train_ticks=36, eval_ticks=28, output=tmp_path / 'a')
    b = run(seeds=range(1101,1103), train_ticks=36, eval_ticks=28, output=tmp_path / 'b')
    assert a == b
    assert a['trials'] == 8
    assert (tmp_path / 'a' / 'trials.csv').read_bytes() == (tmp_path / 'b' / 'trials.csv').read_bytes()
