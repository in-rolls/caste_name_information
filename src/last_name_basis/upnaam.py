"""Validated reader for Upnaam's aggregate electoral-roll outputs."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from last_name_basis.siblings import repo

RESOLVER_REVISION = "resolver-v1"
ROLL_COLUMNS = (
    "source_row",
    "state",
    "name_raw",
    "weight",
    "surname",
    "surname_position",
    "abstained",
    "resolver_revision",
)


def resolved_roll_path(state: str) -> Path:
    """Return the expected local Upnaam artifact for one state."""
    return repo("upnaam") / "data" / "derived" / "resolved" / f"{state}.parquet"


def iter_resolved_roll(
    path: Path,
    *,
    state: str,
    expected_revision: str = RESOLVER_REVISION,
    batch_size: int = 100_000,
) -> Iterator[pd.DataFrame]:
    """Yield validated Upnaam aggregate rows without changing their cardinality.

    The contract is one output row per aggregate input cell, ordered and keyed
    by consecutive ``source_row``. ``weight`` is the source ``n_times`` value;
    rows are never expanded into synthetic electors.
    """
    parquet = pq.ParquetFile(path)
    missing = set(ROLL_COLUMNS).difference(parquet.schema_arrow.names)
    if missing:
        raise ValueError(f"Upnaam artifact is missing columns: {sorted(missing)}")
    expected_row = 0
    for batch in parquet.iter_batches(columns=ROLL_COLUMNS, batch_size=batch_size):
        frame = batch.to_pandas()
        rows = frame["source_row"].to_numpy(dtype="int64")
        expected = np.arange(expected_row, expected_row + len(frame), dtype="int64")
        if not np.array_equal(rows, expected):
            raise ValueError(f"Upnaam source_row is not consecutive at {expected_row}")
        required_values = ("state", "weight", "abstained", "resolver_revision")
        if frame.loc[:, required_values].isna().any().any():
            raise ValueError("Upnaam contract fields must not be missing")
        if set(frame["state"].dropna()) != {state}:
            raise ValueError(f"Upnaam artifact contains rows outside state {state!r}")
        revisions = set(frame["resolver_revision"].dropna())
        if revisions != {expected_revision}:
            raise ValueError(
                f"Upnaam resolver revision must be {expected_revision!r}; "
                f"observed {sorted(revisions)!r}"
            )
        if frame["weight"].isna().any() or frame["weight"].le(0).any():
            raise ValueError("Upnaam weight must contain positive values")
        invalid_resolution = frame["abstained"].eq(frame["surname"].notna())
        if invalid_resolution.any():
            raise ValueError("Upnaam surname and abstained fields disagree")
        resolved_positions = set(frame.loc[~frame["abstained"], "surname_position"])
        if not resolved_positions.issubset({"first", "last"}):
            raise ValueError("Upnaam resolved rows require first or last position")
        expected_row += len(frame)
        yield frame
    if expected_row != parquet.metadata.num_rows:
        raise ValueError("Upnaam row count changed during iteration")
