"""Load the outkast SECC table and pool it into one row per surname.

The only input is the shipped, disclosure-limited artifact:
``state x birth_year x last_name -> n_sc, n_st, n_other``, cells with at least
100 reference records.  Everything downstream reads the frame this module
returns; probabilities live as columns on that frame so they cannot be sheared
away from ``last_name`` by a later sort.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pandas as pd

CATEGORIES = ["sc", "st", "other"]
COUNT_COLS = [f"n_{c}" for c in CATEGORIES]
PROB_COLS = [f"p_{c}" for c in CATEGORIES]

# SECC recorded age, so "adult in 2011" is a birth-year window.  The upper bound
# is 18-in-2011; the lower drops a thin, badly-recorded pre-1930 tail.
ADULT_BIRTH_YEARS = (1930, 1993)

_REL = "data/secc/secc_surname_composition.parquet"


def secc_path() -> Path:
    """The table shipped inside the installed outkast package."""
    return Path(str(files("outkast"))) / _REL


def load_cells(
    min_support: int = 100,
    birth_years: tuple[int, int] = ADULT_BIRTH_YEARS,
) -> pd.DataFrame:
    """State x birth-year x surname cells, filtered to adults and a support floor."""
    cells = pd.read_parquet(secc_path())
    cells["state"] = cells["state"].astype(str)
    lo, hi = birth_years
    cells = cells[cells["birth_year"].between(lo, hi)]
    return cells[cells["total_support"] >= min_support].reset_index(drop=True)


def state_weights(cells: pd.DataFrame, scheme: str) -> pd.Series:
    """Per-record multiplier for each state.

    ``secc``   - none.  Pooling then weights states by how many records SECC
                 holds for them, which is not their share of India.
    ``census`` - scale each state's records up to its Census 2011 population, so
                 the pool stands in for a city drawing from India in proportion.
    """
    states = cells["state"].unique()
    if scheme == "secc":
        return pd.Series(1.0, index=states)
    if scheme != "census":
        raise ValueError(f"unknown weighting scheme: {scheme!r}")

    pop = census_population()
    missing = set(states) - set(pop.index)
    if missing:
        raise KeyError(f"no Census population for {sorted(missing)}")
    records = cells.groupby("state")["total_support"].sum()
    w = pop.reindex(states) / records.reindex(states)
    return w / w.mean()


def census_population() -> pd.Series:
    """Census 2011 total population by state, keyed to outkast's state spelling."""
    path = Path(__file__).resolve().parent / "census_2011_state_population.csv"
    pop = pd.read_csv(path, comment="#")
    return pop.set_index("state")["population_2011"]


def per_name(cells: pd.DataFrame, scheme: str = "secc") -> pd.DataFrame:
    """One row per surname: weighted counts, shares, and the category split."""
    w = state_weights(cells, scheme)
    weighted = cells[COUNT_COLS].mul(cells["state"].map(w).to_numpy(), axis=0)
    tidy = pd.concat([cells[["last_name"]], weighted], axis=1)

    g = tidy.groupby("last_name", as_index=False)[COUNT_COLS].sum()
    g["n"] = g[COUNT_COLS].sum(axis=1)
    for cat in CATEGORIES:
        g[f"p_{cat}"] = g[f"n_{cat}"] / g["n"]
    g["share"] = g["n"] / g["n"].sum()
    return g.sort_values("n", ascending=False).reset_index(drop=True)


def base_rates(names: pd.DataFrame) -> pd.Series:
    """Unconditional P(caste) implied by the same pooled records."""
    return names[COUNT_COLS].sum() / names["n"].sum()
