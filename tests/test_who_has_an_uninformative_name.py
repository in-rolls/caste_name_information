"""The differential-error result, and the null beside it."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from conftest import load

source = load("05_who_has_an_uninformative_name", "data")

TAB = Path(__file__).resolve().parent.parent / (
    "analyses/05_who_has_an_uninformative_name/out/tab"
)


@pytest.fixture(scope="module")
def caste():
    path = TAB / "by_caste.csv"
    if not path.exists():
        pytest.skip("analysis 05 not built")
    return pd.read_csv(path).set_index("caste")


def test_the_guess_is_far_worse_about_dalits(caste):
    """66 wrong per 100 against 4. The headline of this analysis.

    This replaces a test asserting the name does *nothing* for Dalits, which
    compared a group-specific vagueness score against a population-wide blind
    rate. Scored consistently the name helps Dalits more than anyone; it just
    starts them so far back that helping most still leaves them worst off.
    """
    assert caste.loc["Scheduled Caste", "wrong_per_100"] > 60
    assert caste.loc["neither", "wrong_per_100"] < 10
    assert (
        caste.loc["Scheduled Caste", "wrong_per_100"]
        > 10 * caste.loc["neither", "wrong_per_100"]
    )


def test_the_name_helps_the_scheduled_groups_and_not_the_majority(caste):
    """The part that reverses the old claim, so it gets its own test."""
    for group in ("Scheduled Caste", "Scheduled Tribe"):
        row = caste.loc[group]
        assert row["blind_wrong_per_100"] == 100
        assert row["wrong_per_100"] < row["blind_wrong_per_100"] - 25
    other = caste.loc["neither"]
    assert other["blind_wrong_per_100"] == 0
    assert other["wrong_per_100"] > 0


def test_recall_is_wildly_unequal(caste):
    assert caste.loc["Scheduled Caste", "found_by_the_guess"] < 0.45
    assert caste.loc["neither", "found_by_the_guess"] > 0.9


def test_the_sex_gap_does_not_run_one_way():
    """Reported as a null: women fare worse in Bihar and better in UP. An
    earlier draft's figure asserted the opposite before the numbers came in."""
    path = TAB / "sex_gap.csv"
    if not path.exists():
        pytest.skip("sex table not built")
    g = pd.read_csv(path)
    assert (g["gap"] > 0).any() and (g["gap"] < 0).any()
    maharashtra = g.loc[g["state"] == "maharashtra", "gap"]
    if not maharashtra.empty:
        assert abs(maharashtra.iloc[0]) < 0.5


def test_sex_weights_use_upnaam_surname_order(tmp_path, monkeypatch):
    artifact = tmp_path / "in-rolls/upnaam/data/derived/resolved/maharashtra.parquet"
    artifact.parent.mkdir(parents=True)
    pd.DataFrame(
        {
            "source_row": [0, 1, 2],
            "state": ["maharashtra"] * 3,
            "name_raw": ["patil ashwini", "jadhav suresh", "sattar"],
            "weight": [10, 5, 20],
            "surname": ["patil", "jadhav", None],
            "surname_position": ["first", "first", None],
            "abstained": [False, False, True],
            "resolver_revision": ["resolver-v1"] * 3,
        }
    ).to_parquet(artifact, index=False)
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path))
    result = source.surname_by_sex(
        "maharashtra", {"ashwini": 0.8, "suresh": 0.1, "patil": 0.0}
    ).set_index("last_name")
    assert result.loc["patil", "female"] == pytest.approx(8)
    assert result.loc["patil", "male"] == pytest.approx(2)
    assert result.loc["jadhav", "female"] == pytest.approx(0.5)


def test_the_recall_split_reconstructs_the_headline_error():
    """`wrong_per_100` and the headline must be one estimator, not two.

    The README once said a Dalit is guessed wrong 29 times in 100. That was
    `name_vagueness_per_100` -- a property of the names a group carries,
    averaged over its bearers -- read as if it were the group's error rate. The
    two differ by a factor of two and tell opposite stories: on vagueness the
    name appears to do nothing for Dalits, while on error it helps them more
    than anyone (100 wrong to 66) and still leaves them worst off.

    If this ever stops summing, the table has drifted back into mixing them.
    """
    import json
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent
    a05 = root / "analyses/05_who_has_an_uninformative_name/out/tab/summary.json"
    a01 = root / "analyses/01_surname_to_category/out/tab/headline.json"
    if not a05.exists() or not a01.exists():
        pytest.skip("analyses not built")
    by_caste = json.loads(a05.read_text())["by_caste"]
    headline = json.loads(a01.read_text())["err_per_person"] * 100

    implied = sum(v["share_of_people"] * v["wrong_per_100"] for v in by_caste.values())
    assert abs(implied - headline) < 0.01, (
        f"recall split implies {implied:.3f} mistakes per 100, "
        f"headline says {headline:.3f}"
    )
    # And the two quantities must stay distinguishable, or the mistake is back.
    sc = by_caste["Scheduled Caste"]
    assert sc["wrong_per_100"] > 2 * sc["name_vagueness_per_100"]


def test_no_group_is_claimed_to_gain_most_without_checking(caste):
    """A published claim said the name helps Dalits most. It helps Adivasis more.

    Both scheduled groups start at 100 wrong, so the one that ends lower gains
    more, and that is Scheduled Tribe. Guarding it because the error survived a
    green suite, a figure, a note and two READMEs.
    """
    gain = caste["blind_wrong_per_100"] - caste["wrong_per_100"]
    assert gain["Scheduled Tribe"] > gain["Scheduled Caste"]
    # And the point that does hold: biggest gain, still worst outcome.
    assert caste.loc["Scheduled Caste", "wrong_per_100"] == caste["wrong_per_100"].max()


def test_adding_punjab_left_the_other_states_where_they_were():
    """Punjab was a pure addition to the sex split, not a recomputation.

    It is the most sex-marked naming system in the country, Kaur for women and
    Singh for men, and it was the one resolved state this analysis was not
    using. Adding it must not move Bihar, Rajasthan or Maharashtra.
    """
    import json
    import pathlib

    path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "analyses/05_who_has_an_uninformative_name/out/tab/summary.json"
    )
    if not path.exists():
        pytest.skip("analysis 05 not built")
    gaps = json.loads(path.read_text()).get("by_sex", {})
    if "punjab" not in gaps:
        pytest.skip("punjab artifact unavailable")
    assert gaps["bihar"]["gap"] == pytest.approx(3.33, abs=0.05)
    assert gaps["maharashtra"]["gap"] == pytest.approx(-0.20, abs=0.05)
    assert gaps["rajasthan"]["gap"] == pytest.approx(-1.37, abs=0.05)
    # And the null holds across four states rather than three: no direction.
    signs = {k: v["gap"] > 0 for k, v in gaps.items()}
    assert len(set(signs.values())) == 2, signs
