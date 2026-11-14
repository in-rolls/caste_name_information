"""Does knowing who lives around you rescue an uninformative surname?

Analysis 02 shows surname plus village is far better than surname alone. That
comparison memorises the village: it learns the jati mix of every particular
village and looks yours up. It says nothing about a stranger in a village you
have never seen, which is the situation anyone actually inferring caste is in.

So hold out whole villages. On a held-out village the memorised table is
undefined, and the only thing available is the *composition* of the other
surnames there. If that generalises, the repo's negative result needs
qualifying.

The cue is deliberately simple and interpretable. For village V, take every
surname in it other than the person's own, look up the jati distribution that
surname has across *training* villages, and household-weight them into Q_V. One
parameter mixes it with the person's own surname evidence.

Nothing per-person or per-name is published: the output is aggregate error rates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED = 20260826
TEST_SHARE = 0.30
SMOOTH = 0.5  # Dirichlet prior on jati counts, so unseen combinations are finite


def village_surname_jati(
    ladder: pd.DataFrame, level: str, weight: str, village_parts: int
) -> pd.DataFrame:
    """Reshape a ladder's `cell` string into village / surname / jati counts."""
    d = ladder[ladder["level"] == level].copy()
    parts = d["cell"].str.split("|", expand=True)
    d["village"] = parts.iloc[:, :village_parts].agg("|".join, axis=1)
    d["surname"] = parts.iloc[:, village_parts]
    return d.groupby(["village", "surname", "jati"], as_index=False)[weight].sum()


def split_villages(villages: pd.Index, seed: int = SEED) -> tuple[set, set]:
    rng = np.random.default_rng(seed)
    v = np.array(sorted(villages))
    rng.shuffle(v)
    cut = int(len(v) * (1 - TEST_SHARE))
    return set(v[:cut]), set(v[cut:])


def _dist(counts: pd.DataFrame, keys: list[str], jatis: list[str], weight: str):
    """Rows of `keys` -> smoothed distribution over jatis."""
    wide = (
        counts.pivot_table(index=keys, columns="jati", values=weight, aggfunc="sum")
        .reindex(columns=jatis)
        .fillna(0.0)
    )
    arr = wide.to_numpy() + SMOOTH
    return wide.index, arr / arr.sum(axis=1, keepdims=True)


def cooccurrence(train: pd.DataFrame, jatis: list[str], weight: str) -> tuple:
    """P(neighbour surname | your jati), from training villages.

    This is the model the first attempt got wrong. Averaging P(jati|surname)
    over the neighbours produces a near-uniform smear -- entropy 3.83 out of a
    possible 4.93 across 139 jatis -- and a predictor built on it scores worse
    than knowing nothing. The generative question is the right one: which
    surnames do people of jati j actually live among?
    """
    village_totals = train.groupby(["village", "surname"])[weight].sum()
    by_village = village_totals.groupby("village").sum()

    # For each (village, jati) present, the surname mix of the OTHER households.
    jati_by_village = train.groupby(["village", "jati"])[weight].sum().reset_index()
    surnames = sorted(train["surname"].unique())
    s_pos = {s: i for i, s in enumerate(surnames)}
    j_pos = {j: i for i, j in enumerate(jatis)}

    table = np.zeros((len(jatis), len(surnames)))
    vs = village_totals.reset_index()
    vs["si"] = vs["surname"].map(s_pos)
    for village, block in vs.groupby("village", sort=False):
        total = float(by_village.loc[village])
        idx = block["si"].to_numpy(int)
        w = block[weight].to_numpy(float)
        present = jati_by_village[jati_by_village["village"] == village]
        for j, n_j in zip(present["jati"], present[weight]):
            row = table[j_pos[j]]
            np.add.at(row, idx, w * n_j)
            # Households do not count themselves as their own neighbours.
            row[idx] -= 0.0
        del total
    table += SMOOTH
    table /= table.sum(axis=1, keepdims=True)
    return np.log(table), s_pos


def fit_and_score(
    vsj: pd.DataFrame,
    weight: str,
    alphas=np.concatenate(
        [np.linspace(0, 3, 16), np.array([4.0, 6.0, 9.0, 14.0, 20.0])]
    ),
) -> dict:
    """Train on one set of villages, evaluate on villages never seen.

    score(j) = log P(j | surname) + alpha * sum_t f_t log P(t | j)

    where f_t is the share of the village's other households carrying surname t.
    alpha damps the neighbour term because neighbours are not independent draws;
    alpha = 0 recovers surname-only. It is fit on training villages.
    """
    jatis = sorted(vsj["jati"].unique())
    train_v, test_v = split_villages(vsj["village"].unique())
    train = vsj[vsj["village"].isin(train_v)]
    test = vsj[vsj["village"].isin(test_v)]

    prior = train.groupby("jati")[weight].sum().reindex(jatis).fillna(0).to_numpy()
    prior = (prior + SMOOTH) / (prior + SMOOTH).sum()
    s_index, p_surname = _dist(train, ["surname"], jatis, weight)
    surname_lookup = {s: i for i, s in enumerate(s_index)}
    log_cooc, s_pos = cooccurrence(train, jatis, weight)

    def neighbour_term(frame: pd.DataFrame):
        by_vs = frame.groupby(["village", "surname"])[weight].sum().reset_index()
        by_vs["si"] = by_vs["surname"].map(s_pos)
        totals = by_vs.groupby("village")[weight].transform("sum")
        out = np.zeros((len(by_vs), len(jatis)))
        known = by_vs["si"].notna().to_numpy()
        # Village-level sum of f_t * log P(t|j), then remove the focal surname.
        acc: dict[str, np.ndarray] = {}
        rows_by_v: dict[str, list[int]] = {}
        for i, (v, si, w, tot) in enumerate(
            zip(by_vs["village"], by_vs["si"], by_vs[weight], totals)
        ):
            rows_by_v.setdefault(v, []).append(i)
            if pd.notna(si):
                acc[v] = acc.get(v, 0.0) + (w / tot) * log_cooc[:, int(si)]
        for v, idxs in rows_by_v.items():
            base = acc.get(v, np.zeros(len(jatis)))
            for i in idxs:
                si = by_vs["si"].iloc[i]
                own = (
                    (by_vs[weight].iloc[i] / totals.iloc[i]) * log_cooc[:, int(si)]
                    if pd.notna(si)
                    else 0.0
                )
                out[i] = base - own
        del known
        return by_vs, out

    def evaluate(frame: pd.DataFrame, alpha: float, cache=None) -> float:
        by_vs, nb = cache if cache is not None else neighbour_term(frame)
        idx = by_vs["surname"].map(surname_lookup)
        own = np.tile(np.log(prior), (len(by_vs), 1))
        m = idx.notna().to_numpy()
        own[m] = np.log(p_surname[idx[m].to_numpy(int)])
        pred = np.array(jatis)[(own + alpha * nb).argmax(axis=1)]
        pred_map = dict(zip(by_vs.set_index(["village", "surname"]).index, pred))
        truth = (
            frame.groupby(["village", "surname", "jati"])[weight].sum().reset_index()
        )
        got = np.array(
            [pred_map.get((v, s)) for v, s in zip(truth["village"], truth["surname"])]
        )
        wrong = truth.loc[got != truth["jati"].to_numpy(), weight].sum()
        return float(100 * wrong / truth[weight].sum())

    train_cache = neighbour_term(train)
    best_alpha = min(alphas, key=lambda a: evaluate(train, a, train_cache))
    test_cache = neighbour_term(test)

    return {
        "jatis": len(jatis),
        "alpha": float(best_alpha),
        "train_villages": len(train_v),
        "test_villages": len(test_v),
        "test_households": float(test[weight].sum()),
        "blind": float(
            100
            * (
                1
                - test[test["jati"] == jatis[int(prior.argmax())]][weight].sum()
                / test[weight].sum()
            )
        ),
        "surname_only": evaluate(test, 0.0, test_cache),
        "neighbours_only": evaluate(test, 1e6, test_cache),
        "surname_plus_neighbours": evaluate(test, best_alpha, test_cache),
        "alpha_at_grid_edge": bool(best_alpha >= max(alphas) - 1e-9),
    }


def per_surname(
    vsj: pd.DataFrame, weight: str, alpha: float, top: int = 14
) -> pd.DataFrame:
    """Does the neighbour cue rescue the names that say nothing on their own?

    The average can move by four while the common uninformative names move by
    twenty, and it is those names the question was about.
    """
    jatis = sorted(vsj["jati"].unique())
    train_v, test_v = split_villages(vsj["village"].unique())
    train = vsj[vsj["village"].isin(train_v)]
    test = vsj[vsj["village"].isin(test_v)]

    prior = train.groupby("jati")[weight].sum().reindex(jatis).fillna(0).to_numpy()
    prior = (prior + SMOOTH) / (prior + SMOOTH).sum()
    s_index, p_surname = _dist(train, ["surname"], jatis, weight)
    lookup = {s: i for i, s in enumerate(s_index)}
    log_cooc, s_pos = cooccurrence(train, jatis, weight)

    by_vs = test.groupby(["village", "surname"])[weight].sum().reset_index()
    by_vs["si"] = by_vs["surname"].map(s_pos)
    totals = by_vs.groupby("village")[weight].transform("sum")

    acc: dict[str, np.ndarray] = {}
    for v, si, w, tot in zip(by_vs["village"], by_vs["si"], by_vs[weight], totals):
        if pd.notna(si):
            acc[v] = acc.get(v, 0.0) + (w / tot) * log_cooc[:, int(si)]
    nb = np.zeros((len(by_vs), len(jatis)))
    for i, (v, si, w, tot) in enumerate(
        zip(by_vs["village"], by_vs["si"], by_vs[weight], totals)
    ):
        own = (w / tot) * log_cooc[:, int(si)] if pd.notna(si) else 0.0
        nb[i] = acc.get(v, np.zeros(len(jatis))) - own

    idx = by_vs["surname"].map(lookup)
    own = np.tile(np.log(prior), (len(by_vs), 1))
    mask = idx.notna().to_numpy()
    own[mask] = np.log(p_surname[idx[mask].to_numpy(int)])

    truth = test.groupby(["village", "surname", "jati"])[weight].sum().reset_index()
    key = by_vs.set_index(["village", "surname"]).index
    for label, a in (("alone", 0.0), ("with_neighbours", alpha)):
        pred = np.array(jatis)[(own + a * nb).argmax(axis=1)]
        pm = dict(zip(key, pred))
        got = np.array(
            [pm.get((v, s)) for v, s in zip(truth["village"], truth["surname"])]
        )
        truth[label] = (got != truth["jati"].to_numpy()).astype(float)

    g = truth.groupby("surname").apply(
        lambda d: pd.Series(
            {
                "households": d[weight].sum(),
                "alone": 100 * (d["alone"] * d[weight]).sum() / d[weight].sum(),
                "with_neighbours": 100
                * (d["with_neighbours"] * d[weight]).sum()
                / d[weight].sum(),
            }
        ),
        include_groups=False,
    )
    g["saved"] = g["alone"] - g["with_neighbours"]
    return g.nlargest(top, "households").reset_index()
