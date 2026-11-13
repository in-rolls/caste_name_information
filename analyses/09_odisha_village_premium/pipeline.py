"""Does the village premium travel outside Bihar? Entry point: `make a09`."""

from __future__ import annotations

import json
from pathlib import Path

import data as source
import jati as norm
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", HERE / "out/fig"
A02 = HERE.parent / "02_jati_by_geography/out/tab/ladders.csv"

# The merge gate is how much two labels' surname profiles must agree before
# their spellings are treated as one. Same-jati pairs score 0.31 and up,
# different-jati pairs 0.10 and down, so anything in between is a defensible
# setting and the premium is reported across the range rather than at one point.
THRESHOLDS = [0.15, 0.25, 0.40, 0.60]

# What the floor on a jati costs. Removing the tail cuts the group count by
# almost nine tenths, so it has to be shown that it does not move the answer.
FLOORS = [(0, 0), (25, 2), (50, 2), (100, 2)]

# The reach escape: how many villages excuse a label from the size floor.
REACHES = [2, 5, 10]


def bihar() -> dict | None:
    """The Bihar rungs this is compared against, on the same protocol."""
    if not A02.exists():
        return None
    d = pd.read_csv(A02)
    d = d[(d["target"] == "jati") & (d["ladder"] == "records")].set_index("level")
    alone = float(d.loc["surname", "mistakes_per_100_loo"])
    village = float(d.loc["surname+village", "mistakes_per_100_loo"])
    return {
        "surname": alone,
        "surname_village": village,
        "premium": alone - village,
        "premium_share": 100 * (alone - village) / alone,
        "groups": int(d.loc["surname", "cells"] and 141),
        "households": int(d.loc["surname", "people"]),
    }


LADDER = [
    ("surname + village", ["surname", "village"]),
    ("surname + RI circle", ["surname", "ri"]),
    ("surname + tahsil", ["surname", "tahsil"]),
    ("surname alone", ["surname"]),
]


def bihar_ladder() -> list[float] | None:
    """Bihar's rungs at the same four sizes of place, leave-one-out."""
    if not A02.exists():
        return None
    d = pd.read_csv(A02)
    d = d[(d["target"] == "jati") & (d["ladder"] == "records")].set_index("level")
    order = ["surname+village", "surname+zone", "surname+district", "surname"]
    return [float(d.loc[k, "mistakes_per_100_loo"]) for k in order]


def bihar_blind() -> float | None:
    """Bihar's blind rate, from analysis 02's own summary rather than typed."""
    path = A02.parent / "summary.json"
    if not path.exists():
        return None
    return float(
        json.loads(path.read_text())["baselines_mistakes_per_100"]["records/jati"]
    )


def score_all(frame: pd.DataFrame, group: str) -> dict:
    alone = source.score(frame, ["surname"], group=group)
    village = source.score(frame, ["surname", "village"], group=group)
    place = source.score(frame, ["village"], group=group)
    return {
        "groups": int(frame[group].nunique()),
        "households": int(len(frame)),
        "blind": source.blind(frame, group=group),
        "surname": alone["mistakes_per_100"],
        "surname_village": village["mistakes_per_100"],
        "village_alone": place["mistakes_per_100"],
        "premium": alone["mistakes_per_100"] - village["mistakes_per_100"],
        "premium_share": 100
        * (alone["mistakes_per_100"] - village["mistakes_per_100"])
        / alone["mistakes_per_100"],
    }


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    frame = source.load()

    position = source.surname_position(frame)
    labelled = frame[["jati", "surname", "village", "district_name"]]
    result = norm.normalise(labelled)
    result["merges"].to_csv(TAB / "jati_merges.csv", index=False)
    result["dropped"].to_csv(TAB / "jati_dropped.csv", index=False)
    result["refused"].to_csv(TAB / "jati_refused.csv", index=False)
    result["floored"].to_csv(TAB / "jati_floored.csv", index=False)

    # Both sweeps below vary what the normalization keeps, so they have to see
    # the rows it would drop. Scoring them against the frame already filtered by
    # the default settings made every setting return the default's answer.
    every = frame
    frame = frame.assign(jati_norm=frame["jati"].map(result["mapping"]))
    frame = frame[frame["jati_norm"].notna()].copy()
    # Reported both ways rather than decided: a jati recorded as "Pana" and one
    # recorded as "Pana Christian" are two prediction targets unless the
    # religion is stripped, and treating religion as a predictor is not
    # something this repo does silently.
    frame["jati_no_religion"] = frame["jati_norm"].map(norm.strip_religion)

    scored = {
        "as recorded": score_all(frame, "jati_norm"),
        "religion stripped": score_all(frame, "jati_no_religion"),
    }

    sensitivity = []
    default_gate = norm.MIN_PROFILE
    for threshold in THRESHOLDS:
        norm.MIN_PROFILE = threshold
        mapping = norm.normalise(labelled)["mapping"]
        alt = every.assign(g=every["jati"].map(mapping))
        alt = alt[alt["g"].notna()]
        row = score_all(alt, "g")
        row["threshold"] = threshold
        sensitivity.append(row)
    norm.MIN_PROFILE = default_gate
    pd.DataFrame(sensitivity).to_csv(TAB / "sensitivity.csv", index=False)

    default_floor = (norm.MIN_JATI_HOUSEHOLDS, norm.MIN_JATI_VILLAGES)
    floors = []
    for households, villages in FLOORS:
        norm.MIN_JATI_HOUSEHOLDS, norm.MIN_JATI_VILLAGES = households, villages
        mapping = norm.normalise(labelled, floor=households > 0)["mapping"]
        alt = every.assign(g=every["jati"].map(mapping))
        alt = alt[alt["g"].notna()]
        row = score_all(alt, "g")
        row["min_households"] = households
        row["min_villages"] = villages
        row["rows"] = int(len(alt))
        floors.append(row)
    norm.MIN_JATI_HOUSEHOLDS, norm.MIN_JATI_VILLAGES = default_floor
    default_reach = norm.MIN_JATI_REACH
    for reach in REACHES:
        norm.MIN_JATI_REACH = reach
        mapping = norm.normalise(labelled)["mapping"]
        alt = every.assign(g=every["jati"].map(mapping))
        alt = alt[alt["g"].notna()]
        row = score_all(alt, "g")
        row["min_households"] = norm.MIN_JATI_HOUSEHOLDS
        row["min_villages"] = norm.MIN_JATI_VILLAGES
        row["reach"] = reach
        row["rows"] = int(len(alt))
        floors.append(row)
    norm.MIN_JATI_REACH = default_reach
    pd.DataFrame(floors).to_csv(TAB / "floors.csv", index=False)

    frame["ri"] = (
        frame["district_code"].astype(str)
        + "|"
        + frame["tahsil_code"].astype(str)
        + "|"
        + frame["ri_code"].astype(str)
    )
    frame["tahsil"] = (
        frame["district_code"].astype(str) + "|" + frame["tahsil_code"].astype(str)
    )
    ladder = [
        source.score(frame, keys, group="jati_norm")["mistakes_per_100"]
        for _, keys in LADDER
    ]
    pd.DataFrame(
        {"level": [name for name, _ in LADDER], "mistakes_per_100": ladder}
    ).to_csv(TAB / "ladder.csv", index=False)

    # Pooled across thirty districts, the premium is one number standing for
    # places that differ. Gajapati was the published result, so it is kept
    # separately comparable rather than absorbed.
    by_district = []
    for name, part in frame.groupby("district_name", sort=True, observed=True):
        if part["jati_norm"].nunique() < 2 or len(part) < 500:
            continue
        row = score_all(part, "jati_norm")
        row["district"] = str(name)
        row["villages"] = int(part["village"].nunique())
        by_district.append(row)
    by_district.sort(key=lambda r: -r["households"])
    pd.DataFrame(by_district).to_csv(TAB / "by_district.csv", index=False)

    summary = {
        "districts": frame.attrs["districts"],
        "ladder": ladder,
        "ladder_levels": [name for name, _ in LADDER],
        "sampling": frame.attrs["sampling"],
        "villages": int(frame["village"].nunique()),
        "surnames": int(frame["surname"].nunique()),
        "surname_position": position,
        "normalisation": {
            k: result[k]
            for k in (
                "strings_in",
                "strings_out",
                "labels_covering_99pct",
                "households_dropped",
                "households_merged",
                "candidates_refused",
                "labels_floored",
                "households_floored",
            )
        },
        "odisha": scored,
        "by_district": by_district,
        "bihar": bihar(),
        "bihar_ladder": bihar_ladder(),
        "bihar_blind": bihar_blind(),
        "sensitivity": sensitivity,
        "floors": floors,
    }
    (TAB / "summary.json").write_text(json.dumps(summary, indent=2))
    pd.DataFrame(scored).T.to_csv(TAB / "scores.csv")

    import figures

    figures.premium(summary, FIG / "village_premium.png")
    bl = bihar_ladder()
    if bl is not None:
        figures.atrophy(
            {"Bihar": bl, "Odisha": summary["ladder"]},
            {
                "Bihar": bihar_blind() or 0.0,
                "Odisha": scored["as recorded"]["blind"],
            },
            FIG / "atrophy.png",
        )
    print(f"wrote {TAB} and {FIG}")


if __name__ == "__main__":
    main()
