from dataclasses import replace
import numpy as np
import pytest

from biosphere.simulation import Config, World
from biosphere.navigation import (ECOLOGIES, common_garden, intervention_config,
                                   paired_contrast, run_navigation_experiment, target_assay)


def test_island_layout_is_distinct_scarce_and_reproducible():
    cfg = Config(resource_layout="islands", resource_background=0.01, island_count=5)
    a, b = World(cfg, 122), World(cfg, 122)
    dense = World(replace(cfg, resource_layout="hills"), 122)
    assert np.array_equal(a.capacity, b.capacity)
    assert not np.array_equal(a.capacity, dense.capacity)
    assert np.mean(a.capacity < 0.25) > 0.40
    assert np.sum(a.capacity) < np.sum(dense.capacity)
    assert np.all(a.capacity >= 0)
    assert np.max(a.capacity) <= 12


def test_island_terrain_respects_reflecting_boundaries():
    cfg = Config(width=30, height=22, founders=12, resource_layout="islands",
                 boundary_mode="reflect", island_count=4)
    w = World(cfg, 15)
    for _ in range(40):
        w.step()
    assert np.all(w.x >= 0) and np.all(w.x < cfg.width)
    assert np.all(w.y >= 0) and np.all(w.y < cfg.height)


def test_invalid_island_settings():
    for override in (dict(resource_layout="other"), dict(island_count=0),
                     dict(island_sigma=0), dict(island_peak=-1)):
        with pytest.raises(ValueError):
            Config(**override)


def test_sparse_world_checkpoint_determinism(tmp_path):
    a = World(Config(resource_layout="islands", move_cost=0.5), 67)
    for _ in range(30):
        a.step()
    path = tmp_path / "islands.npz"
    a.save(path)
    b = World.load(path)
    for _ in range(40):
        assert a.step() == b.step()
    assert np.array_equal(a.capacity, b.capacity)
    assert np.array_equal(a.genomes, b.genomes)
    assert b.config.resource_layout == "islands"


def test_garden_uses_identical_conditions_under_ablations():
    genomes = World(Config(founders=15), 7).genomes
    a = common_garden(genomes, seed=20_000, ticks=18, ecology="islands")
    b = common_garden(genomes, seed=20_000, ticks=18, ecology="islands")
    c = common_garden(genomes, seed=20_000, ticks=18, ecology="islands",
                      intervention="zero_turn")
    assert a == b
    assert 0 <= a["harvest"]
    assert 0 <= c["survival"] <= 1
    with pytest.raises(ValueError):
        common_garden(genomes, seed=1, ticks=5, ecology="bog")
    with pytest.raises(ValueError):
        intervention_config(Config(), "special_navigation")


def test_target_assay_is_deterministic_and_ablations_are_valid():
    genomes = World(Config(founders=52), 17).genomes
    a = target_assay(genomes, seed=1210, ticks=15)
    b = target_assay(genomes, seed=1210, ticks=15)
    no_turn = target_assay(genomes, seed=1210, ticks=15, intervention="zero_turn")
    assert a == b
    for response in (a, no_turn):
        assert 0 <= response["hit_fraction"] <= 1
        assert 0 <= response["occupancy_fraction"] <= 1
        assert response["harvest"] >= 0
    assert a != no_turn


def test_contrast_counts_seeds_not_organisms():
    rows = [{"seed": 1, "group": "a", "intervention": "normal", "x": 2},
            {"seed": 1, "group": "b", "intervention": "normal", "x": 1},
            {"seed": 2, "group": "a", "intervention": "normal", "x": 3},
            {"seed": 2, "group": "b", "intervention": "normal", "x": 2}]
    diff = paired_contrast(rows, measure="x", ecology=None, left="a", right="b")
    assert diff["paired_seeds"] == 2
    assert diff["positive_seeds"] == 2
    assert diff["mean_difference"] == 1.0


def test_mini_navigation_experiment_produces_replayable_evidence(tmp_path):
    summary = run_navigation_experiment(seeds=[19, 21], steps=14, probe_ticks=9,
                                        count=12, output=tmp_path,
                                        save_checkpoints=True, progress=False)
    assert set(summary["training"]) == set(ECOLOGIES)
    assert summary["contrasts"]["target_normal_minus_zero_turn"]["paired_seeds"] == 2
    assert len(list((tmp_path / "checkpoints").glob("*.npz"))) == 6
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "target_assay.csv").exists()
    from biosphere.simulation import World
    check = World.load(tmp_path / "checkpoints" / "seed_19_islands.npz")
    assert check.config.resource_layout == "islands"


def test_fixed_speed_ablations_isolate_heading_control():
    w = World(Config(founders=12), 43)
    cfg = Config(founders=12)
    choices = {mode: intervention_config(cfg, mode) for mode in
               ("speed_fixed", "fixed_zero_turn", "fixed_food_blind", "fixed_mirror_food")}
    for config in choices.values():
        assert config.fixed_speed == 0.60
    assert choices["fixed_zero_turn"].fixed_turn == 0
    assert choices["fixed_food_blind"].sensor_mode == "food_blind"
    assert choices["fixed_mirror_food"].sensor_mode == "mirror_food"
    for mode, config in choices.items():
        p = World(config, 19, founder_genomes=w.genomes)
        turning, speed, _ = p.controls()
        assert np.allclose(speed, 0.6)
        if mode == "fixed_zero_turn":
            assert np.allclose(turning, 0)


def test_completed_seed_cache_rejects_changed_protocol(tmp_path):
    from biosphere.navigation import run_navigation_experiment
    args = dict(seeds=[22], steps=5, probe_ticks=5, count=8, output=tmp_path,
                save_checkpoints=False, progress=False)
    first = run_navigation_experiment(**args)
    second = run_navigation_experiment(**args)
    assert first == second
    with pytest.raises(ValueError, match="Incompatible cached"):
        run_navigation_experiment(**{**args, "count": 9})


def test_viewer_ecology_preset_restarts_with_rare_background():
    from biosphere.viewer import toggle_resource_layout
    config = Config()
    sparse = toggle_resource_layout(config)
    assert sparse.resource_layout == "islands"
    assert sparse.resource_background == 0.01
    restored = toggle_resource_layout(sparse)
    assert restored.resource_layout == "hills"
    assert restored.resource_background == 0.25
