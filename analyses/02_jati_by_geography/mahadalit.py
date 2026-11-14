"""The Bihar Mahadalit census, scored one rung finer than the shipped ladder.

`naampata`'s `census_ladder` stops at the village. The raw district files carry
a level below it -- `tola_basti`, the hamlet -- which is the finest geography in
any of this data and has never been scored.

Everything here is Scheduled Caste by construction, so the numbers are
within-Dalit across 22 jatis and are not comparable to the 141-jati land ladder.
"""

from __future__ import annotations

import glob
from pathlib import Path

import pandas as pd

from last_name_basis.siblings import repo

# Finest to coarsest. The keys nest, so each rung is a strict coarsening.
GEO = ["district", "block", "panchayat_nagar", "vill_ward", "tola_basti"]

RUNGS = {
    "surname+tola": GEO,
    "surname+village": GEO[:4],
    "surname+panchayat": GEO[:3],
    "surname+block": GEO[:2],
    "surname+district": GEO[:1],
    "surname": [],
}

# Place alone, no name. The hamlets are often caste-named -- "chamar tola",
# "mushar tola" -- so this is the rung that says whether the surname is adding
# anything or the segregation is doing the work.
PLACE_ONLY = {
    "tola alone": GEO,
    "village alone": GEO[:4],
    "district alone": GEO[:1],
}

RUNG_LABEL = {
    "surname+tola": "surname + hamlet",
    "surname+village": "surname + village",
    "surname+panchayat": "surname + panchayat",
    "surname+block": "surname + block",
    "surname+district": "surname + district",
    "surname": "surname alone, statewide",
}


def census_dir() -> Path:
    return repo("land") / "data/mahadalit_census_district_wise_csv"


def load() -> pd.DataFrame | None:
    """All district files, with the head-of-household surname extracted.

    The surname is the last token here: matching head against father names,
    59.8% of shared tokens sit last and 0.3% first. That is checked rather than
    assumed, because Maharashtra's rolls put it first.
    """
    files = sorted(glob.glob(str(census_dir() / "*.csv")))
    if not files:
        return None
    cols = GEO + ["name_hoh", "name_fat", "jati"]
    d = pd.concat(
        [pd.read_csv(f, usecols=cols, dtype=str) for f in files], ignore_index=True
    )
    d = d.dropna(subset=["name_hoh", "jati"])
    for c in GEO + ["name_hoh", "name_fat", "jati"]:
        d[c] = d[c].fillna("").str.strip().str.lower()
    d["surname"] = d["name_hoh"].str.split().str[-1]
    return d[d["surname"].str.len() >= 2]


def ladder(d: pd.DataFrame) -> pd.DataFrame:
    """One long frame the shared scorer can take: level, cell, jati, households."""
    rows = []
    for level, keys in RUNGS.items():
        parts = [d[k] for k in keys] + [d["surname"]]
        cell = parts[0] if len(parts) == 1 else parts[0].str.cat(parts[1:], sep="|")
        rows.append(pd.DataFrame({"level": level, "cell": cell, "jati": d["jati"]}))
    for level, keys in PLACE_ONLY.items():
        parts = [d[k] for k in keys]
        cell = parts[0] if len(parts) == 1 else parts[0].str.cat(parts[1:], sep="|")
        rows.append(pd.DataFrame({"level": level, "cell": cell, "jati": d["jati"]}))
    out = pd.concat(rows, ignore_index=True)
    out["households"] = 1
    return out
