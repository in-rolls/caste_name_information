"""Every headline number on the front page must match the output it came from.

The failure this guards against has happened four times: an analysis is re-run,
its note is regenerated automatically, and the README -- which is written by
hand -- keeps the old number. Nobody notices, because nothing compares the two.

Each claim below pairs a regex against README.md with the output that should
supply the captured number. A claim that no longer matches is either a stale
number or a rewritten sentence; both need a human to look.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
A01 = ROOT / "analyses/01_surname_to_category/out/tab"
A02 = ROOT / "analyses/02_jati_by_geography/out/tab"
A03 = ROOT / "analyses/03_how_few_names/out/tab"
A05 = ROOT / "analyses/05_who_has_an_uninformative_name/out/tab"
A06 = ROOT / "analyses/06_neighbours/out/tab"
A07 = ROOT / "analyses/07_where_the_name_works/out/tab"
A08 = ROOT / "analyses/08_karnataka_psc/out/tab"
A11 = ROOT / "analyses/11_rajasthan_surname_to_category/out/tab"


def _json(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path} not built")
    return json.loads(path.read_text())


def _ladder(target: str, rung: str) -> float:
    path = A02 / "ladders.csv"
    if not path.exists():
        pytest.skip("analysis 02 not built")
    d = pd.read_csv(path)
    row = d[(d["target"] == target) & (d["level"] == rung) & (d["ladder"] == "records")]
    return float(row["mistakes_per_100_loo"].to_numpy()[0])


def _surname_pair(surname: str) -> tuple[float, float]:
    path = A06 / "per_surname.csv"
    if not path.exists():
        pytest.skip("analysis 06 not built")
    d = pd.read_csv(path)
    row = d[d["surname"] == surname]
    return float(row["alone"].to_numpy()[0]), float(
        row["with_neighbours"].to_numpy()[0]
    )


def _sex_gap(state: str) -> float:
    """Women's mistakes per 100 minus men's. Positive means women fare worse."""
    path = A05 / "by_sex.csv"
    if not path.exists():
        pytest.skip("analysis 05 not built")
    d = pd.read_csv(path)
    d = d[d["state"] == state].set_index("who")["mistakes_per_100"]
    return float(d["women"] - d["men"])


def _analytic_share(state: str) -> float:
    """Share of the state's roll the sex estimate actually rests on.

    Not `gendered_share`: that is measured before `by_sex` inner-joins onto the
    caste table, and a surname can be gendered and then dropped for having no
    caste row. Maharashtra reads 66% before the merge and 36% after.
    """
    path = A05 / "surname_resolution.csv"
    if not path.exists():
        pytest.skip("analysis 05 not built")
    d = pd.read_csv(path).set_index("state")
    return float(d.loc[state, "analytic_share"]) * 100


def _roll(key: str):
    return lambda: _json(A01 / "headline.json")["weighted"]["roll"][key]


def _a03(*path):
    def get():
        v = _json(A03 / "summary.json")
        for k in path:
            v = v[k]
        return v

    return get


def _mah(key: str):
    return lambda: _json(A06 / "summary.json")["held_out"]["Mahadalit census"][key]


def _ceil(key: str):
    return lambda: _json(A06 / "summary.json")["ceiling"][key]


def _caste(group: str, key: str = "wrong_per_100"):
    return lambda: _json(A05 / "summary.json")["by_caste"][group][key]


def _band(rank: str, col: str):
    """A row of analysis 01's frequency-band table."""

    def get():
        path = A01 / "by_frequency_band.csv"
        if not path.exists():
            pytest.skip("analysis 01 not built")
        d = pd.read_csv(path).set_index("rank")
        v = float(d.loc[rank, col])
        return 100 * v if col == "share_people" else v

    return get


def _state(state: str, col: str):
    def get():
        path = A07 / "by_state.csv"
        if not path.exists():
            pytest.skip("analysis 07 not built")
        return float(pd.read_csv(path).set_index("state").loc[state, col])

    return get


def _rajasthan(*keys: str):
    def read():
        s = _json(A11 / "summary.json")
        for k in keys:
            s = s[k]
        return s

    return read


def _karnataka(key: str):
    def get():
        path = A08 / "summary.json"
        if not path.exists():
            pytest.skip("analysis 08 not built")
        s = _json(path)
        if key in s:
            return s[key]
        if key in s.get("by_category", {}):
            return s["by_category"][key]["wrong_per_100"]
        return float(s["scores"][key]["mistakes_per_100"])

    return get


def _coverage(key: str):
    """From the pipeline's own output, so the README cannot drift from it."""

    def get():
        c = _json(A01 / "headline.json").get("coverage_national")
        if not c:
            pytest.skip("roll frequencies unavailable")
        return 100 * c[key] if key == "share_of_roll_covered" else c[key]

    return get


def claims():
    """(label, regex with one capture group, callable giving the value).

    Nothing here may touch the filesystem: this list is built at collection
    time, when a clean checkout has no out/tab at all.
    """

    return [
        # Section 01 is roll-weighted throughout. The SECC-weighted blind rate
        # is 29.6, and quoting the two on one page without saying which is
        # which is how the front page ended up self-contradictory.
        (
            "01 Dalit ranks higher",
            r"The Dalit ranks higher (\d+) times in 100",
            lambda: _json(A01 / "headline.json")["discrimination"]["roll"]["sc"] * 100,
        ),
        (
            "01 Adivasi ranks higher",
            r"Adivasi against everyone else the\s+figure is (\d+)",
            lambda: _json(A01 / "headline.json")["discrimination"]["roll"]["st"] * 100,
        ),
        (
            "01 roll Dalit share",
            r"room is (\d+) Dalit",
            lambda: _roll("base_rates")()["sc"] * 100,
        ),
        (
            "01 roll Adivasi share",
            r"(\d+)\s*\n?Adivasi, \d+ neither",
            lambda: _roll("base_rates")()["st"] * 100,
        ),
        (
            "01 roll blind",
            r"you are wrong \*\*(\d+)\*\*\stimes",
            lambda: _roll("err_blind")() * 100,
        ),
        (
            "01 roll with name",
            r"hear the last name and you are wrong \*\*(\d+)\*\*",
            lambda: _roll("err_per_person")() * 100,
        ),
        (
            "01 share unchanged",
            r"For \*\*(\d+)% of people the\s+surname does not change the guess",
            lambda: _roll("share_guess_unchanged")() * 100,
        ),
        (
            "01 share made worse",
            r"A further \*\*(\d+)% of people\*\*",
            lambda: _roll("share_whose_name_is_more_mixed_than_the_population")() * 100,
        ),
        # The skew: the commonest names cover a third of India and none of
        # them changes the answer. Both halves are pinned, because the pairing
        # is the point and a stale half would break it silently.
        (
            "01 top ten share",
            r"\| 1–10 \| 10 \| \*\*(\d+)%\*\*",
            _band("1-10", "share_people"),
        ),
        (
            "01 band 11-25 gainers",
            r"\| 11–25 \| 15 \| \d+% \| (\d+) \|",
            _band("11-25", "names_gain_gt0"),
        ),
        (
            "01 tail gainers",
            r"\| 1001–3930 \| 2,930 \| \d+% \| (\d+) \|",
            _band("1001-3930", "names_gain_gt0"),
        ),
        (
            "01 names in table",
            r"leaves \*\*([\d,]+) surnames\*\*",
            _coverage("names_in_table"),
        ),
        (
            "01 roll coverage",
            r"are\s+\*\*(\d+)% of all the names people",
            _coverage("share_of_roll_covered"),
        ),
        # The rung with median cell size 1, so the one where plug-in bias is
        # worst and leave-one-out is not optional.
        (
            "02 surname+village",
            r"leave \*\*(\d+) mistakes per 100\*\*",
            lambda: _ladder("jati", "surname+village"),
        ),
        (
            "02 surname alone",
            r"the\s+surname alone leaves \*\*(\d+)\*\*",
            lambda: _ladder("jati", "surname"),
        ),
        (
            "03 commonest name share",
            r"at (\d+\.\d)% of the electoral roll",
            lambda: _a03("levels", "as_written", "top_name_share")() * 100,
        ),
        (
            "03 sex-marking coverage",
            r"cover \*\*(\d+(?:\.\d)?)% of the\s+country\*\*",
            lambda: _a03("levels", "minus_clear", "people_dropped_share")() * 100,
        ),
        (
            "03 names for a quarter as written",
            r"\*\*(\d+)\*\* names cover a quarter of India",
            _a03("levels", "as_written", "names_for_25"),
        ),
        (
            "03 sex-marking plus singh and kumar",
            r"adding Singh and Kumar takes it to \*\*(\d+)%\*\*",
            lambda: _a03("levels", "minus_all", "people_dropped_share")() * 100,
        ),
        (
            "03 names for a quarter",
            r"and \*\*(\d+)\*\* if you count only names a\s+brother",
            _a03("levels", "minus_all", "names_for_25"),
        ),
        (
            "05 Dalit error",
            r"wrong about \*\*(\d+) of every 100 Dalits\*\*",
            _caste("Scheduled Caste"),
        ),
        (
            "05 other error",
            r"\*\*(\d+) of\s+every 100 people outside the schedules\*\*",
            _caste("neither"),
        ),
        (
            "05 Bihar sex gap",
            r"\*\*(\d+\.\d)\s+more mistakes per hundred than men's in Bihar\*\*",
            lambda: _sex_gap("bihar"),
        ),
        (
            "05 Rajasthan sex gap",
            r"but (\d+\.\d) \*fewer\*",
            lambda: -_sex_gap("rajasthan"),
        ),
        (
            "05 Maharashtra sex gap",
            r"and (\d+\.\d) fewer in Maharashtra",
            lambda: -_sex_gap("maharashtra"),
        ),
        # Coverage measured AFTER the merge onto the caste table, which is what
        # the estimate actually rests on. The pre-merge gendered share reads
        # 66% for Maharashtra where the analytic share is 36%.
        (
            "05 Rajasthan coverage",
            r"(\d+)% of\s+Rajasthan\'s",
            lambda: _analytic_share("rajasthan"),
        ),
        (
            "05 Punjab coverage",
            r"and (\d+)% of Punjab's",
            lambda: _analytic_share("punjab"),
        ),
        (
            "05 Bihar coverage",
            r"(\d+)% of the Bihar roll",
            lambda: _analytic_share("bihar"),
        ),
        (
            "05 Maharashtra coverage",
            r"(\d+)% of Maharashtra\'s",
            lambda: _analytic_share("maharashtra"),
        ),
        (
            "06 chaudhary alone",
            r"Chaudhary goes from (\d+) mistakes",
            lambda: _surname_pair("\u091a\u094c\u0927\u0930\u0940")[0],
        ),
        (
            "06 chaudhary rescued",
            r"Chaudhary goes from \d+ mistakes\s+to (\d+)",
            lambda: _surname_pair("\u091a\u094c\u0927\u0930\u0940")[1],
        ),
        (
            "06 prasad alone",
            r"Prasad from (\d+)\s+to \d+",
            lambda: _surname_pair("\u092a\u094d\u0930\u0938\u093e\u0926")[0],
        ),
        (
            "06 prasad rescued",
            r"Prasad from \d+\s+to (\d+)",
            lambda: _surname_pair("\u092a\u094d\u0930\u0938\u093e\u0926")[1],
        ),
        (
            "06 surname alone",
            r"the surname alone leaves \*\*(\d+)\*\*",
            _mah("surname_only"),
        ),
        (
            "06 with neighbours",
            r"neighbours bring\s+that to \*\*(\d+)\*\*",
            _mah("surname_plus_neighbours"),
        ),
        # Not "the roll page": caste is on no roll. The 9 comes from matching
        # the roll's cues against a caste register of the same population.
        (
            "06 ceiling",
            r"caste register leave\s+\*\*(\d+)\*\*",
            _ceil("mistakes_per_100"),
        ),
        (
            "06 households",
            r"([\d,]+) Scheduled Caste\s+households",
            _ceil("households"),
        ),
        ("06 villages", r"([\d,]+)\s*\nheld-out villages", _ceil("villages_held_out")),
        (
            "07 assam",
            r"closes \*\*(\d+)% of the\s+gap in Assam",
            _state("assam", "removed"),
        ),
        (
            "07 haryana",
            r"gap in Assam and\s+(\d+)% in Haryana\*\*",
            _state("haryana", "removed"),
        ),
        (
            "08 initial share",
            r"single\s+letter \*\*(\d+)% of the time\*\*",
            _karnataka("naive_is_single_letter"),
        ),
        (
            "08 SC error",
            r"wrong about \*\*(\d+) of every 100 Scheduled Caste candidates",
            _karnataka("Scheduled Caste"),
        ),
        (
            "08 General error",
            r"Scheduled Caste candidates and\s+(\d+)\s+of every 100 General ones\*\*",
            _karnataka("General"),
        ),
        (
            "08 gap closed",
            r"the surname closes (\d+)% of the gap",
            _karnataka("gap_closed_share"),
        ),
        (
            "11 blind",
            r"nothing leaves \*\*(\d+) mistakes per 100 and the last name \d+\*\*",
            _rajasthan("headline", "rajasthan", "blind"),
        ),
        (
            "11 surname",
            r"nothing leaves \*\*\d+ mistakes per 100 and the last name (\d+)\*\*",
            _rajasthan("headline", "rajasthan", "surname"),
        ),
        (
            "11 surname contestants",
            r"own surname leaves \*\*(\d+\.\d+) mistakes per 100\*\*",
            _rajasthan("headline", "rajasthan", "surname_contest"),
        ),
        (
            "11 both",
            r"both surnames \*\*(\d+\.\d+)\*\*",
            _rajasthan("headline", "rajasthan", "both_contest"),
        ),
        (
            "11 OBC vs General",
            r"above a General\s+person \*\*(\d+)\*\* times",
            lambda: 100 * _rajasthan("ranking", "OBC vs General | surname")(),
        ),
        (
            "11 SC error",
            r"The guess is wrong about \*\*(\d+) of every 100 Dalits\*\*",
            lambda: _rajasthan("by_category", "rajasthan", "SC", "wrong_per_100")(),
        ),
        (
            "11 deterministic",
            r"Of (\d+) surnames that are\s+at least 90% one category",
            _rajasthan("tokens", "deterministic"),
        ),
        (
            "11 jati names",
            r"\*\*(\d+) are literally the name of a jati\*\*",
            _rajasthan("tokens", "deterministic_jati_names"),
        ),
    ]


@pytest.mark.parametrize(
    "label,pattern,expected", claims(), ids=lambda v: v if isinstance(v, str) else ""
)
def test_readme_number_matches_its_output(label, pattern, expected) -> None:
    text = README.read_text()
    value = expected() if callable(expected) else expected
    match = re.search(pattern, text)
    assert match, f"{label}: README no longer contains a sentence matching {pattern!r}"
    printed = float(match.group(1).replace(",", ""))
    # Half of the last printed digit: 30 covers [29.5, 30.5), 10.5 covers
    # [10.45, 10.55). A number rounded correctly passes; a stale one does not.
    decimals = len(match.group(1).split(".")[1]) if "." in match.group(1) else 0
    tol = 0.5 * 10**-decimals
    assert (
        abs(printed - value) < tol
    ), f"{label}: README says {match.group(1)}, output says {value:.4f}"


def test_the_readme_says_none_only_while_none_is_true() -> None:
    """The pairing is the point: ten names, a third of India, no information.

    The word "none" carries a number, so it needs pinning like one. If any of
    the ten commonest surnames ever starts moving the guess off the base rate,
    this sentence becomes false while still reading fine.
    """
    path = A01 / "by_frequency_band.csv"
    if not path.exists():
        pytest.skip("analysis 01 not built")
    gainers = pd.read_csv(path).set_index("rank").loc["1-10", "names_gain_gt0"]
    says_none = "| 1–10 | 10 | **32%** | **none** |" in README.read_text()
    assert says_none == (
        gainers == 0
    ), f"README says none={says_none}, but {gainers} of the top ten gain"
