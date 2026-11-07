from dataclasses import replace
import numpy as np
import pytest
from biosphere import Config, World


def small(**kw):
    return Config(width=22, height=18, founders=25, max_population=80, **kw)


def test_determinism_and_seed_difference():
    a, b, c = World(small(), 99), World(small(), 99), World(small(), 100)
    for _ in range(100):
        a.step(); b.step(); c.step()
    for key in ("food", "x", "y", "ids", "genomes", "generation"):
        assert np.array_equal(getattr(a, key), getattr(b, key))
    assert not np.array_equal(a.capacity, c.capacity)


def test_food_nonnegative_even_when_crowded():
    w = World(small(), 1)
    w.x[:] = 4.2; w.y[:] = 5.2
    w.config = replace(w.config, max_speed=0.0)
    for _ in range(20):
        w.step()
        assert np.all(w.food >= -1e-10)
        assert np.all(w.food <= w.capacity + 1e-10)


def test_energy_transfer_and_lineage():
    w = World(small(), 12)
    w.age[:] = 99
    w.energy[:] = 80
    w.step()
    assert w.total_births > 0
    assert len(w.ids) == len(np.unique(w.ids))
    assert np.all(w.generation[-w.total_births:] == 1)
    assert all(e["parent_id"] >= 0 for e in w.last_events if e["kind"] == "birth")
    assert w.population <= w.config.max_population


def test_restart_bitwise_identical(tmp_path):
    a = World(small(), 5)
    for _ in range(15):
        a.step()
    dest = tmp_path / "state.npz"
    a.save(dest)
    b = World.load(dest)
    for _ in range(45):
        assert a.step() == b.step()
    for name in ("x", "y", "angle", "genomes", "food", "ids"):
        assert np.array_equal(getattr(a, name), getattr(b, name))


def test_sensor_ablation_and_brain_outputs():
    a = World(small(sensor_mode="normal"), 6)
    b = World(small(sensor_mode="blind"), 6)
    assert np.any(a.perceive()[:, 1:6] != 0)
    assert np.all(b.perceive()[:, 1:6] == 0)
    assert np.all(a.controls()[1] > 0)
    assert np.all(a.controls()[1] <= a.config.max_speed)


def test_extinction_stays_extinct():
    w = World(small(allow_reproduction=False, metabolism=1000), 7)
    w.step()
    assert w.population == 0
    for _ in range(5):
        assert w.step()["population"] == 0


def test_mutation_disabled_clones_parent():
    w = World(small(allow_mutation=False), 3)
    w.age[:] = 99; w.energy[:] = 75
    original = {int(i): g.copy() for i, g in zip(w.ids, w.genomes)}
    w.step()
    for p, g in zip(w.parents, w.genomes):
        if p >= 0:
            assert np.array_equal(g, original[int(p)])


def test_invalid_configuration():
    with pytest.raises(ValueError):
        Config(newborn_energy=100)
    with pytest.raises(ValueError):
        Config(mutation_probability=-0.1)


def test_zero_food_has_no_free_energy():
    w = World(small(allow_reproduction=False, growth_rate=0), 9)
    w.food[:] = 0
    before = w.energy.copy()
    w.step()
    assert w.total_harvest == 0
    assert np.all(w.energy < before)


def test_bounded_population_after_many_births():
    w = World(small(), 13)
    w.energy[:] = 100
    w.age[:] = 99
    for _ in range(50):
        w.step()
        assert w.population <= w.config.max_population
        assert len(np.unique(w.ids)) == w.population


def test_common_garden_is_deterministic():
    from biosphere.experiment import probe
    w = World(small(), 38)
    a = probe(w.genomes, seed=3000, ticks=15)
    b = probe(w.genomes, seed=3000, ticks=15)
    assert a == b
    assert a['harvest'] >= 0


def test_save_load_restores_rich_observables(tmp_path):
    w = World(small(), 91)
    for _ in range(15):
        w.step()
    path = tmp_path / 'checkpoint.npz'
    w.save(path)
    r = World.load(path)
    assert r.total_harvest == w.total_harvest
    assert r.last_total_intake == w.last_total_intake
    assert r.death_causes == w.death_causes
