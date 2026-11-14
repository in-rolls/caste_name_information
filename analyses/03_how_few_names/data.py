"""Surname frequencies from instate's 2017 electoral rolls.

Two floors in the shipped table bound everything built on it, and both are
stated in the note rather than left for a reader to discover:

``total_n >= 3``   names appearing once or twice are absent, so the real tail is
                   longer than any curve here.
``len(name) >= 3`` single- and double-letter tokens are gone. In the south that
                   is most of the population: in the Kerala PSC records, 78.5%
                   of 1.44M people have a last token that is one initial.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from last_name_basis.siblings import repo

# outkast covers these; the crosswalk lets analysis 03 join to analysis 01.
OUTKAST_TO_INSTATE = {
    "uttar pradesh": "Uttar Pradesh",
    "bihar": "Bihar",
    "haryana": "Haryana",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal",
    "odisha": "Odisha",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "gujarat": "Gujarat",
    "kerala": "Kerala",
    "tamilnadu": "Tamil Nadu",
    "assam": "Assam",
    "sikkim": "Sikkim",
    "nagaland": "Nagaland",
    "mizoram": "Mizoram",
    "arunachal pradesh": "Arunachal Pradesh",
}

FEATURED = ["Punjab", "Bihar", "Uttar Pradesh", "Delhi", "Tamil Nadu", "Kerala"]


def instate_table() -> Path | None:
    try:
        from importlib.resources import files

        p = Path(str(files("instate"))) / "data/instate_unique_ln_state_prop_v2.parquet"
        if p.exists():
            return p
    except (ImportError, ModuleNotFoundError):
        pass
    p = repo("instate") / "src/instate/data/instate_unique_ln_state_prop_v2.parquet"
    return p if p.exists() else None


def surnames() -> pd.DataFrame | None:
    """One row per surname: national count and per-state counts."""
    path = instate_table()
    if path is None:
        return None
    d = pd.read_parquet(path)
    states = [c for c in d.columns if c not in ("last_name", "total_n")]
    counts = d[states].mul(d["total_n"], axis=0)
    counts.insert(0, "last_name", d["last_name"].to_numpy())
    counts["national"] = d["total_n"].to_numpy()
    return counts


def curve(counts: pd.Series) -> np.ndarray:
    """Cumulative share of people against surname rank, commonest first."""
    n = np.sort(counts.to_numpy(dtype=float))[::-1]
    n = n[n > 0]
    return np.cumsum(n) / n.sum()


def names_for(counts: pd.Series, share: float = 0.5) -> int:
    """How many of the commonest names it takes to cover `share` of people."""
    return int(np.searchsorted(curve(counts), share) + 1)


def kerala_initial_share() -> float | None:
    """Share of Kerala PSC candidates whose last token is a single letter.

    Uses only the name field. The `community` column in that file is missing
    precisely on the forward castes -- 82% of Nairs are unlabelled against 17%
    overall -- so nothing here touches it.
    """
    p = (
        repo("pranaam")
        / "scripts/data-acquisition/kerala_psc/raw/psc_candidates.parquet"
    )
    if not p.exists():
        return None
    d = pd.read_parquet(p, columns=["name"])
    last = d["name"].fillna("").str.strip().str.split().str[-1].fillna("")
    return float((last.str.len() == 1).mean())


GENDERED = {
    "devi",
    "kumari",
    "bai",
    "rani",
    "begam",
    "begum",
    "khatun",
    "bibi",
    "banu",
    "beevi",
    "kaur",
}


def first_name_gender(min_bearers: int = 200) -> dict[str, float] | None:
    """P(female | first name), from naampy's electoral-roll counts.

    Used to ask who carries which last name. The gender comes from the first
    name and the question is about the last name, so the two are independent.
    """
    p = repo("naampy") / "in_rolls_state_year_fn_naampy.csv.gz"
    if not p.exists():
        return None
    d = pd.read_csv(p, usecols=["first_name", "n_female", "n_male"])
    g = d.groupby("first_name")[["n_female", "n_male"]].sum()
    n = g["n_female"] + g["n_male"]
    return (g["n_female"] / n)[n >= min_bearers].to_dict()


def sex_marked_share(state: str, gender: dict[str, float]) -> dict | None:
    """Share of each sex whose last name is one of the gendered ones.

    Reads the raw per-state roll rather than the aggregated table, because it
    needs the first and last name of the same person.
    """
    import csv
    import gzip

    path = repo("instate") / f"data/names_{state}.csv.gz"
    if not path.exists():
        return None

    female = male = female_marked = male_marked = 0.0
    matched = total = 0
    with gzip.open(path, "rt") as fh:
        for row in csv.DictReader(fh):
            n = int(row["n_times"])
            total += n
            parts = row["english_name"].split()
            if len(parts) < 2:
                continue
            p_female = gender.get(parts[0])
            if p_female is None:
                continue
            matched += n
            female += n * p_female
            male += n * (1 - p_female)
            if parts[-1] in GENDERED:
                female_marked += n * p_female
                male_marked += n * (1 - p_female)
    if not matched:
        return None
    return {
        "state": state,
        "people_matched": matched,
        "coverage": matched / total,
        "female_share": female / matched,
        "women_sex_marked": female_marked / female,
        "men_sex_marked": male_marked / male,
    }
