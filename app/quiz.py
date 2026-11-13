"""The quiz's logic, kept out of the Streamlit file so it can be tested.

The game draws one Dalit and one non-Dalit at random and asks which is which.
That is not an illustration of the repo's headline statistic; it is the same
experiment. The ranking measure in `last_name_basis.scoring.ranks_above` is
defined as the share of exactly these pairs in which the Dalit's surname ranks
higher, so a player's score and the data's score are the same quantity.

People are drawn in proportion to how many of them there are, so the pairs a
player sees are the pairs the statistic averages over: mostly common surnames,
occasionally a decisive one.
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

# The tests cross-check  against last_name_basis.scoring.ranks_above,
# which is why src is importable from here.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

HERE = Path(__file__).resolve().parent
NAMES = HERE / "data" / "names.csv"
LOCAL_LOG = HERE / "data" / "rounds.csv"

LOG_COLUMNS = [
    "at",
    "session",
    "round",
    "left",
    "right",
    "dalit_side",
    "picked",
    "correct",
]


# Names that mark a religion rather than a caste. They are near-perfect "not
# Dalit" tells -- together 4.8% of non-Dalit draws against 0.1% of Dalit draws,
# at compositions around 0.2% to 1.6% Dalit -- so a player who recognizes them
# wins those rounds without knowing anything about caste. This repo does not
# treat religion as a feature, and a game that rewards it would.
RELIGION_MARKED = frozenset("""
    khan ali sk ansari sheikh shaikh begum bibi fatima fatma mohammad mohammed
    md muhammad hussain hossain syed sayyed qureshi abdul rahman rehman mondal
    molla mullick sardar shah alam akhtar parveen nisha yasmin
    """.split())


def load_names(path: Path = NAMES) -> pd.DataFrame:
    """The commonest surnames, with how many of each group carry them.

    Two exclusions, both applied to the table rather than to the draw, so that
    `baseline` and `draw` see the same names. Rejecting bad pairs at draw time
    instead would quote a baseline no player could reach: throwing out the
    coin-flip rounds lifts a perfect player two points above a figure computed
    over every pair.
    """
    d = pd.read_csv(path)
    d = d[~d["last_name"].isin(RELIGION_MARKED)]
    d = d[(d["n_sc"] > 0) & (d["n_not_sc"] > 0)].reset_index(drop=True)
    return d[~_is_variant_of_a_commoner_name(d["last_name"])].reset_index(drop=True)


def _is_variant_of_a_commoner_name(labels: pd.Series) -> np.ndarray:
    """Flag each name that is another, commoner name spelled differently.

    The table arrives sorted by frequency, so the first spelling seen is the one
    kept. `sing` goes and `singh` stays; `majhi` goes and `manjhi` stays.
    """
    kept: list[str] = []
    drop = np.zeros(len(labels), dtype=bool)
    for i, name in enumerate(labels):
        if any(too_alike(name, k) for k in kept):
            drop[i] = True
        else:
            kept.append(name)
    return drop


def baseline(names: pd.DataFrame, same_name: bool = False) -> float:
    """What the data scores on this exact game, from this exact table.

    Quoted in the app, so it is computed rather than written down: if the table
    is regenerated and the number moves, the app moves with it.

    `same_name` excludes rounds that would show one surname on both sides. The
    draw refuses them, because "which of these two Singhs is the Dalit" is not a
    question, and 3.1% of pairs are of that kind. Counting them as the coin
    flips they are would put the quoted figure a point below anything a player
    could reach, so both ends exclude them.

    With `same_name=True` this is `scoring.ranks_above` over the same inputs,
    which the tests use as a cross-check on the arithmetic here.
    """
    p = names["p_sc"].to_numpy(float)
    sc = names["n_sc"].to_numpy(float)
    other = names["n_not_sc"].to_numpy(float)
    weight = np.outer(sc / sc.sum(), other / other.sum())
    if not same_name:
        np.fill_diagonal(weight, 0.0)
    wins = (p[:, None] > p[None, :]) + 0.5 * (p[:, None] == p[None, :])
    return float((weight * wins).sum() / weight.sum())


@dataclass(frozen=True)
class Pair:
    """Two surnames, one belonging to a Dalit, in the order shown."""

    left: str
    right: str
    dalit_side: str  # "left" or "right"

    @property
    def dalit(self) -> str:
        return self.left if self.dalit_side == "left" else self.right


def too_alike(a: str, b: str, threshold: int = 88) -> bool:
    """Whether two surnames are the same name spelled two ways.

    `sing` against `singh`, or `majhi` against `manjhi`, is not a question about
    caste. Seventeen such pairs sit among the thousand commonest names, and a
    round built from one measures transliteration.
    """
    return a == b or fuzz.ratio(a, b) >= threshold


def draw(names: pd.DataFrame, rng: np.random.Generator) -> Pair:
    """One Dalit and one non-Dalit, each drawn in proportion to their numbers.

    One surname can be drawn for both sides, since every name here has bearers
    in both groups. Those rounds are unanswerable and are redrawn; `baseline`
    excludes them for the same reason, so this stays the experiment it scores.
    """
    sc = names["n_sc"].to_numpy(float)
    other = names["n_not_sc"].to_numpy(float)
    label = names["last_name"]
    a = b = ""
    while not a or a == b:
        a = label.iloc[rng.choice(len(names), p=sc / sc.sum())]
        b = label.iloc[rng.choice(len(names), p=other / other.sum())]
    if rng.random() < 0.5:
        return Pair(left=a, right=b, dalit_side="left")
    return Pair(left=b, right=a, dalit_side="right")


def perfect_player(pair: Pair, names: pd.DataFrame) -> str:
    """What a player who knew every surname's composition would answer.

    Used to check that the game really is the measure: answering this way over
    many rounds must score the baseline.
    """
    p = names.set_index("last_name")["p_sc"]
    left, right = p.get(pair.left, 0.0), p.get(pair.right, 0.0)
    if left == right:
        return "left"
    return "left" if left > right else "right"


def log_row(pair: Pair, picked: str, session: str, index: int) -> dict:
    return {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session": session,
        "round": index,
        "left": pair.left,
        "right": pair.right,
        "dalit_side": pair.dalit_side,
        "picked": picked,
        "correct": int(picked == pair.dalit_side),
    }


def append_local(row: dict, path: Path = LOCAL_LOG) -> None:
    """Fallback when no sheet is configured, and the path the tests exercise."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({k: row[k] for k in LOG_COLUMNS})
