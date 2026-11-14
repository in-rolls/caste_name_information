"""Where a surname works, state by state.

Analyses 01 and 05 report one national number and its split by caste. Neither
says *where* the name works, and the range across states is far wider than the
national figure suggests.

Everything comes from the same source as analysis 01 -- outkast's SECC extract,
`state x birth_year x surname -> n_sc, n_st, n_other`, adults only, cells with
at least 100 records -- pooled to one row per (state, surname).

Two things about that extract govern how these numbers may be read, so they are
computed here rather than left to the note:

`covered_share`  what fraction of the state's Census 2011 population the
                 retained surnames account for. It runs from 3% to 19%, so
                 every per-state result describes surnames that cleared a
                 disclosure floor, not a state.

`removed_top25`  the same score with every state cut to its 25 commonest
                 names. The floor keeps common names, and this repo's own
                 finding is that common names are the uninformative ones, so a
                 state retaining few names could look uninformative by
                 construction. This holds that constant.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from last_name_basis.scoring import ranks_above  # noqa: E402

HERE = Path(__file__).resolve().parent
A01 = HERE.parent / "01_surname_to_category"
TOP_N = 25


def _secc():
    """Analysis 01's loader, imported without colliding with this data.py."""
    spec = importlib.util.spec_from_file_location("a01_data", A01 / "data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load() -> pd.DataFrame:
    """One row per (state, surname), birth-year cells pooled."""
    secc = _secc()
    cells = secc.load_cells()
    per = cells.groupby(["state", "last_name"], as_index=False)[secc.COUNT_COLS].sum()
    per.attrs["count_cols"] = secc.COUNT_COLS
    per.attrs["categories"] = secc.CATEGORIES
    return per


def census_population() -> pd.Series:
    return _secc().census_population()


def score(counts: np.ndarray) -> dict:
    """Blind and with-name error for one state, and the share of the gap closed.

    The guess is each surname's argmax category. Leave-one-out is deliberately
    absent: every cell here holds at least 100 records, so removing one person
    cannot flip an argmax, and a LOO column would be identical to this one.
    """
    total = counts.sum()
    if total <= 0:
        return {"blind": 0.0, "with_name": 0.0, "removed": 0.0}
    prior = counts.sum(axis=0)
    blind = 100 * (1 - prior.max() / total)
    with_name = 100 * (1 - counts.max(axis=1).sum() / total)
    return {
        "blind": float(blind),
        "with_name": float(with_name),
        "removed": float(100 * (blind - with_name) / blind) if blind > 0 else 0.0,
    }


def state_table(per: pd.DataFrame, min_names: int = TOP_N) -> pd.DataFrame:
    """Per-state scores, with the coverage and the top-25 control beside them."""
    cols = per.attrs["count_cols"]
    pop = census_population()
    rows = []
    for state, d in per.groupby("state"):
        n = d[cols].to_numpy(float)
        if len(d) < min_names:
            continue
        totals = n.sum(axis=1)
        top = d.assign(_t=totals).nlargest(min_names, "_t")[cols].to_numpy(float)
        row = {"state": state, "names": len(d), "people": float(n.sum())}
        row.update(score(n))
        row["removed_top25"] = score(top)["removed"]
        row["sc_share_of_extract"] = float(100 * n[:, 0].sum() / n.sum())
        # `removed` is accuracy against the largest category, so it moves with
        # the state's composition as much as with its surnames. Kerala closes
        # under 1% of the gap while separating Dalit from non-Dalit as well as
        # Maharashtra does, because only 8% of its extract is Scheduled Caste
        # and a surname that raises the odds still rarely crosses a half.
        totals = n.sum(axis=1)
        p_sc = np.divide(n[:, 0], totals, out=np.zeros(len(d)), where=totals > 0)
        row["ranks_dalit_higher"] = ranks_above(p_sc, n[:, 0], totals - n[:, 0])
        census = pop.get(state, np.nan)
        row["census_population"] = float(census)
        row["covered_share"] = float(100 * n.sum() / census) if census else np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values("removed", ascending=False)


def decisive_names(per: pd.DataFrame, state: str, k: int = 3) -> pd.DataFrame:
    """The surnames that actually carry a state's signal.

    Not a count of Dalit-pointing names -- that misleads. Punjab has five in its
    top 25 and closes 3% of the gap; Assam has two and closes 65%, because one
    of them is `das`. What matters is how many people a decisive name covers.
    """
    cols = per.attrs["count_cols"]
    d = per[per["state"] == state].copy()
    n = d[cols].to_numpy(float)
    d["people"] = n.sum(axis=1)
    d["p_sc"] = n[:, 0] / d["people"]
    d["points_sc"] = n.argmax(axis=1) == 0
    d["share_of_extract"] = 100 * d["people"] / d["people"].sum()
    out = d[d["points_sc"]].nlargest(k, "people")
    return out[["last_name", "people", "p_sc", "share_of_extract"]].reset_index(
        drop=True
    )


def roll_concentration(state: str) -> dict | None:
    """How concentrated a state's surnames are, from upnaam's resolved roll.

    Analysis 07 reports that Punjab's surnames rank 0.55, barely above the 0.50
    a surname carrying nothing would give, and does not say why. The roll
    answers it: two names cover most of the state, and neither is a family name.

    This is also the one cross-source check in the repo. Every concentration
    figure in analysis 03 comes from instate; this comes from a different
    collection through a different pipeline, and the two can be compared.
    """
    from last_name_basis.upnaam import iter_resolved_roll, resolved_roll_path

    path = resolved_roll_path(state)
    if not path.exists():
        return None

    weight: dict[str, float] = {}
    for frame in iter_resolved_roll(path, state=state):
        resolved = frame.loc[~frame["abstained"]]
        if resolved.empty:
            continue
        grouped = resolved.groupby("surname")["weight"].sum()
        for name, w in grouped.items():
            weight[str(name)] = weight.get(str(name), 0.0) + float(w)

    counts = pd.Series(weight).sort_values(ascending=False)
    total = counts.sum()
    if total <= 0:
        return None
    share = counts / total
    cumulative = share.cumsum()
    return {
        "state": state,
        "electors": float(total),
        "distinct_surnames": int(len(counts)),
        "top10_share": float(share.head(10).sum()),
        "names_for_half": int((cumulative < 0.5).sum() + 1),
        "commonest": [
            {"surname": str(n), "share": float(s)} for n, s in share.head(10).items()
        ],
    }


def dominant_names(frame: pd.DataFrame, cols: list[str], cover: float = 0.5) -> list:
    """The fewest commonest surnames that together cover `cover` of a state."""
    people = frame[cols].to_numpy(float).sum(axis=1)
    order = np.argsort(people)[::-1]
    share = np.cumsum(people[order]) / people.sum()
    keep = int((share < cover).sum() + 1)
    return list(frame["last_name"].to_numpy()[order][:keep])


def decompose(per: pd.DataFrame, state: str, cover: float = 0.5) -> dict | None:
    """Split the ranking statistic by whether a pair involves a dominant name.

    Concentration is not a nuisance to net out of these numbers. Devi, Singh and
    Kaur are the names people write on forms, and their spread is a process that
    removed caste information from names rather than noise hiding it.

    But concentration alone does not do the work, and this is what shows it.
    `delta`, the change from removing the dominant names, is positive where they
    are dead weight and negative where they carry the signal. Kerala's dominant
    names are `nair` and `pillai`, which are caste names, so removing them makes
    the guess worse. Punjab's is `singh`, a title carried across castes, so
    removing it makes the guess better. What matters is not how concentrated a
    state's naming is but whether the concentration sits in names that mark a
    lineage.

    A decomposition, not an identified mediation: nothing is randomised and no
    counterfactual is estimated. It describes where the pairs sit.
    """
    cols = per.attrs["count_cols"]
    g = per[per["state"] == state]
    if len(g) < 3:
        return None
    n = g[cols].to_numpy(float)
    total = n.sum(axis=1)
    p_sc, sc, other = n[:, 0] / total, n[:, 0], total - n[:, 0]

    top = dominant_names(g, cols, cover)
    is_top = g["last_name"].isin(top).to_numpy()

    # Share of (Dalit, non-Dalit) pairs in which at least one carries one.
    dalit_side = sc / sc.sum()
    other_side = other / other.sum()
    touching = 1 - (1 - dalit_side[is_top].sum()) * (1 - other_side[is_top].sum())

    rest = ~is_top
    without = (
        ranks_above(p_sc[rest], sc[rest], other[rest])
        if rest.sum() > 1
        else float("nan")
    )
    return {
        "state": state,
        "dominant": top,
        "dominant_share_of_records": float(total[is_top].sum() / total.sum()),
        "pairs_touching_a_dominant_name": float(touching),
        "ranks_all_names": float(ranks_above(p_sc, sc, other)),
        "ranks_without_dominant": float(without),
        "names_outside_the_dominant": int(rest.sum()),
        # Positive: the dominant names are dead weight. Negative: they carry
        # the signal. This is the diagnostic, not the touch share.
        "delta": float(without - ranks_above(p_sc, sc, other)),
    }


def one_name_across_states(per: pd.DataFrame, name: str = "singh") -> pd.DataFrame:
    """The same surname's caste composition against each state's own.

    The clearest statement of the mechanism, and it needs no index. As a name's
    coverage of a state rises, its composition converges on the state's, because
    a name carried by everyone describes everyone. Singh is 9% of Bihar and
    never Dalit there; it is 73% of Punjab and exactly as Dalit as Punjab is.
    """
    cols = per.attrs["count_cols"]
    rows = []
    for state, g in per.groupby("state"):
        n = g[cols].to_numpy(float)
        total = n.sum(axis=1)
        hit = g["last_name"] == name
        if not hit.any():
            continue
        mine = n[hit.to_numpy()][0]
        carried = mine.sum()
        if carried < 20000:
            continue
        rows.append(
            {
                "state": state,
                "records": float(carried),
                "share_of_state": float(carried / total.sum()),
                "p_sc": float(mine[0] / carried),
                "state_base": float(n[:, 0].sum() / total.sum()),
            }
        )
    out = pd.DataFrame(rows)
    out["distance_from_base"] = out["p_sc"] - out["state_base"]
    return out.sort_values("share_of_state")
