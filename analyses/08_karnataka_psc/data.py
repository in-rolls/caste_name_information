"""What a surname reveals about caste in Karnataka.

Karnataka is absent from SECC. outkast covers nineteen states and Karnataka is
not among them, and in the south it holds only Kerala and Tamil Nadu, so these
recruitment lists are the only caste-linked name data this project has for the
state.

Recovering the surname takes a step first, because the commonest last tokens
here are single initials.

    S 772   R 550   K 534   N 514   B 375   G 304 ...   PATIL 161

Eleven initials before the first real surname. A pipeline that takes the last
token and calls it a surname is, in Karnataka, mostly measuring initials.

The data are Karnataka Public Service Commission select lists: 14,854 rows of
`name`, `reservation`, `district`, `pin`. Two things about them govern how the
result may be read, and both belong in the first paragraph of anything written
from this:

  * PSC candidates are a **selected population** -- educated applicants for
    government jobs -- so nothing here estimates a population quantity.
  * `reservation` is **self-declared for a quota**, not observed caste.

Geography is `pin` (99.8% filled, 1,176 values), not `district` (12.9% filled,
and dirty: values like "BELAGAVI BELAGAVI").
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

# Karnataka's backward-class categories. 2B is defined by religion, so it is
# folded into one OBC bucket rather than reported on its own, which is the norm
# this repo already keeps.
OBC_CODES = {"2A", "2B", "3A", "3B", "C1", "CAT1"}
CATEGORY = {"GM": "General", "SC": "Scheduled Caste", "ST": "Scheduled Tribe"}


def _github() -> Path:
    return Path(os.environ.get("GITHUB_DIR", Path.home() / "Documents/GitHub"))


def source_path() -> Path:
    return (
        _github()
        / "pranaam/scripts/data-acquisition/karnataka_psc/raw"
        / "karnataka_candidates.parquet"
    )


def load() -> pd.DataFrame | None:
    """Candidates with a collapsed category, a naive surname and a cleaned one."""
    path = source_path()
    if not path.exists():
        return None
    d = pd.read_parquet(path)

    base = d["reservation"].astype(str).str.split("/").str[0].str.strip().str.upper()
    d["category"] = base.map(lambda c: CATEGORY.get(c, "OBC" if c in OBC_CODES else ""))
    d = d[d["category"] != ""].copy()

    tokens = d["name"].astype(str).str.strip().str.upper().str.split()
    d["tokens"] = tokens
    d["naive_surname"] = tokens.str[-1]
    # The cleaned rule: the last token longer than one character. Nothing more
    # clever, because the point is to size the damage the naive rule does, not
    # to build a resolver -- upnaam owns that.
    d["clean_surname"] = tokens.map(
        lambda t: next((w for w in reversed(t) if len(w) > 1), None)
    )
    d["pin"] = d["pin"].astype(str).str.strip()
    return d.reset_index(drop=True)


def initial_share(d: pd.DataFrame) -> dict:
    """How much of the naive column is an initial rather than a name."""
    is_initial = d["naive_surname"].str.len() <= 1
    return {
        "rows": int(len(d)),
        "naive_is_single_letter": float(100 * is_initial.mean()),
        "distinct_naive": int(d["naive_surname"].nunique()),
        "distinct_clean": int(d["clean_surname"].dropna().nunique()),
        "no_clean_surname": float(100 * d["clean_surname"].isna().mean()),
    }


def score(d: pd.DataFrame, key: str, min_cell: int = 1) -> dict:
    """Leave-one-out error guessing category from `key`.

    Leave-one-out is not optional here. Most surnames appear once or twice, so
    scoring a person against a table their own row built would report a number
    about memorization.

    `min_cell` is how many *other* candidates must share a cue before it is used
    instead of the blind guess. One, matching analysis 09, so the two are
    comparable. At two the headline reads 43.9 instead of 40.0, which is why the
    rule is stated rather than left to a default.
    """
    frame = d[d[key].notna()].copy()
    cats = sorted(frame["category"].unique())
    idx = {c: i for i, c in enumerate(cats)}
    truth = frame["category"].map(idx).to_numpy()

    counts = (
        pd.crosstab(frame[key], frame["category"])
        .reindex(columns=cats, fill_value=0)
        .astype(float)
    )
    cell = counts.loc[frame[key]].to_numpy()
    own = np.zeros_like(cell)
    own[np.arange(len(frame)), truth] = 1
    left = cell - own

    prior = counts.to_numpy().sum(axis=0)
    blind = int(prior.argmax())
    resolved = left.sum(axis=1) >= min_cell
    guess = np.where(resolved, left.argmax(axis=1), blind)

    return {
        "cue": key,
        "people": int(len(frame)),
        "distinct": int(counts.shape[0]),
        "blind_per_100": float(100 * (1 - prior.max() / prior.sum())),
        "mistakes_per_100": float(100 * (guess != truth).mean()),
        "share_resolved": float(100 * resolved.mean()),
    }


def by_category(d: pd.DataFrame, key: str = "clean_surname") -> pd.DataFrame:
    """The same guess, split by the candidate's own category.

    Analysis 05's decomposition, applied to a different source and a different
    set of categories. The blind guess names the largest category, so it is
    right about all of that one and wrong about every other.
    """
    frame = d[d[key].notna()].copy()
    cats = sorted(frame["category"].unique())
    index = {c: i for i, c in enumerate(cats)}
    truth = frame["category"].map(index).to_numpy()

    counts = (
        pd.crosstab(frame[key], frame["category"])
        .reindex(columns=cats, fill_value=0)
        .astype(float)
    )
    cell = counts.loc[frame[key]].to_numpy()
    own = np.zeros_like(cell)
    own[np.arange(len(frame)), truth] = 1
    left = cell - own

    prior = counts.to_numpy().sum(axis=0)
    blind = int(prior.argmax())
    guess = np.where(left.sum(axis=1) >= 1, left.argmax(axis=1), blind)

    rows = []
    for category, i in index.items():
        mine = truth == i
        rows.append(
            {
                "category": category,
                "share_of_candidates": float(mine.mean()),
                "blind_wrong_per_100": 0.0 if i == blind else 100.0,
                "wrong_per_100": float(100 * (guess[mine] != truth[mine]).mean()),
                "candidates": int(mine.sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("wrong_per_100")
