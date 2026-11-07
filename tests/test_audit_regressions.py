"""Step 1 characterization: known v1.1 defects, deliberately strict xfails.

These tests describe the separately approved *future* behavior.  Their xfail
markers MUST be removed only in the approved, individual defect-fix steps.
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import pytest

from biosphere.simulation import Config, World


def test_resume_preserves_existing_csv_and_creates_new_segment(tmp_path: Path) -> None:
    """Phase 2.0: 200-step run, then three-step resume into same directory."""
    output = tmp_path / "run"
    base_cmd = [sys.executable, "-m", "biosphere", "run"]
    subprocess.run(
        [*base_cmd, "--genetics", "--reproduction-mode", "asexual",
         "--seed", "3", "--founders", "30", "--max-population", "100",
         "--steps", "200", "--sample-every", "1", "--events",
         "--output", str(output)],
        check=True, capture_output=True, text=True,
    )
    before_metrics = (output / "metrics.csv").read_bytes()
    before_lineage = (output / "lineage.csv").read_bytes()
    assert len(list(csv.reader(before_metrics.decode().splitlines()))) > 10
    assert len(list(csv.reader(before_lineage.decode().splitlines()))) > 1
    subprocess.run(
        [*base_cmd, "--resume", str(output / "world.npz"),
         "--steps", "3", "--sample-every", "1", "--events",
         "--output", str(output)],
        check=True, capture_output=True, text=True,
    )
    # These must remain EXACTLY unchanged after a resumed run.
    assert (output / "metrics.csv").read_bytes() == before_metrics
    assert (output / "lineage.csv").read_bytes() == before_lineage
    # The future output policy is a unique, non-destructive run segment.
    segment = output / "segments" / "segment-000001"
    assert (segment / "metrics.csv").exists()
    assert (segment / "lineage.csv").exists()
    assert (segment / "world.npz").exists()
    assert (segment / "summary.json").exists()


@pytest.mark.xfail(
    strict=True,
    raises=ZeroDivisionError,
    reason="v1.1 accepts zero reproduction cost then divides by it (reproduction.py:147)",
)
def test_new_biological_world_rejects_zero_cost_before_reproduction() -> None:
    """Phase 2.0 reproduction: Config accepts a cost of zero and step crashes."""
    with pytest.raises(ValueError, match=r"reproduction_cost"):
        config = Config(
            founders=1,
            max_population=2,
            genetics_enabled=True,
            reproduction_mode="asexual",
            allow_mutation=False,
            reproduction_cost=0,
            newborn_energy=0,
            reproduction_age=0,
        )
        world = World(config, seed=5)
        world.energy[:] = 100
        world.step()


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="v1.1 asexual generation uses unrelated organism at array index 0 (reproduction.py:158)",
)
def test_asexual_child_generation_only_uses_actual_parent() -> None:
    """Phase 2.0 exact case: unrelated generation-10, actual parent generation-1."""
    config = Config(
        founders=2,
        max_population=3,
        genetics_enabled=True,
        reproduction_mode="asexual",
        allow_mutation=False,
        reproduction_age=1,
    )
    world = World(config, seed=7)
    world.generation[:] = [10, 1]
    world.age[:] = [0, 50]
    world.energy[:] = [0, 100]
    world.step()
    birth_events = [
        (event["id"], event["parent_id"], event["parent2_id"], event["generation"])
        for event in world.last_events if event["kind"] == "birth"
    ]
    assert birth_events == [(2, 1, -1, 2)]
    assert int(world.generation[-1]) == 2
