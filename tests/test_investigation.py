from dataclasses import replace
import numpy as np
import pytest
from biosphere.simulation import Config, World
from biosphere.investigation import (cue_sensors, motor_outputs, stimulus_response,
                                    effective_gene_weights, run_probe, run_investigation)


def test_mirror_reverses_lateral_food_without_touching_nonfood_inputs():
    w = World(Config(founders=20), seed=9)
    before = w.perceive()
    w.config = replace(w.config, sensor_mode="mirror_food")
    after = w.perceive()
    assert np.array_equal(after[:,2], before[:,3])
    assert np.array_equal(after[:,3], before[:,2])
    assert np.array_equal(after[:,5], -before[:,5])
    assert np.array_equal(after[:,[0,1,4,6,7]],before[:,[0,1,4,6,7]])


def test_ablation_keeps_crowd_separate_from_food():
    w = World(Config(founders=20, sensor_mode="food_blind"), 9)
    assert np.all(w.perceive()[:,1:6] == 0)
    w.config = replace(w.config, sensor_mode="crowd_blind")
    assert np.all(w.perceive()[:,7] == 0)
    assert np.any(w.perceive()[:,1:6] != 0)


def test_fixed_speed_and_turn_do_not_change_inherited_genome():
    w = World(Config(founders=5, fixed_speed=.42, fixed_turn=0.), 19)
    original = w.genomes.copy()
    t, v, _ = w.controls()
    assert np.all(t == 0)
    assert np.all(v == .42)
    w.step()
    assert np.array_equal(w.genomes[:5], original)
    with pytest.raises(ValueError): Config(fixed_speed=2)
    with pytest.raises(ValueError): Config(fixed_turn=1)


def test_synthetic_cue_steering_known_controller():
    genomes = np.zeros((5,2,8))
    genomes[:,0,5] = 1.0  # left-minus-right controls positive turning
    response = stimulus_response(genomes)
    assert response["directional_cue_response"] > 0
    genomes[:,0,5] = -1
    assert stimulus_response(genomes)["directional_cue_response"] < 0
    assert np.all(motor_outputs(genomes, cue_sensors(.5,.5,.5))[1] > 0)


def test_effective_weights_preserve_raw_linear_network():
    rng = np.random.default_rng(5)
    g = rng.normal(size=(20,2,8))
    raw = cue_sensors(.3,.8,.1, energy_fraction=.9, crowd=.2)
    effective = effective_gene_weights(g)
    channels = np.array([.3,.8,.1,.9,.2,1.])
    assert np.allclose(np.einsum('nij,j->ni',g,raw),np.einsum('nij,j->ni',effective,channels))


def test_probe_replay_and_no_resurrection():
    g = World(Config(founders=18), 15).genomes
    a = run_probe(g, 300, 28, .006, intervention="fixed_speed")
    b = run_probe(g, 300, 28, .006, intervention="fixed_speed")
    assert a == b
    assert np.isnan(run_probe(g[:0], 300, 28, .006)["harvest"])


def test_small_end_to_end_investigation(tmp_path):
    result = run_investigation(seeds=[240,241],steps=25,probe_ticks=12,output=tmp_path,
                               regrowths=(.030,.006),probe_regrowths=(.030,.006),count=20,
                               save_checkpoints=False)
    assert result['parameters']['training_seeds'] == [240,241]
    assert (tmp_path/'effective_genes.csv').exists()
    assert (tmp_path/'probe_trials.csv').exists()
    assert result['harvest_contrasts']['growth_0.030']['evolved_minus_founder']['paired_seeds'] == 2


def test_regrowth_experiments_share_exact_initial_condition():
    high = World(Config(growth_rate=.030), 91)
    scarce = World(Config(growth_rate=.001), 91)
    for name in ("capacity", "food", "x", "y", "angle", "energy", "genomes"):
        assert np.array_equal(getattr(high, name), getattr(scarce, name))
    assert high.rng.bit_generator.state == scarce.rng.bit_generator.state
    for _ in range(40):
        high.step()
        scarce.step()
    assert not np.array_equal(high.food, scarce.food)


def test_save_load_intervention_roundtrip(tmp_path):
    w = World(Config(founders=18, growth_rate=.006, fixed_speed=.60,
                     sensor_mode="mirror_food"), 71)
    for _ in range(14):
        w.step()
    path = tmp_path / "intervention.npz"
    w.save(path)
    restored = World.load(path)
    assert restored.config == w.config
    assert np.array_equal(restored.genomes, w.genomes)
    for _ in range(8):
        assert w.step() == restored.step()
