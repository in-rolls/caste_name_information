"""How much of a real city's population the surname table can speak to at all.

Uses instate's 2017 electoral-roll surname counts.  instate is not a hard
dependency: if its table is not on disk this returns None and the build says so
rather than failing.
"""

from __future__ import annotations

import csv
import gzip
from pathlib import Path

import pandas as pd

from last_name_basis.siblings import repo


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


def city_surname_counts(city: str = "Delhi") -> pd.DataFrame | None:
    path = instate_table()
    if path is None:
        return None
    d = pd.read_parquet(path, columns=["last_name", city, "total_n"])
    d["n_city"] = d["total_n"] * d[city]
    return d.loc[d["n_city"] >= 1, ["last_name", "n_city"]].reset_index(drop=True)


def roll_token_census(state: str = "delhi") -> dict | None:
    """Share of electors whose roll entry is a single token -- no surname at all.

    Read from the raw per-state roll rather than the derived table, so it is an
    independent count.
    """
    path = repo("instate") / f"data/names_{state}.csv.gz"
    if not path.exists():
        return None
    by_tokens: dict[int, int] = {}
    with gzip.open(path, "rt") as fh:
        for row in csv.DictReader(fh):
            k = len(row["english_name"].split())
            by_tokens[k] = by_tokens.get(k, 0) + int(row["n_times"])
    total = sum(by_tokens.values())
    return {
        "electors": total,
        "single_token": by_tokens.get(1, 0),
        "single_token_share": by_tokens.get(1, 0) / total,
    }


def coverage(named: pd.DataFrame, city: str = "Delhi") -> dict | None:
    counts = city_surname_counts(city)
    if counts is None:
        return None
    known = set(named["last_name"])
    counts["in_table"] = counts["last_name"].isin(known)
    total = counts["n_city"].sum()
    matched = counts.loc[counts["in_table"], "n_city"].sum()
    out = {
        "city": city,
        "surname_tokens": float(total),
        "distinct_surnames": int(len(counts)),
        "matched_tokens": float(matched),
        "matched_share": float(matched / total),
        "matched_surnames": int(counts["in_table"].sum()),
    }
    census = roll_token_census(city.lower())
    if census:
        out.update(
            {
                "electors": census["electors"],
                "single_token_share": census["single_token_share"],
            }
        )
        # A single-token roll entry has no surname, so the table cannot speak to
        # that person at all. Fold it into an all-in denominator.
        surnamed = 1.0 - census["single_token_share"]
        out["matched_share_of_all_electors"] = float(out["matched_share"] * surnamed)
    return out


def national_frequency() -> pd.DataFrame | None:
    """How common each surname is among actual adults.

    SECC counts heads of household, who are mostly men, so it badly undercounts
    women's surnames -- Devi is 2.3M there and Kumari 52k.  The 2017 electoral
    rolls count adults of both sexes, where Devi is the commonest surname in the
    country.  So "how common is this name" comes from here; "what does it mean"
    stays with SECC.
    """
    path = instate_table()
    if path is None:
        return None
    d = pd.read_parquet(path, columns=["last_name", "total_n"])
    d = d[d["total_n"] > 0].copy()
    d["roll_share"] = d["total_n"] / d["total_n"].sum()
    return d.rename(columns={"total_n": "n_roll"}).sort_values(
        "n_roll", ascending=False
    )


def national_coverage(named: pd.DataFrame) -> dict | None:
    """What share of the names people actually carry the table can speak to.

    The front page says a hundred people drawn at roll frequency are 19 Dalit,
    6 Adivasi, 75 neither. `with_roll_frequency` renormalises its weights over
    matched names, so that room is built only from surnames the table covers.
    This is how large that restriction is, and it belongs beside the claim.
    """
    freq = national_frequency()
    if freq is None:
        return None
    matched = named.merge(freq, on="last_name", how="inner")
    total = float(freq["n_roll"].sum())
    covered = float(matched["n_roll"].sum())
    return {
        "names_in_table": int(len(named)),
        "names_on_the_roll": int(len(freq)),
        "names_matched": int(len(matched)),
        "roll_tokens_total": total,
        "roll_tokens_covered": covered,
        "share_of_roll_covered": covered / total,
    }


def with_roll_frequency(named: pd.DataFrame) -> pd.DataFrame:
    """Attach roll counts to the per-name table, and a roll-weighted share.

    ``roll_share`` is the share of *all* roll surnames; ``share_roll`` renormalises
    to the names SECC can speak to, so it is the weight to use when asking about a
    randomly drawn person whose name is in the table.
    """
    freq = national_frequency()
    if freq is None:
        return named.assign(n_roll=pd.NA, roll_share=pd.NA, share_roll=pd.NA)
    out = named.merge(freq, on="last_name", how="left")
    matched = out["n_roll"].fillna(0)
    out["share_roll"] = matched / matched.sum()
    return out
