"""Bihar ladders: what a surname buys you at successively coarser geographies.

Two ready-made ladders ship inside the `naampata` package in the `naampata` repo.
Both are already aggregated to (level, cell, group) counts, so nothing here
touches the individual-level files in `land/data/derived/`, which run to a
gigabyte apiece.

A third target is built here: the five reservation categories split by religion,
using the caste dictionary in `land/data/caste_codes/`, which carries a `muslim`
flag alongside each caste's category.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from last_name_basis.siblings import repo

# Rungs from finest to coarsest, so a ladder always plots in the right order.
RECORD_RUNGS = ["surname+village", "surname+zone", "surname+district", "surname"]
CENSUS_RUNGS = [
    "surname+village",
    "surname+panchayat",
    "surname+block",
    "surname+district",
    "surname",
]
PLACE_ONLY = {"village", "zone", "panchayat", "block", "district"}

RUNG_LABEL = {
    "surname+village": "surname + village",
    "surname+panchayat": "surname + panchayat",
    "surname+block": "surname + block",
    "surname+zone": "surname + zone",
    "surname+district": "surname + district",
    "surname": "surname alone, statewide",
    "village": "village alone, no name",
    "panchayat": "panchayat alone, no name",
    "zone": "zone alone, no name",
}


def _naampata(name: str) -> Path | None:
    try:
        from importlib.resources import files

        p = Path(str(files("naampata"))) / "data" / name
        if p.exists():
            return p
    except (ImportError, ModuleNotFoundError):
        pass
    p = repo("naampata") / "src/naampata/data" / name
    return p if p.exists() else None


def records_ladder() -> pd.DataFrame | None:
    """Bihar land records: 141 jatis, land-owning accounts only."""
    p = _naampata("records_ladder.parquet")
    return pd.read_parquet(p) if p else None


def census_ladder() -> pd.DataFrame | None:
    """Mahadalit census: 22 Scheduled Caste jatis, SC households only."""
    p = _naampata("census_ladder.parquet")
    return pd.read_parquet(p) if p else None


def caste_dictionary() -> pd.DataFrame | None:
    """Caste name -> reservation category and a Muslim flag.

    `caste_category` is one of ebc / bc2 / sc / st / uc. Muslim castes are
    folded into those same categories -- Sheikh and Pathan sit in `uc`, Momin
    and Ansari in `ebc` -- so religion has to come from the separate flag.
    """
    p = repo("land") / "data/caste_codes/caste_dictionary_n292.dta"
    if not p.exists():
        return None
    d = pd.read_stata(p)
    d = d[["caste_name", "caste_category", "muslim"]].copy()
    d["caste_name"] = d["caste_name"].str.strip().str.lower()
    d["muslim"] = d["muslim"].astype(int)
    return d.drop_duplicates("caste_name")


def with_group(ladder: pd.DataFrame, target: str) -> pd.DataFrame:
    """Relabel a ladder's rows to the requested target and re-key the counts.

    ``jati``     the ladder's own 141 groups.
    ``category`` the five reservation categories.
    ``category_religion`` the same five, but upper-caste and backward Muslim
                 castes broken out, because that is the split people actually
                 use and it is invisible in `category` alone.
    """
    d = ladder.copy()
    if target == "jati":
        d["group"] = d["jati"]
        return d
    if target == "category":
        d["group"] = d["category"]
        return d
    if target != "category_religion":
        raise ValueError(f"unknown target: {target!r}")

    lookup = caste_dictionary()
    if lookup is None:
        raise FileNotFoundError("caste dictionary not available")
    flag = dict(zip(lookup["caste_name"], lookup["muslim"]))
    is_muslim = d["jati"].str.strip().str.lower().map(flag).fillna(0).astype(int)
    d["group"] = d["category"].where(is_muslim == 0, "muslim")
    return d
