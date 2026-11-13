"""Analysis 07: where a surname works, and analysis 08's Karnataka null."""

from __future__ import annotations

import json
import pathlib

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
A07 = ROOT / "analyses/07_where_the_name_works/out/tab"
A08 = ROOT / "analyses/08_karnataka_psc/out/tab"


@pytest.fixture(scope="module")
def states():
    path = A07 / "by_state.csv"
    if not path.exists():
        pytest.skip("analysis 07 not built")
    return pd.read_csv(path).set_index("state")


def test_no_state_reports_a_result_without_its_coverage(states):
    """Every per-state number describes surnames past a disclosure floor.

    Reporting the result without the coverage beside it is how "Haryana has no
    Dalit surnames" gets read as a fact about Haryana rather than about the 36
    surnames that cleared the floor, covering 4% of the state.
    """
    assert states["covered_share"].notna().all()
    assert (states["covered_share"] > 0).all()
    # And the coverage really does vary enough to matter.
    assert states["covered_share"].max() / states["covered_share"].min() > 3


def test_the_spread_across_states_is_the_finding(states):
    assert states.loc["assam", "removed"] > 60
    assert states.loc["haryana", "removed"] < 1
    assert states["removed"].max() - states["removed"].min() > 50


def test_the_top25_control_preserves_the_ordering(states):
    """The objection a reader raises first.

    The floor keeps a state's commonest names and common names are the
    uninformative ones, so a state retaining few names could look uninformative
    by construction. If the ordering only held before this control, the result
    would be an artifact of the floor rather than a fact about the states.
    """
    for good in ("assam", "bihar"):
        for bad in ("punjab", "haryana", "kerala"):
            assert states.loc[good, "removed_top25"] > states.loc[bad, "removed_top25"]


def test_the_count_of_dalit_pointing_names_is_not_the_story(states):
    """Punjab has more of them than Assam and gets a twentieth of the benefit.

    Guarded because the first draft of this analysis reported that count as the
    explanatory variable, which is wrong: what matters is whether a decisive
    name is large.
    """
    path = A07 / "decisive_names.csv"
    if not path.exists():
        pytest.skip("analysis 07 not built")
    d = pd.read_csv(path)
    punjab = d[d.state == "punjab"]
    assam = d[d.state == "assam"]
    assert len(punjab) >= len(assam)
    assert states.loc["punjab", "removed"] < states.loc["assam", "removed"] / 10
    # Assam's single decisive name is far larger than any of Punjab's.
    assert assam["share_of_extract"].max() > 2 * punjab["share_of_extract"].max()


def test_karnataka_last_tokens_are_mostly_initials():
    path = A08 / "summary.json"
    if not path.exists():
        pytest.skip("analysis 08 not built")
    s = json.loads(path.read_text())
    assert s["naive_is_single_letter"] > 25
    tokens = pd.read_csv(A08 / "commonest_tokens.csv")
    # Every one of the top ten naive tokens should be a single letter.
    assert (tokens["naive"].head(10).str.len() == 1).all()
    assert (tokens["clean"].head(10).str.len() > 1).all()


def test_the_karnataka_error_is_far_larger_for_scheduled_candidates():
    """Analysis 05's finding, on a different state, source and label set.

    This is why the analysis is in the repo. Karnataka is absent from SECC, so
    these lists are the only caste-linked name data for the state, and what they
    show is the differential the rest of the repo finds nationally.
    """
    path = A08 / "by_category.csv"
    if not path.exists():
        pytest.skip("analysis 08 not built")
    d = pd.read_csv(path).set_index("category")
    assert d.loc["General", "wrong_per_100"] < 25
    assert d.loc["Scheduled Caste", "wrong_per_100"] > 55
    assert (
        d.loc["Scheduled Caste", "wrong_per_100"]
        > 2 * d.loc["General", "wrong_per_100"]
    )
    # The blind guess names the largest category, so its own blind rate is 0.
    assert d.loc["General", "blind_wrong_per_100"] == 0
    assert (d.drop(index="General")["blind_wrong_per_100"] == 100).all()


def test_the_karnataka_split_reconstructs_the_overall_error():
    """One estimator split by whom it lands on, the identity analysis 05 uses."""
    path = A08 / "by_category.csv"
    if not path.exists():
        pytest.skip("analysis 08 not built")
    d = pd.read_csv(path)
    implied = (d["share_of_candidates"] * d["wrong_per_100"]).sum()
    overall = pd.read_csv(A08 / "scores.csv").set_index("cue")
    assert abs(implied - overall.loc["clean_surname", "mistakes_per_100"]) < 0.5


def test_cleaning_karnataka_surnames_helps_a_little():
    """Reported as a null on 14,854 candidates; the sign flipped at 48,395.

    The earlier reading was underpowered, not wrong about surnames, and this
    test now pins the direction so a future sample cannot flip it back
    unremarked. The effect is small either way: neither cue is strong.
    """
    path = A08 / "summary.json"
    if not path.exists():
        pytest.skip("analysis 08 not built")
    s = json.loads(path.read_text())
    # Negative means the cleaned surname makes fewer mistakes.
    assert s["cleaning_changes_prediction_by"] < 0
    assert abs(s["cleaning_changes_prediction_by"]) < 5
    sc = pd.read_csv(A08 / "scores.csv").set_index("cue")
    assert (
        sc.loc["clean_surname", "share_resolved"]
        < sc.loc["naive_surname", "share_resolved"]
    )
    # The cleaned column still resolves fewer people, which is what shows the
    # naive rule was pooling on initials rather than predicting from surnames.
    # And the surname helps without resolving: it closes some of the gap to the
    # blind rate and nothing close to all of it. Stated as a share of the gap
    # rather than a bound on the level, because the level moves with the
    # resolve rule and the share is what analysis 07 compares across states.
    blind = sc.loc["naive_surname", "blind_per_100"]
    for cue in ("naive_surname", "clean_surname"):
        closed = 100 * (blind - sc.loc[cue, "mistakes_per_100"]) / blind
        assert 5 < closed < 50, f"{cue} closes {closed:.0f}% of the gap"


@pytest.fixture(scope="module")
def summary():
    path = A07 / "summary.json"
    if not path.exists():
        pytest.skip("analysis 07 not built")
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def rolls(summary):
    if "roll_concentration" not in summary or not summary["roll_concentration"]:
        pytest.skip("upnaam rolls not present")
    return summary["roll_concentration"]


def test_two_names_cover_most_of_punjab(rolls):
    """The mechanism for the weakest surnames in the country.

    Analysis 07 reports that Punjab ranks 0.55 against a floor of 0.50 and does
    not say why. Singh and Kaur together are most of the state, and neither is a
    family name: Kaur is carried by Sikh women and Singh by Sikh men, across
    castes. A state where two names that were never lineage markers cover two
    thirds of the population cannot have informative surnames.
    """
    punjab = rolls["punjab"]
    top = {c["surname"]: c["share"] for c in punjab["commonest"]}
    assert {"singh", "kaur"} <= set(top)
    assert top["singh"] + top["kaur"] > 0.60, top
    assert punjab["names_for_half"] <= 2


def test_the_two_sources_agree_where_the_resolver_covers_the_state(summary):
    """The only cross-source check here, and it behaves.

    Every concentration figure in analysis 03 comes from instate. These come
    from upnaam, a different collection through a different pipeline. Where the
    resolver covers nearly all of a state the two agree closely; where it
    covers a third they diverge twentyfold, which is the check doing its job
    rather than failing.
    """
    compared = summary.get("instate_comparison", {})
    if not compared:
        pytest.skip("analysis 03 not built")
    for state in ("bihar", "punjab"):
        if state not in compared:
            continue
        c = compared[state]
        assert abs(c["names_for_half_instate"] - c["names_for_half_roll"]) <= 2, c
        assert abs(c["top10_share_instate"] - c["top10_share_roll"]) < 0.06, c


def test_rajasthan_is_where_the_sources_part_company(summary):
    """Flagged rather than quietly reported, because one of them is wrong.

    The resolver abstains on two thirds of Rajasthan, so the roll's surname
    distribution is computed on a selected third and is not a description of the
    state. If this ever starts agreeing, the resolver's Rajasthan coverage has
    changed and the note needs rereading.
    """
    compared = summary.get("instate_comparison", {})
    if "rajasthan" not in compared:
        pytest.skip("rajasthan not compared")
    c = compared["rajasthan"]
    assert c["names_for_half_instate"] > 10 * c["names_for_half_roll"], c


def test_concentration_alone_does_not_explain_the_weak_states(summary):
    """The claim the write-up had to be corrected into.

    An earlier version said Punjab's surnames carry nothing because two names
    cover the state. Bihar's dominant names touch a comparable share of its
    pairs and Bihar ranks 0.96, so concentration on its own is not the cause.
    """
    splits = summary.get("dominant_names", {})
    if not {"punjab", "bihar"} <= set(splits):
        pytest.skip("analysis 07 not built")
    punjab, bihar = splits["punjab"], splits["bihar"]
    assert bihar["pairs_touching_a_dominant_name"] > 0.7
    assert bihar["ranks_all_names"] > 0.9
    assert punjab["ranks_all_names"] < 0.6


def test_dominant_names_help_in_some_states_and_hurt_in_others(summary):
    """The sign of the change is the finding, not its size.

    Removing Kerala's `nair` and `pillai` makes the guess worse because they
    are 0.00 Dalit against a state of 0.08. Removing Punjab's `singh` makes it
    better. If every state moved the same way, the explanation would be about
    concentration and not about what the names are.
    """
    splits = summary.get("dominant_names", {})
    if not splits:
        pytest.skip("analysis 07 not built")
    deltas = {k: v["delta"] for k, v in splits.items()}
    assert any(d > 0.05 for d in deltas.values()), deltas
    assert any(d < 0 for d in deltas.values()), deltas
    assert deltas.get("punjab", 0) > 0 > deltas.get("kerala", 0)


def test_a_name_that_covers_a_state_carries_that_state(summary):
    """The mechanism, stated in one surname and needing no index.

    Singh is 9% of Bihar and never Dalit there; it is 73% of Punjab and exactly
    as Dalit as Punjab is. If this ever inverts, the account in the note is
    wrong and the prose has to change with it.
    """
    rows = {r["state"]: r for r in summary.get("singh_across_states", [])}
    if not {"bihar", "punjab"} <= set(rows):
        pytest.skip("analysis 07 not built")
    bihar, punjab = rows["bihar"], rows["punjab"]
    assert punjab["share_of_state"] > 3 * bihar["share_of_state"]
    assert abs(punjab["distance_from_base"]) < 0.05
    assert abs(bihar["distance_from_base"]) > 0.15
    # Moderate and reported as such: Uttarakhand does not fit.
    assert -0.9 < summary["singh_share_vs_distance"] < -0.2
