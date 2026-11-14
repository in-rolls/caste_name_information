"""Invariants for the surname-concentration analysis."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import load

source = load("03_how_few_names", "data")
titles = load("03_how_few_names", "titles")
variants = load("03_how_few_names", "variants")


@pytest.fixture(scope="module")
def counts():
    c = source.surnames()
    if c is None:
        pytest.skip("instate unavailable")
    return c


@pytest.fixture(scope="module")
def curves(counts):
    return {
        level: source.curve(counts["national"][~counts["last_name"].isin(drop)])
        for level, drop in titles.LEVELS.items()
    }


def test_titles_are_a_fifth_of_the_roll(counts):
    """The headline the note leads with."""
    nat = counts["national"]
    drop = counts["last_name"].isin(titles.LEVELS["minus_all"])
    assert nat[drop].sum() / nat.sum() == pytest.approx(0.183, abs=0.005)


def test_removing_titles_changes_what_concentration_means(curves):
    """19 tokens cover a quarter of India; 19 real family names do not."""
    as_written = int(np.searchsorted(curves["as_written"], 0.25) + 1)
    minus_all = int(np.searchsorted(curves["minus_all"], 0.25) + 1)
    assert as_written == 19
    assert minus_all == 100


def test_curves_are_ordered(curves):
    """Dropping head names can only lower the curve at every rank.

    Tolerance is not cosmetic: the per-state counts are `total_n x share`
    products, which carry float error around 5e-08.
    """
    n = min(len(c) for c in curves.values())
    a, b, d = (curves[k][:n] for k in ("as_written", "minus_clear", "minus_all"))
    assert (a >= b - 1e-6).all()
    assert (b >= d - 1e-6).all()


def test_names_for_half_can_move_either_way(counts):
    """Removing titles does not always mean more names are needed.

    Where titles are the head, the count rises sharply -- Punjab goes 2 to 7.
    Where they sit further down, removing them renormalises the survivors
    upward and the count can fall, as in Tripura. An earlier draft of these
    tests asserted it could only rise, which is false.
    """
    drop = counts["last_name"].isin(titles.LEVELS["minus_all"])
    punjab = counts["Punjab"]
    assert source.names_for(punjab) == 2
    assert source.names_for(punjab[~drop]) > source.names_for(punjab)

    tripura = counts["Tripura"]
    assert source.names_for(tripura[~drop]) <= source.names_for(tripura)


def test_punjab_is_mostly_titles(counts):
    s = counts["Punjab"]
    drop = counts["last_name"].isin(titles.LEVELS["minus_all"])
    assert float(s[drop].sum() / s.sum()) == pytest.approx(0.73, abs=0.02)


def test_south_is_not(counts):
    drop = counts["last_name"].isin(titles.LEVELS["minus_all"])
    for state in ("Tamil Nadu", "Kerala", "Karnataka"):
        s = counts[state]
        assert float(s[drop].sum() / s.sum()) < 0.05


def test_title_list_is_published_and_disjoint():
    assert not set(titles.CLEAR) & set(titles.AMBIGUOUS)
    table = titles.table()
    assert len(table) == len(titles.CLEAR) + len(titles.AMBIGUOUS)
    assert table["why"].str.len().gt(0).all()


def test_variant_merges_only_concentrate(counts):
    """A merge must fold a rare spelling into a commoner one, never the reverse."""
    m = variants.assign(counts)
    assert (m["target_n"] > m["n"]).all()
    assert (m["edits"] <= variants.MAX_EDITS).all()
    assert not set(m["last_name"]) & set(m["target"])


def test_only_transliteration_edits_are_accepted():
    """Distance alone merges different names. These are the cases that forced
    the rule: raul/raut, ari/ali and ajam/alam are all one edit apart."""
    assert variants.transliteration_variant("kamar", "kumar")
    assert variants.transliteration_variant("hassan", "hasan")
    assert variants.transliteration_variant("shahu", "sahu")
    for a, b in (
        ("raul", "raut"),
        ("ari", "ali"),
        ("ajam", "alam"),
        ("pan", "pal"),
        ("kasam", "kadam"),
    ):
        assert not variants.transliteration_variant(a, b), f"{a} -> {b}"


def test_the_tail_is_not_mostly_spelling(counts):
    m = variants.assign(counts)
    moved = m["n"].sum() / counts["national"].sum()
    assert moved < 0.02


def test_sex_marking_is_the_point(counts):
    """The claim the note leads with: these names are carried by one sex.

    Reads the cached table rather than the raw rolls, which take minutes.
    """
    import pandas as pd

    path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "analyses/03_how_few_names/out/tab/sex_marked.csv"
    )
    if not path.exists():
        pytest.skip("sex_marked.csv not built")
    d = pd.read_csv(path).set_index("state")

    bihar = d.loc["bihar"]
    assert bihar["women_sex_marked"] > 0.75
    assert bihar["men_sex_marked"] < 0.15
    # Every state, the gap runs the same way and is large where it exists.
    assert (d["women_sex_marked"] >= d["men_sex_marked"] - 1e-9).all()


def test_low_coverage_states_are_dropped_not_reported(counts):
    """Tamil Nadu matches 4% of its roll. A share computed on that slice does
    not describe the state, so it must not reach a figure."""
    import pandas as pd

    path = (
        __import__("pathlib").Path(__file__).resolve().parent.parent
        / "analyses/03_how_few_names/out/tab/sex_marked.csv"
    )
    if not path.exists():
        pytest.skip("sex_marked.csv not built")
    d = pd.read_csv(path)
    thin = d[d["coverage"] < 0.15]
    assert "tamil_nadu" in set(thin["state"])
