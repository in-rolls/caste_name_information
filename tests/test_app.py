"""The quiz, and the claim that it is the same experiment as the measure."""

from __future__ import annotations

import csv
import importlib.util
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"


def _quiz():
    if not (APP / "data" / "names.csv").exists():
        pytest.skip("app data not built; run `make app-data`")
    spec = importlib.util.spec_from_file_location("quiz", APP / "quiz.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["quiz"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def quiz():
    return _quiz()


@pytest.fixture(scope="module")
def names(quiz):
    return quiz.load_names()


def test_the_shipped_table_is_the_thousand_commonest_names(quiz, names):
    shipped = pd.read_csv(APP / "data" / "names.csv")
    assert len(shipped) == 1000
    assert shipped["n_roll"].is_monotonic_decreasing
    # What is playable is smaller: religion-marked names and duplicate
    # spellings are removed before anyone sees a round.
    assert 800 < len(names) < len(shipped)
    assert (names["n_sc"] > 0).all() and (names["n_not_sc"] > 0).all()


def test_the_baseline_matches_the_shared_scoring_routine(quiz, names):
    """Cross-check on the pairwise arithmetic in `baseline`.

    Told to include same-name rounds, it must equal `ranks_above`, which is the
    routine the rest of the repo uses and which was itself checked against a
    second implementation.
    """
    from last_name_basis.scoring import ranks_above

    mine = quiz.baseline(names, same_name=True)
    theirs = ranks_above(
        names["p_sc"].to_numpy(float),
        names["n_sc"].to_numpy(float),
        names["n_not_sc"].to_numpy(float),
    )
    assert abs(mine - theirs) < 1e-9, (mine, theirs)


def test_the_baseline_the_app_quotes_comes_from_the_shipped_table(quiz, names):
    """The app prints this number, so it must be computed and not written down.

    If the table is regenerated and the figure moves, the app moves with it.
    """
    target = quiz.baseline(names)
    assert 0.75 < target < 0.95, target


def test_playing_perfectly_scores_the_baseline(quiz, names):
    """The claim the whole design rests on.

    The game draws one Dalit and one non-Dalit and asks which is which. The
    repo's ranking measure is defined as the share of exactly those pairs in
    which the Dalit's surname ranks higher. So a player who knows every
    surname's composition must score the baseline, and if this drifts the game
    has stopped being the measurement it claims to be.
    """
    rng = np.random.default_rng(20260830)
    right = 0
    rounds = 4000
    for _ in range(rounds):
        pair = quiz.draw(names, rng)
        if quiz.perfect_player(pair, names) == pair.dalit_side:
            right += 1
    played = right / rounds
    target = quiz.baseline(names)
    assert abs(played - target) < 0.02, (played, target)


def test_the_two_sides_are_shuffled(quiz, names):
    """A fixed side would make the game trivially winnable and the log useless."""
    rng = np.random.default_rng(7)
    sides = [quiz.draw(names, rng).dalit_side for _ in range(400)]
    assert 0.4 < sides.count("left") / len(sides) < 0.6


def test_a_round_is_logged_with_no_identifying_field(quiz, names, tmp_path):
    """The fallback path, exercised here rather than only in production."""
    rng = np.random.default_rng(1)
    pair = quiz.draw(names, rng)
    row = quiz.log_row(pair, pair.dalit_side, "abc123", 1)
    assert row["correct"] == 1
    assert (
        quiz.log_row(
            pair, "left" if pair.dalit_side == "right" else "right", "abc123", 1
        )["correct"]
        == 0
    )

    path = tmp_path / "rounds.csv"
    quiz.append_local(row, path)
    quiz.append_local(row, path)
    with path.open(encoding="utf8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert set(rows[0]) == set(quiz.LOG_COLUMNS)
    # Nothing here may identify a player.
    assert not {"ip", "name", "email", "user", "agent"} & set(rows[0])


def test_religion_marked_names_are_kept_out_of_the_game(quiz):
    """They are a free win that has nothing to do with caste.

    khan, ali, bibi, ansari and the rest sit at 0.2% to 1.6% Dalit and together
    carry 4.8% of non-Dalit draws against 0.1% of Dalit draws. A player who
    recognizes them takes those rounds without knowing anything about caste,
    and this repo does not treat religion as a feature.
    """
    shipped = set(pd.read_csv(APP / "data" / "names.csv")["last_name"])
    playable = set(quiz.load_names()["last_name"])
    assert {"khan", "ali", "ansari"} & shipped, "expected these in the raw table"
    assert not (quiz.RELIGION_MARKED & playable)


def test_a_round_never_shows_one_name_twice_or_spelled_two_ways(quiz, names):
    """`sing` against `singh`, or `singh` against `singh`, is not a question."""
    rng = np.random.default_rng(11)
    for _ in range(600):
        pair = quiz.draw(names, rng)
        assert pair.left != pair.right, pair
        assert not quiz.too_alike(pair.left, pair.right), pair
