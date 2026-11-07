from dataclasses import replace
import numpy as np
import pytest
from biosphere.simulation import Config, World
from biosphere.environment import evaluate, run_environment_experiment


def small(**kwargs):
    return Config(width=24, height=20, founders=14, max_population=60, **kwargs)


def test_reflective_wall_flips_angle_but_does_not_wrap():
    world = World(small(boundary_mode="reflect", fixed_speed=0.5, fixed_turn=0,
                        allow_reproduction=False), seed=9)
    world.x[:] = 23.8
    world.y[:] = 10
    world.angle[:] = 0
    world.step()
    assert np.all(world.x < 24)
    assert np.allclose(world.x, 23.7)
    assert np.all(np.isclose(np.abs(world.angle), np.pi))
    assert world.last_wall_hits == 14


def test_wrap_remains_backward_compatible():
    w = World(small(fixed_speed=0.5, fixed_turn=0, allow_reproduction=False), seed=9)
    w.x[:] = 23.8; w.y[:] = 10; w.angle[:] = 0
    w.step()
    assert np.allclose(w.x, .3)
    assert w.last_wall_hits == 0


def test_reflective_food_sensing_stays_within_world():
    w = World(small(boundary_mode="reflect"), seed=19)
    w.x[:] = .02; w.y[:] = .05; w.angle[:] = -np.pi
    s = w.perceive()
    assert s.shape == (w.population, 8)
    assert np.all(np.isfinite(s))
    assert np.all((s[:,1:4] >= 0) & (s[:,1:4] <= 1))


def test_patch_shifts_conserve_current_stock_when_growth_and_biting_disabled():
    w = World(small(patch_shift_interval=1, growth_rate=0, max_bite=0,
                    allow_reproduction=False), seed=31)
    food = np.sum(w.food)
    capacity = np.sum(w.capacity)
    for _ in range(15):
        w.step()
    assert np.isclose(np.sum(w.food), food, rtol=1e-12)
    assert np.isclose(np.sum(w.capacity), capacity, rtol=1e-12)
    assert w.patch_moves == 15


def test_reflect_and_shifting_deterministic_checkpoint(tmp_path):
    a = World(small(boundary_mode="reflect", patch_shift_interval=7), seed=4)
    for _ in range(22):
        a.step()
    filename = tmp_path / "state.npz"
    a.save(filename)
    b = World.load(filename)
    for _ in range(30):
        assert a.step() == b.step()
    for name in ("capacity", "food", "x", "y", "angle", "genomes", "ids"):
        assert np.array_equal(getattr(a, name), getattr(b, name))
    assert a.patch_moves == b.patch_moves
    assert a.cumulative_wall_hits == b.cumulative_wall_hits


def test_old_checkpoint_defaults_for_new_environment_state(tmp_path):
    import json
    file = tmp_path / "legacy.npz"
    w = World(small(), seed=9)
    w.save(file)
    with np.load(file, allow_pickle=False) as data:
        arr = {k: data[k] for k in data.files if k != "state"}
        state = json.loads(str(data["state"]))
    for key in ("patch_moves", "cumulative_wall_hits", "last_wall_hits"):
        state.pop(key)
    state["config"].pop("boundary_mode"); state["config"].pop("patch_shift_interval")
    np.savez_compressed(file, **arr, state=json.dumps(state))
    loaded = World.load(file)
    assert loaded.config.boundary_mode == "wrap"
    assert loaded.patch_moves == 0
    assert loaded.cumulative_wall_hits == 0


def test_config_rejects_invalid_values():
    with pytest.raises(ValueError):
        Config(boundary_mode="teleport")
    with pytest.raises(ValueError):
        Config(patch_shift_interval=-1)
    with pytest.raises(ValueError):
        Config(move_cost=-1)


def test_holdout_and_intervention_reproducible():
    genomes = World(small(), seed=5).genomes
    a = evaluate(genomes, seed=1201, ticks=17, environment="reflect", intervention="zero_turn")
    b = evaluate(genomes, seed=1201, ticks=17, environment="reflect", intervention="zero_turn")
    assert a == b
    assert 0 <= a["harvest"]
    assert a["mean_wall_hits"] >= 0
    with pytest.raises(ValueError):
        evaluate(genomes, seed=1201, ticks=17, environment="unknown")


def test_mini_experiment_outputs_replicates_and_contrasts(tmp_path):
    result = run_environment_experiment(seeds=[81, 82], steps=14, probe_ticks=9,
                                        count=10, output=tmp_path,
                                        save_checkpoints=False, progress=False)
    assert result["training"]["wrap"]["replicates"] == 2
    assert result["contrasts"]["zero_turn_wrap"]["paired_seeds"] == 2
    assert len(list(tmp_path.glob("*.csv"))) == 3
    assert (tmp_path / "summary.json").exists()
