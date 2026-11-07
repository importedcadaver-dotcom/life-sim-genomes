"""Optional bounded-RAM, SQLite-backed archive for deceased organisms.

Only the already-dead observation records are stored here. Live organisms,
reproduction, RNG and ecological behavior never query this database.
Checkpoint saves embed a consistent SQLite snapshot, so a checkpoint remains
self-contained, portable and replayable without a fragile external sidecar.
"""
from __future__ import annotations

from collections.abc import MutableMapping, Iterator
import json
from pathlib import Path
import sqlite3
import tempfile
from typing import Any


class DiskArchive(MutableMapping[int, dict[str, Any]]):
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS lives ("
                        "id INTEGER PRIMARY KEY, parent INTEGER, parent2 INTEGER, data TEXT NOT NULL)")
        self.db.execute("CREATE INDEX IF NOT EXISTS lives_parent ON lives(parent)")
        self.db.execute("CREATE INDEX IF NOT EXISTS lives_parent2 ON lives(parent2)")
        self.db.commit()

    def __setitem__(self, key: int, value: dict[str, Any]) -> None:
        self.db.execute("INSERT OR REPLACE INTO lives(id, parent, parent2, data) VALUES(?,?,?,?)",
                        (int(key), int(value.get("parent_id", -1)),
                         int(value.get("parent2_id", -1)), json.dumps(value, separators=(",", ":"))))
        # Live in-process inserts are visible immediately. SQLite's WAL can
        # batch transactions until the next checkpoint or explicit flush.

    def __getitem__(self, key: int) -> dict[str, Any]:
        row = self.db.execute("SELECT data FROM lives WHERE id=?", (int(key),)).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row[0])

    def __delitem__(self, key: int) -> None:
        if self.db.execute("DELETE FROM lives WHERE id=?", (int(key),)).rowcount == 0:
            raise KeyError(key)

    def __iter__(self) -> Iterator[int]:
        for (id_,) in self.db.execute("SELECT id FROM lives ORDER BY id"):
            yield int(id_)

    def __len__(self) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM lives").fetchone()[0])

    def items(self):
        for id_, data in self.db.execute("SELECT id, data FROM lives ORDER BY id"):
            yield int(id_), json.loads(data)

    def recent(self, limit: int = 32, offset: int = 0) -> list[dict[str, Any]]:
        return [json.loads(row[0]) for row in
                self.db.execute("SELECT data FROM lives ORDER BY id DESC LIMIT ? OFFSET ?",
                                (max(0, int(limit)), max(0, int(offset))))]

    def children_ids(self, parent: int, limit: int, offset: int,
                     *, newest_first: bool = False) -> list[int]:
        direction = "DESC" if newest_first else "ASC"
        return [int(row[0]) for row in self.db.execute(
            f"SELECT id FROM lives WHERE parent=? OR parent2=? ORDER BY id {direction} LIMIT ? OFFSET ?",
            (parent, parent, limit, offset))]

    def snapshot_bytes(self) -> bytes:
        """Consistent SQLite backup included inside a single atomic NPZ save."""
        self.db.commit()
        with tempfile.TemporaryDirectory(prefix="biosphere_archive_backup_") as folder:
            path = Path(folder) / "archive.sqlite"
            target = sqlite3.connect(path)
            try:
                self.db.backup(target)
            finally:
                target.close()
            return path.read_bytes()

    @classmethod
    def from_bytes(cls, data: bytes) -> "DiskArchive":
        folder = tempfile.TemporaryDirectory(prefix="biosphere_archive_loaded_")
        path = Path(folder.name) / "history.sqlite"
        path.write_bytes(data)
        archive = cls(path)
        archive._temporary_folder = folder
        return archive

    def flush(self) -> None:
        self.db.commit()

    def close(self) -> None:
        if not hasattr(self, 'db'):
            return
        self.db.commit()
        self.db.close()
        del self.db
        if hasattr(self, '_temporary_folder'):
            self._temporary_folder.cleanup()
            del self._temporary_folder

    def __del__(self) -> None:
        if hasattr(self, 'db'):
            try:
                self.close()
            except (sqlite3.Error, OSError):
                pass
