# Optional SQLite lineage archive

Long-lived simulations can store deceased-organism biographies in SQLite rather than an ever-growing Python dictionary. `World.enable_disk_archive(path)` moves current deaths into a SQLite archive and then writes subsequent deaths there. The data are indexed by organism ID and the two parent IDs. The living ecosystem and its random number stream are unaffected. The normal mode remains in-memory for backwards compatibility.

Run from the command line:

```bash
python -m biosphere run --genetics --regulation --disk-archive --seed 19 --steps 10000 --output results/long_run
```

This produces `long_life_archive.sqlite` and a complete `world.npz`. Checkpoints embed a consistent SQLite snapshot; they can be moved without carrying a separate sidecar. Loading a checkpoint materializes a temporary working archive, cleaned when the object closes. Archive reads query by ID, recent deaths or indexed parent IDs. Old in-memory checkpoints still load.

**Limitations:** the checkpoint must still read and compress the full database when saving; this operation uses memory proportional to the snapshot size, so the system is not unlimited. `viewer.py` displays the 2,500 newest disk-backed deaths, although any older specimen can be queried by ID through `World.specimen`. There is not yet an asynchronous archive writer, a transactional multi-file backup, distributed data store, or GUI search across millions of historical individuals. SQLite runtime RAM reduction and full backup portability are the implemented features—not an unlimited-memory guarantee.
