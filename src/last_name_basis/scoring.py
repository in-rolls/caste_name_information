"""Shared scoring. One measure, used by every analysis: mistakes per hundred.

Guess the commonest category in whatever group you can place someone in, and
count how often you are wrong. It needs no gloss, it is bounded, and it ranks
names by how *certain* they leave you rather than by how much they surprise you
-- which is why it puts Jha (leaves you 99.7% sure) above Paswan (89%).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def entropy_bits(prior) -> float:
    prior = np.asarray(prior, dtype=float)
    prior = prior[prior > 0]
    return float(-(prior * np.log2(prior)).sum())


def weighted_summary(
    frame: pd.DataFrame, prob_cols: list[str], weight: str, categories: list[str]
) -> dict:
    """Summarize a per-group table under a people-weighting, prior and all.

    The prior is recomputed from these weights. Averaging against a prior from
    some other weighting silently breaks the identity that makes the average
    interpretable -- it is how one draft reported 0.32 and 0.44 for a single
    quantity, and nine squares against sixteen percent.
    """
    w = frame[weight].fillna(0).to_numpy(float)
    w = w / w.sum()
    p = frame[prob_cols].to_numpy()
    prior = (p * w[:, None]).sum(axis=0)

    h_prior = entropy_bits(prior)
    with np.errstate(divide="ignore", invalid="ignore"):
        conditional = -np.where(p > 0, p * np.log2(p), 0.0).sum(axis=1)
    cut = h_prior - conditional
    blind = int(prior.argmax())

    return {
        "base_rates": {c: float(prior[i]) for i, c in enumerate(categories)},
        "caste_entropy_bits": h_prior,
        "err_blind": float(1.0 - prior.max()),
        "err_per_person": float((w * (1.0 - p.max(axis=1))).sum()),
        "uncertainty_removed_bits": float((w * cut).sum()),
        "share_guess_unchanged": float(w[p.argmax(axis=1) == blind].sum()),
        # NOT an error rate, and it does not mean the name makes you wronger:
        # max(p) >= p[blind] always, so no name can beat the blind guess
        # downward. This is the share of people whose surname has a MORE evenly
        # spread caste mix than the population does, which reads as "be less
        # certain", not "you get more wrong".
        "share_whose_name_is_more_mixed_than_the_population": float(w[cut < 0].sum()),
    }


def score_ladder(
    long: pd.DataFrame,
    *,
    level: str = "level",
    cell: str = "cell",
    group: str = "jati",
    weight: str = "accounts",
) -> pd.DataFrame:
    """Mistakes per hundred at each rung of a geographic ladder.

    ``long`` is one row per (level, cell, group) with a count. For every cell we
    guess its commonest group; the score is the count-weighted share of people
    that guess gets wrong. Cells are weighted by how many people are in them, so
    the number answers "pick a person", not "pick a cell".
    """
    counts = long.groupby([level, cell, group], observed=True)[weight].sum()
    counts = counts.reset_index()
    per_cell = counts.groupby([level, cell], observed=True)[weight]

    size = per_cell.sum().rename("people")
    biggest = per_cell.max().rename("modal")
    groups = (
        counts.groupby([level, cell], observed=True)[group].nunique().rename("groups")
    )
    cells = pd.concat([size, biggest, groups], axis=1).reset_index()

    rows = []
    for name, g in cells.groupby(level, observed=True):
        w = g["people"] / g["people"].sum()
        rows.append(
            {
                level: name,
                "cells": len(g),
                "people": int(g["people"].sum()),
                "mistakes_per_100": float(
                    (w * (1 - g["modal"] / g["people"])).sum() * 100
                ),
                "median_groups_in_cell": float(g["groups"].median()),
                "smallest_cell": int(g["people"].min()),
            }
        )
    return pd.DataFrame(rows).sort_values("mistakes_per_100").reset_index(drop=True)


def leave_one_out_ladder(
    long: pd.DataFrame,
    *,
    level: str = "level",
    cell: str = "cell",
    group: str = "jati",
    weight: str = "accounts",
) -> pd.DataFrame:
    """The same score, but each person is guessed from a cell that excludes them.

    Without this, a cell holding one person is "predicted" perfectly by
    construction, and a ladder of small cells looks far sharper than it is.
    """
    counts = (
        long.groupby([level, cell, group], observed=True)[weight].sum().reset_index()
    )

    def cell_error(n: np.ndarray) -> float:
        total = n.sum()
        if total < 2:
            return np.nan
        wrong = 0
        for k in range(len(n)):
            held = n.copy()
            held[k] -= 1
            wrong += n[k] * (int(np.argmax(held)) != k)
        return wrong / total

    rows = []
    for name, g in counts.groupby(level, observed=True):
        per_cell = g.groupby(cell, observed=True)[weight]
        err = per_cell.apply(lambda s: cell_error(s.to_numpy()))
        size = per_cell.sum()
        keep = err.notna()
        w = size[keep] / size[keep].sum()
        rows.append(
            {
                level: name,
                "mistakes_per_100_loo": float((w * err[keep]).sum() * 100),
            }
        )
    return pd.DataFrame(rows)


def ranks_above(score: np.ndarray, positive: np.ndarray, negative: np.ndarray) -> float:
    """How often a positive outranks a negative, ties counted as half.

    Take one person from the positive group and one from the negative group at
    random, and rank the pair by `score`. This returns the share of such pairs
    in which the positive ranks higher. A score carrying no information gives
    exactly 0.5.

    It is the Mann-Whitney statistic, equivalently the area under the ROC curve,
    and the reason this repo needs it is that accuracy does not answer the
    question. A rule that names the largest category is right 70 times in 100 in
    a population that is 70% one group, whatever surnames reveal. This statistic
    cannot be inflated by the base rate.

    `positive` and `negative` are counts of people at each score, not indicators,
    so a per-name table can be passed directly.
    """
    order = np.argsort(score, kind="mergesort")
    s, pos, neg = score[order], positive[order], negative[order]

    below = np.zeros(len(s))
    tied = np.zeros(len(s))
    running = 0.0
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        group = neg[i : j + 1].sum()
        below[i : j + 1] = running
        tied[i : j + 1] = group
        running += group
        i = j + 1

    pairs = pos.sum() * neg.sum()
    if pairs <= 0:
        return float("nan")
    return float((pos * (below + 0.5 * tied)).sum() / pairs)
