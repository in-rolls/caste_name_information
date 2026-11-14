"""Whose name tells you nothing, and whether that group is random.

The other analyses report a population average: a name saves about nine
mistakes per hundred, and for most people it changes nothing. This asks who the
"most people" are, because if the uninformative names are not evenly spread then
every name-based caste method has differential error in a knowable direction --
and that is the thing a downstream user of instate, outkast or a BISG-style
method needs to know before using one.

Two cuts, and both use data already in the repo:

by caste  weight each surname by the people of that caste who carry it, so the
          figure is "mistakes made on a Dalit" rather than "mistakes on average";
by sex    weight by female and male bearers, using naampy's first-name gender to
          sex the roll. Women disproportionately carry devi and kumari, which
          carry no caste signal at all.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from last_name_basis.siblings import repo
from last_name_basis.upnaam import iter_resolved_roll, resolved_roll_path

CATEGORY_LABEL = {"sc": "Scheduled Caste", "st": "Scheduled Tribe", "other": "neither"}


def by_caste(
    named: pd.DataFrame, prob_cols: list[str], categories: list[str]
) -> pd.DataFrame:
    """Mistakes made on a person, split by the person's own caste.

    The weighting is the whole point. Weighting names by all their bearers gives
    the population average; weighting by the bearers *of one caste* gives what a
    member of that caste actually experiences.
    """
    p = named[prob_cols].to_numpy()
    err = (1 - p.max(axis=1)) * 100
    guess = p.argmax(axis=1)

    counts = named[[f"n_{c}" for c in categories]].to_numpy()
    prior = counts.sum(axis=0) / counts.sum()

    # The best constant guess names the largest group, so it is wrong about
    # every member of every other group and right about all of that one.
    blind_guess = int(prior.argmax())

    rows = []
    for i, cat in enumerate(categories):
        w = counts[:, i]
        w = w / w.sum()
        found = float((w * (guess == i)).sum())
        rows.append(
            {
                "caste": CATEGORY_LABEL[cat],
                "share_of_people": float(prior[i]),
                # How uninformative the names this group carries are. A
                # property of the name, averaged over the group's bearers --
                # NOT how often the guess is wrong about one of them.
                "name_vagueness_per_100": float((w * err).sum()),
                "found_by_the_guess": found,
                # How often the guess is actually wrong about a member of this
                # group. These weight up to the headline error exactly.
                "wrong_per_100": 100 * (1 - found),
                "blind_wrong_per_100": 0.0 if i == blind_guess else 100.0,
            }
        )
    out = pd.DataFrame(rows)
    out.attrs["blind"] = float((1 - prior.max()) * 100)
    return out


def first_name_gender(min_bearers: int = 200) -> dict[str, float] | None:
    path = repo("naampy") / "in_rolls_state_year_fn_naampy.csv.gz"
    if not path.exists():
        return None
    d = pd.read_csv(path, usecols=["first_name", "n_female", "n_male"])
    g = d.groupby("first_name")[["n_female", "n_male"]].sum()
    n = g["n_female"] + g["n_male"]
    return (g["n_female"] / n)[n >= min_bearers].to_dict()


def surname_by_sex(state: str, gender: dict[str, float]) -> pd.DataFrame | None:
    """Female and male bearers of each surname, from one state's roll.

    Sex comes from the positional given-name token and the question is about
    Upnaam's recorded surname, so the two tokens are distinct. In Maharashtra,
    the surname is first and the second token supplies the gender lookup.
    """
    path = resolved_roll_path(state)
    if not path.exists():
        return None
    female: Counter[str] = Counter()
    male: Counter[str] = Counter()
    input_weight = 0
    resolved_weight = 0
    gendered_weight = 0
    for frame in iter_resolved_roll(path, state=state):
        input_weight += int(frame["weight"].sum())
        resolved = frame.loc[~frame["abstained"]].copy()
        resolved_weight += int(resolved["weight"].sum())
        if resolved.empty:
            continue
        tokens = resolved["name_raw"].astype("string").str.split(expand=True)
        if tokens.shape[1] < 2:
            continue
        given = tokens[0].copy()
        surname_first = resolved["surname_position"].eq("first")
        given.loc[surname_first] = tokens.loc[surname_first, 1]
        given = given.str.casefold()
        p_female = given.map(gender)
        # A one-letter token is an initial, and a token equal to the resolved
        # surname means the position rule landed on the surname itself.
        looks_like_a_given_name = given.str.len().gt(1) & given.ne(
            resolved["surname"].astype("string").str.casefold()
        )
        usable = p_female.notna() & looks_like_a_given_name
        if not usable.any():
            continue
        weights = resolved.loc[usable, "weight"].astype(float)
        probabilities = p_female.loc[usable].astype(float)
        surnames = resolved.loc[usable, "surname"]
        gendered_weight += int(weights.sum())
        female.update((weights * probabilities).groupby(surnames).sum().to_dict())
        male.update((weights * (1 - probabilities)).groupby(surnames).sum().to_dict())
    names = set(female) | set(male)
    result = pd.DataFrame(
        {
            "last_name": sorted(names),
            "female": [female.get(x, 0.0) for x in sorted(names)],
            "male": [male.get(x, 0.0) for x in sorted(names)],
        }
    )
    result.attrs.update(
        {
            "input_weight": input_weight,
            "resolved_weight": resolved_weight,
            "gendered_weight": gendered_weight,
            "resolver_revision": "resolver-v1",
        }
    )
    return result


def by_sex(
    named: pd.DataFrame, sexed: pd.DataFrame, prob_cols: list[str]
) -> pd.DataFrame:
    """Mistakes made on a woman against a man, in one state."""
    d = named.merge(sexed, on="last_name", how="inner")
    err = (1 - d[prob_cols].to_numpy().max(axis=1)) * 100
    rows = []
    for label, col in (("women", "female"), ("men", "male")):
        w = d[col].to_numpy(float)
        w = w / w.sum()
        rows.append(
            {
                "who": label,
                "people": float(d[col].sum()),
                "mistakes_per_100": float((w * err).sum()),
            }
        )
    out = pd.DataFrame(rows)
    out.attrs["matched_names"] = len(d)
    return out


def spread(named: pd.DataFrame, weight: str = "share") -> dict:
    """How unevenly informativeness is distributed across people."""
    w = named[weight].fillna(0).to_numpy(float)
    w = w / w.sum()
    gain = named["gain"].to_numpy()
    return {
        "share_gain_zero": float(w[gain <= 1e-9].sum()),
        "share_of_gain_from_top_decile": float(
            np.sort(w * gain)[::-1][: max(1, len(gain) // 10)].sum()
            / max((w * gain).sum(), 1e-12)
        ),
    }
