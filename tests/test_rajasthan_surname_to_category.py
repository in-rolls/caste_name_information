"""Analysis 11: the OBC / General line, from self-declared panchayat candidates."""

from __future__ import annotations

import json
import pathlib

import pandas as pd
import pytest
from conftest import load

ROOT = pathlib.Path(__file__).resolve().parent.parent
A11 = ROOT / "analyses/11_rajasthan_surname_to_category"
TAB = A11 / "out/tab"


@pytest.fixture(scope="module")
def summary():
    path = TAB / "summary.json"
    if not path.exists():
        pytest.skip("analysis 11 not built")
    return json.loads(path.read_text())


def _data():
    return load("11_rajasthan_surname_to_category", "data")


def test_category_normaliser_maps_every_spelling_the_files_use():
    """The suffix is a sex flag, not a fifth category."""
    data = _data()
    raw = pd.Series(
        ["OBC (Woman)", "OBCW", "OBC W", "ST(Woman)", "GEN", "General (Woman)", "SC"]
    )
    out = data.normalise_category(raw)
    assert out["category"].tolist() == ["OBC", "OBC", "OBC", "ST", "General"] + [
        "General",
        "SC",
    ]
    assert out["female"].tolist() == [True, True, True, True, False, True, False]
    assert (
        data.normalise_category(pd.Series(["INHABITED", ""]))["category"].eq("").all()
    )


def test_surname_rule_cuts_relatives_out_of_the_name_field():
    data = _data()
    names = pd.Series(
        [
            "GHASIRAM S/O SURJARAM",
            "DOLI / HIMMAT SINGH",
            "sohni (sona devi )",
            "VIKRAM SINGH / S S",
            "सुशीला देवी",
            "RAM KANVARI DEVI`",
        ]
    )
    assert data.surname_tokens(names).tolist() == [
        "ghasiram",
        "doli",
        "sohni",
        "singh",
        "devi",
        "devi",
    ]


def test_reweighting_lands_on_the_assumed_state_shares(summary):
    """The whole point of the second column: the marginals are Rajasthan's."""
    data = _data()
    cats = pd.Series(["SC"] * 20 + ["ST"] * 20 + ["OBC"] * 40 + ["General"] * 20)
    w = data.reweight(cats)
    got = pd.Series(w).groupby(cats.to_numpy()).sum() / w.sum()
    for c, share in data.RAJASTHAN_SHARES.items():
        assert abs(got[c] - share) < 1e-9
    assert abs(sum(data.RAJASTHAN_SHARES.values()) - 1) < 1e-9


def test_the_sample_is_reservation_shaped_and_the_note_says_so(summary):
    """ST is over-represented against the census; if that ever stops being
    true the re-weighting paragraph is describing a sample that no longer
    exists."""
    assert summary["category_share_raw"]["ST"] > 0.16
    assert summary["category_share_assumed"]["ST"] == 0.135


def test_the_surname_beats_the_blind_guess_under_both_weightings(summary):
    for w in ("raw", "rajasthan"):
        h = summary["headline"][w]
        assert h["surname"] < h["blind"] - 5
        assert h["both_contest"] < h["surname_contest"]
        # Holding out a district must cost more than holding out a person.
        assert h["surname"] > h["surname_self_loo"]


def test_the_ranking_measure_separates_obc_from_general(summary):
    """The reason this analysis exists: a line SECC cannot draw."""
    assert summary["ranking"]["OBC vs General | surname"] > 0.7
    assert summary["ranking"]["SC vs rest | surname"] > 0.65


def test_deterministic_tokens_are_mostly_jati_names(summary):
    t = summary["tokens"]
    assert t["deterministic"] > 50
    assert t["deterministic_jati_names"] / t["deterministic"] > 0.6
    assert (
        t["deterministic_jati_names"]
        + t["deterministic_clan_names"]
        + len(t["deterministic_neither"])
        == t["deterministic"]
    )


def test_election_and_secc_agree_on_the_scheduled_shares(summary):
    ok = summary["outkast"]
    if not ok:
        pytest.skip("outkast extract not present")
    assert ok["corr_SC_reweighted"] > 0.9
    assert ok["corr_ST_reweighted"] > 0.9
