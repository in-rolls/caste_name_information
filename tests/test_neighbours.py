"""Invariants for the held-out neighbors test."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from conftest import load

nb = load("06_neighbours", "neighbours")


def test_the_split_is_by_village_and_disjoint():
    """Leakage here would manufacture the finding."""
    villages = pd.Index([f"v{i}" for i in range(1000)])
    train, test = nb.split_villages(villages)
    assert not (train & test)
    assert len(train) + len(test) == 1000
    assert 0.25 < len(test) / 1000 < 0.35


def test_the_split_is_stable():
    a = nb.split_villages(pd.Index([f"v{i}" for i in range(500)]))
    b = nb.split_villages(pd.Index([f"v{i}" for i in range(500)]))
    assert a == b


@pytest.fixture(scope="module")
def held_out():
    path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "analyses/06_neighbours/out/tab/held_out.csv"
    )
    if not path.exists():
        pytest.skip("analysis 06 not built")
    return pd.read_csv(path).set_index("ladder")


def test_neighbours_help_but_do_not_rescue(held_out):
    for ladder in held_out.index:
        row = held_out.loc[ladder]
        assert row["surname_plus_neighbours"] < row["surname_only"]
        # Nowhere near closing the gap to knowing the village itself.
        assert row["surname_only"] - row["surname_plus_neighbours"] < 15


def test_neighbours_alone_are_useless(held_out):
    """The check that caught a broken first design. Averaging P(jati|surname)
    over neighbors scored worse than blind, and the combined model still
    'improved' the headline by 0.1 -- noise dressed as a result. Co-occurrence
    cannot identify you, only tilt you, so this must stay bad."""
    for ladder in held_out.index:
        row = held_out.loc[ladder]
        assert row["neighbours_only"] > row["surname_only"]


def test_alpha_did_not_stop_at_the_grid_edge(held_out):
    """The first grid topped out at 1.2 and the optimum was past it, which
    understated the gain by half."""
    assert not held_out["alpha_at_grid_edge"].any()


def test_uninformative_names_are_the_ones_rescued():
    """The question was about specific names, not the mean. The mean moves by
    four; the worst-off common names move by twenty."""
    path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "analyses/06_neighbours/out/tab/per_surname.csv"
    )
    if not path.exists():
        pytest.skip("analysis 06 not built")
    d = pd.read_csv(path)
    # Across both ladders, how much a name gains should rise with how badly it
    # does alone.
    r = np.corrcoef(d["alone"], d["saved"])[0, 1]
    assert r > 0.4, f"expected uninformative names to gain most, got r={r:.2f}"
    assert d["saved"].max() > 10


def test_the_ceiling_scores_every_household():
    """The trap this analysis fell into twice.

    At the finest cue only 36% of households share a cell with anyone, and those
    are the easy ones -- people with a same-named relative in the same hamlet.
    Scoring only them gives 1.2 mistakes per 100 and describes a third of the
    population. Falling back to a coarser cue instead of excusing the household
    gives 9.1, which describes everybody.
    """
    import json
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "analyses/06_neighbours/out/tab/summary.json"
    )
    if not path.exists():
        pytest.skip("analysis 06 not built")
    s = json.load(open(path))
    if "ceiling" not in s:
        pytest.skip("Mahadalit census unavailable")
    # The bracket's own row is scored on held-out villages, to match the rungs
    # above it. The everyone-scored version is kept beside it and is what this
    # test guards, because it is the one that can silently shrink to the easy
    # third.
    c = s["ceiling_all_households"]

    assert c["households"] > 2_000_000
    # The finest cue resolves a minority. If this ever reads high, the fallback
    # chain has been removed and the number is about the easy third again.
    assert c["coverage"][0]["resolves"] < 0.6
    # And almost nobody should be left to the global fallback.
    assert c["share_needing_the_global_fallback"] < 0.05
    # The honest ceiling is several times the misleading one.
    assert 5 < c["mistakes_per_100"] < 20


def test_the_ceiling_beats_the_name_but_does_not_reach_zero():
    import json
    import pathlib

    base = (
        pathlib.Path(__file__).resolve().parent.parent
        / "analyses/06_neighbours/out/tab"
    )
    if not (base / "summary.json").exists():
        pytest.skip("analysis 06 not built")
    s = json.load(open(base / "summary.json"))
    if "ceiling" not in s:
        pytest.skip("Mahadalit census unavailable")
    held = pd.read_csv(base / "held_out.csv").set_index("ladder")
    name_only = held.loc["Mahadalit census", "surname_only"]
    assert s["ceiling"]["mistakes_per_100"] < name_only


def test_every_bracket_row_uses_the_same_held_out_villages():
    """The bracket puts four numbers side by side, so they must answer one
    question. Splitting naampata's 27,687 villages and the raw files' 28,602
    independently put only 2,509 of ~8,300 test villages in common, and the rows
    silently described different people."""
    import json
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "analyses/06_neighbours/out/tab/summary.json"
    )
    if not path.exists():
        pytest.skip("analysis 06 not built")
    s = json.load(open(path))
    if "ceiling" not in s:
        pytest.skip("Mahadalit census unavailable")
    assert s["ceiling"].get("shares_split_with_neighbour_rungs") is True
    assert s["ceiling"]["scored_on"] == "held-out villages"
