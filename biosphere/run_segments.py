"""Non-destructive continuation of CLI simulation runs.

This module manages *only* resumed headless outputs. Fresh runs retain their
historical file placement and overwrite semantics pending a separate decision.
It does not change simulation, checkpoint formats, or evolutionary RNG usage.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any
import uuid


_SEGMENT_NAME = re.compile(r"segment-[0-9]{6}\Z")
_FILES = ("metrics.csv", "lineage.csv", "world.npz", "summary.json", "segment.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot read run metadata {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid run metadata object: {path}")
    return data


def _prior_segments(root: Path) -> list[tuple[str, Path, dict[str, Any]]]:
    directory = root / "segments"
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise ValueError(f"Cannot resume: segments path is not a directory: {directory}")
    records = []
    for candidate in sorted(directory.iterdir()):
        if not _SEGMENT_NAME.fullmatch(candidate.name):
            # Ignore temporary directories left by interrupted runs; never delete them.
            continue
        metadata_path = candidate / "segment.json"
        if not candidate.is_dir() or not metadata_path.is_file():
            raise ValueError(f"Incomplete segment: {candidate}. No files were changed.")
        record = _read_object(metadata_path)
        if record.get("segment") != candidate.name or int(record.get("end_tick", -1)) < int(record.get("start_tick", -1)):
            raise ValueError(f"Invalid segment metadata: {metadata_path}")
        if any(not (candidate / name).is_file() for name in _FILES):
            raise ValueError(f"Incomplete segment outputs: {candidate}")
        if sha256(candidate / "world.npz") != record.get("checkpoint_sha256"):
            raise ValueError(f"Segment checkpoint hash does not match metadata: {candidate}")
        records.append((candidate.name, candidate, record))
    for previous, current in zip(records, records[1:]):
        older = previous[2]
        newer = current[2]
        if (int(older["end_tick"]) != int(newer["start_tick"]) or
                older["checkpoint_sha256"] != newer.get("source_sha256")):
            raise ValueError(f"Overlapping or disconnected run segments: {current[0]}")
    return records


@dataclass(frozen=True)
class ResumePlan:
    source: Path
    root: Path
    target: Path
    number: str
    source_sha256: str
    start_tick: int
    overwrite: bool

    def stage(self) -> Path:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=".pending-", dir=self.target.parent))

    def publish(self, staged: Path, end_tick: int) -> None:
        if end_tick < self.start_tick:
            raise ValueError("Cannot publish a segment that moves simulation time backward")
        metadata = {
            "format": "biosphere-headless-segment-1",
            "segment": self.number,
            "source_checkpoint": str(self.source.resolve()),
            "source_sha256": self.source_sha256,
            "start_tick": self.start_tick,
            "end_tick": end_tick,
            "checkpoint_sha256": sha256(staged / "world.npz"),
        }
        (staged / "segment.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        if not self.overwrite:
            if self.target.exists():
                raise FileExistsError(f"Segment already exists: {self.target}")
            # Publish the complete directory in one rename. Never open old output files.
            staged.rename(self.target)
            return
        # Only preflight-approved terminal replacements reach this path.
        backup = self.target.with_name(f".replaced-{uuid.uuid4().hex}")
        self.target.rename(backup)
        try:
            staged.rename(self.target)
        except BaseException:
            backup.rename(self.target)
            raise
        shutil.rmtree(backup)


def plan_resume(output: Path, source_arg: Path | None, *, latest: bool = False,
                segment: str | None = None, overwrite: bool = False) -> ResumePlan:
    """Reject stale, overlapping or unrelated resumes *before* any output writes."""
    root = output.resolve()
    earlier = _prior_segments(root)
    if latest:
        if source_arg is not None:
            raise ValueError("Use either --resume or --resume-latest, not both")
        source = earlier[-1][1] / "world.npz" if earlier else root / "world.npz"
    elif source_arg is not None:
        source = Path(source_arg).resolve()
    else:
        raise ValueError("Resume requires --resume PATH or --resume-latest")
    if not source.is_file():
        raise FileNotFoundError(f"Resume checkpoint does not exist: {source}")
    source_hash = sha256(source)
    latest_tick = None
    if earlier:
        _, last_folder, last_record = earlier[-1]
        current_checkpoint = last_folder / "world.npz"
        latest_tick = int(last_record["end_tick"])
        latest_hash = last_record["checkpoint_sha256"]
    else:
        current_checkpoint = root / "world.npz"
        if current_checkpoint.is_file():
            summary = root / "summary.json"
            if not summary.is_file():
                raise ValueError(f"Existing root checkpoint lacks summary.json: {root}")
            latest_tick = int(_read_object(summary)["steps_completed"])
            latest_hash = sha256(current_checkpoint)
        else:
            latest_hash = None
            if (root / "metrics.csv").exists() or (root / "lineage.csv").exists():
                raise ValueError(f"Output contains records but no root checkpoint: {root}")

    if overwrite:
        if segment is None or not _SEGMENT_NAME.fullmatch(segment):
            raise ValueError("--overwrite requires --segment segment-NNNNNN")
        if not earlier or segment != earlier[-1][0]:
            raise ValueError("--overwrite may replace only the terminal run segment")
        record = earlier[-1][2]
        if source_hash != record.get("source_sha256"):
            raise ValueError("Overwrite source does not match the original terminal segment source")
        start_tick = int(record["start_tick"])
        target = earlier[-1][1]
    else:
        if segment is not None:
            raise ValueError("--segment is only valid with --overwrite")
        if latest_hash is not None and source_hash != latest_hash:
            raise ValueError(
                f"STALE CHECKPOINT / OVERLAPPING TICKS: latest recorded tick is {latest_tick}; "
                f"resume from {current_checkpoint} (or use --resume-latest). "
                "Original records were not touched."
            )
        next_number = int(earlier[-1][0][-6:]) + 1 if earlier else 1
        if next_number > 999999:
            raise ValueError("Segment number limit reached")
        segment = f"segment-{next_number:06d}"
        target = root / "segments" / segment
        if target.exists():
            raise FileExistsError(f"Segment destination exists: {target}")
        start_tick = int(latest_tick) if latest_tick is not None else -1

    return ResumePlan(source, root, target, segment, source_hash, start_tick, overwrite)


def check_resume_tick(plan: ResumePlan, tick: int) -> ResumePlan:
    """Call after checkpoint loading, before output/archive creation."""
    if plan.start_tick >= 0 and tick != plan.start_tick:
        raise ValueError(
            f"STALE CHECKPOINT / OVERLAPPING TICKS: checkpoint tick {tick}, "
            f"expected {plan.start_tick}; no output files were changed"
        )
    if tick < 0:
        raise ValueError("Invalid negative checkpoint tick")
    if plan.start_tick < 0:
        from dataclasses import replace
        return replace(plan, start_tick=tick)
    return plan
