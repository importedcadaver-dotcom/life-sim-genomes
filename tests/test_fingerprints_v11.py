"""Pinned-environment full-world v1.1 characterization fingerprints.

Baseline generation environment (exact): Python 3.13.5, NumPy 2.3.5.
Fingerprints include EVERY saved living array and both resource arrays, the
complete config, RNG state, counters, life archive and all event histories.
Never regenerate the expectations to conceal a behavior change.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import platform

import numpy as np
import pytest

from biosphere.genetics import INDEX
from biosphere.simulation import Config, World
from biosphere.state_schema import SAVED_ARRAY_FIELDS


BASELINE_ENVIRONMENT = {"python": "3.13.5", "numpy": "2.3.5"}
# Each entry is a baseline captured from the Step 0 Git-tagged v1.1 engine.
EXPECTED_FINGERPRINTS = {
    "legacy:37": "66c7d54d846ff0e54bbc71f4379b868ece937cfe88efcc7761bcd8693d1e2b07",
    "legacy:93": "9cf9a7f6fd05b8680a01687d5e12c8e4e6e1f289a4548880808328f71464f4a4",
    "genetic:37": "71d4fa1fdbd33a0e52ac1072e808573318c5ed886e5a8b7f4458abbe10ad7cdd",
    "genetic:93": "f02cf551be27c6629ad28c814676d1a981e2150891b135fc7dd976e1740f6c0c",
    "regulatory:37": "757b357552ca02ce930d5ace988c135324b312e2a80c1ae160bfef278dd9819f",
    "regulatory:93": "1c5b22a1bdbba1a15fa33fca9d1512f57c3d329485875ba0ff9fbb3d598d5eb0",
}


def _require_pinned_environment() -> None:
    actual = {"python": platform.python_version(), "numpy": np.__version__}
    if actual != BASELINE_ENVIRONMENT:
        pytest.fail(
            f"ENVIRONMENT MISMATCH: expected Python {BASELINE_ENVIRONMENT['python']} "
            f"and NumPy {BASELINE_ENVIRONMENT['numpy']}; got Python "
            f"{actual['python']} and NumPy {actual['numpy']}. "
            "Do not regenerate fingerprints or weaken comparisons.",
            pytrace=False,
        )


def _canonical(value):
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        # No mutable NumPy arrays may bypass the SAVED_ARRAY_FIELDS contract.
        raise AssertionError("unexpected ndarray outside schema fields")
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    return value


def world_fingerprint(world: World) -> str:
    """Hash typed/shape-aware arrays plus all remaining world state and events."""
    fields = set(SAVED_ARRAY_FIELDS)
    unseen_arrays = [
        name for name, value in vars(world).items()
        if isinstance(value, np.ndarray) and name not in fields
    ]
    assert not unseen_arrays, f"UNTRACKED STATE ARRAYS: {unseen_arrays}"
    array_state = {}
    for name in SAVED_ARRAY_FIELDS:
        value = np.ascontiguousarray(getattr(world, name))
        array_state[name] = {
            "dtype": value.dtype.str,
            "shape": list(value.shape),
            "sha256": hashlib.sha256(value.tobytes()).hexdigest(),
        }
    other_state = {
        name: value for name, value in vars(world).items()
        if name not in fields and name not in ("rng", "config")
    }
    payload = {
        "schema_arrays": array_state,
        "config": asdict(world.config),
        "rng_state": world.rng.bit_generator.state,
        "world_state_and_events": other_state,
    }
    encoded = json.dumps(_canonical(payload), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_world(mode: str, seed: int) -> World:
    assert mode in ("legacy", "genetic", "regulatory")
    config = Config(
        width=22,
        height=20,
        founders=26,
        max_population=72,
        lifespan=160,
        reproduction_age=10,
        growth_rate=0.012,
        genetics_enabled=mode != "legacy",
        regulation_enabled=mode == "regulatory",
        reproduction_mode="mixed",
    )
    world = World(config, seed=seed)
    for _ in range(130):
        world.step()
    return world


@pytest.mark.parametrize("mode,seed", [
    ("legacy", 37), ("legacy", 93),
    ("genetic", 37), ("genetic", 93),
    ("regulatory", 37), ("regulatory", 93),
])
def test_fixed_seed_entire_world_fingerprint_repeated(mode: str, seed: int) -> None:
    _require_pinned_environment()
    key = f"{mode}:{seed}"
    expected = EXPECTED_FINGERPRINTS[key]
    first = world_fingerprint(make_world(mode, seed))
    second = world_fingerprint(make_world(mode, seed))
    if first != second:
        pytest.fail(
            f"BEHAVIOR MISMATCH: {key} differs between two identical runs: "
            f"first={first}, second={second}", pytrace=False,
        )
    if first != expected:
        pytest.fail(
            f"BEHAVIOR MISMATCH: {key} expected={expected}, actual={first}",
            pytrace=False,
        )


def test_regulatory_sensor_distance_remains_fixed_while_neural_sensor_range_is_inherited() -> None:
    """Pin *current* behavior: regulatory offset ignores the sensor_range locus."""
    _require_pinned_environment()
    config = Config(
        width=48, height=48, founders=1, max_population=3,
        genetics_enabled=True, regulation_enabled=True,
        sensor_distance=3.0,
    )
    world = World(config, seed=197)
    world.x[:] = 20
    world.y[:] = 20
    world.angle[:] = 0
    world.body_dna[:] = 0
    world.gene_copies[:] = 1
    world.capacity.fill(12)
    world.food.fill(0)
    # Config-distance sample at 3.0: left (21,22), right (21,17).
    # Inherited-longer-distance sample at ~5.33: left (22,24), right (22,15).
    world.food[22, 21] = 12
    world.food[15, 22] = 12
    near_reg = world._regulation_signals()
    near_neural = world.perceive()
    world.body_dna[0, INDEX["sensor_range"]] = 2.5
    far_reg = world._regulation_signals()
    far_neural = world.perceive()
    assert near_reg[0, 5] == pytest.approx(1.0)
    assert far_reg[0, 5] == pytest.approx(1.0)
    assert near_neural[0, 2] > near_neural[0, 3]
    assert far_neural[0, 2] < far_neural[0, 3]
