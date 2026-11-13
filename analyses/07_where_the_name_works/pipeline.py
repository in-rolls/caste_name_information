"""Where a surname works, state by state. Entry point: `make a07`."""

from __future__ import annotations

import json
from pathlib import Path

import data as source
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", HERE / "out/fig"
SPOTLIGHT = ["assam", "bihar", "punjab", "haryana"]
# The states upnaam has resolved. Their rolls give a second, independent read on
# how concentrated a state's surnames are, which every figure in analysis 03
# otherwise takes from instate alone.
RESOLVED = ["bihar", "maharashtra", "punjab", "rajasthan"]
INSTATE = HERE.parent / "03_how_few_names/out/tab/by_state.csv"


def compare_with_instate(rolls: list[dict]) -> dict:
    """Do instate and upnaam agree on how concentrated a state's names are?"""
    if not INSTATE.exists():
        return {}
    d = pd.read_csv(INSTATE)
    d["key"] = d["state"].str.lower().str.replace(" ", "_", regex=False)
    d = d.set_index("key")
    out = {}
    for roll in rolls:
        state = roll["state"]
        if state not in d.index:
            continue
        out[state] = {
            "names_for_half_instate": int(d.loc[state, "names_for_half"]),
            "names_for_half_roll": roll["names_for_half"],
            "top10_share_instate": float(d.loc[state, "top10_share"]),
            "top10_share_roll": roll["top10_share"],
        }
    return out


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    per = source.load()
    table = source.state_table(per)
    table.to_csv(TAB / "by_state.csv", index=False)

    spotlight = {s: source.decisive_names(per, s) for s in SPOTLIGHT}
    for state, d in spotlight.items():
        d.insert(0, "state", state)
    if spotlight:
        import pandas as pd

        pd.concat(spotlight.values(), ignore_index=True).to_csv(
            TAB / "decisive_names.csv", index=False
        )

    splits = [r for r in (source.decompose(per, x) for x in table["state"]) if r]
    if splits:
        pd.DataFrame(
            [{**r, "dominant": ", ".join(r["dominant"])} for r in splits]
        ).sort_values("delta", ascending=False).to_csv(
            TAB / "dominant_names.csv", index=False
        )

    singh = source.one_name_across_states(per, "singh")
    singh.to_csv(TAB / "one_name_across_states.csv", index=False)

    rolls = [r for r in (source.roll_concentration(x) for x in RESOLVED) if r]
    if rolls:
        pd.DataFrame(
            [{k: v for k, v in r.items() if k != "commonest"} for r in rolls]
        ).to_csv(TAB / "roll_concentration.csv", index=False)
        pd.DataFrame(
            [{"state": r["state"], **c} for r in rolls for c in r["commonest"]]
        ).to_csv(TAB / "roll_commonest.csv", index=False)

    best, worst = table.iloc[0], table.iloc[-1]
    summary = {
        # Two collections, two pipelines, one answer. The only cross-source
        # check in the repo.
        "roll_concentration": {
            r["state"]: {k: v for k, v in r.items() if k != "state"} for r in rolls
        },
        "instate_comparison": compare_with_instate(rolls),
        "dominant_names": {r["state"]: r for r in splits},
        # The mechanism without an index: as a name covers more of a state, its
        # caste composition converges on that state's own.
        "singh_across_states": singh.to_dict("records"),
        "singh_share_vs_distance": float(
            singh["share_of_state"].corr(singh["distance_from_base"].abs())
        ),
        "states": int(len(table)),
        "names_total": int(table["names"].sum()),
        "coverage_share_range": [
            float(table["covered_share"].min()),
            float(table["covered_share"].max()),
        ],
        "best": {
            "state": best["state"],
            "removed": float(best["removed"]),
            "covered_share": float(best["covered_share"]),
        },
        "worst": {
            "state": worst["state"],
            "removed": float(worst["removed"]),
            "covered_share": float(worst["covered_share"]),
        },
        # The objection a reader raises first: the floor keeps common names,
        # and common names are the uninformative ones. If the ordering held
        # only before this control, the result would be an artifact of it.
        "top25_control": {
            "spearman_with_full": float(
                table["removed"].rank().corr(table["removed_top25"].rank())
            ),
            "by_state": {
                r["state"]: float(r["removed_top25"]) for _, r in table.iterrows()
            },
        },
        "by_state": {
            r["state"]: {
                k: float(r[k])
                for k in (
                    "removed",
                    "removed_top25",
                    "blind",
                    "with_name",
                    "covered_share",
                    "sc_share_of_extract",
                )
            }
            | {"names": int(r["names"])}
            for _, r in table.iterrows()
        },
    }
    (TAB / "summary.json").write_text(json.dumps(summary, indent=2))

    import figures

    figures.where_it_works(table, FIG / "where_it_works.png")
    figures.decisive(spotlight, FIG / "decisive_names.png")
    figures.decides_versus_discriminates(table, FIG / "discriminates.png")
    if splits:
        figures.dominant_names(splits, FIG / "dominant_names.png")
    print(f"wrote {TAB} and {FIG}")


if __name__ == "__main__":
    main()
