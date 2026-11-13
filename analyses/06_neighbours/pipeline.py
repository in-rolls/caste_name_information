"""Do neighbors rescue an uninformative surname? Entry point: `make a06`."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import ceiling as C
import neighbours as nb
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", HERE / "out/fig"

LADDERS = [
    ("land records", "records_ladder", "accounts", 3),
    ("Mahadalit census", "census_ladder", "households", 4),
]


def ladders():
    """analysis 02's loaders, imported without colliding on the name `data`."""
    folder = HERE.parent / "02_jati_by_geography"
    sys.path.insert(0, str(folder))
    saved = sys.modules.pop("data", None)
    try:
        spec = importlib.util.spec_from_file_location(
            "jati_data_06", folder / "data.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.modules.pop("data", None)
        if saved is not None:
            sys.modules["data"] = saved
        sys.path.remove(str(folder))


def _mahadalit():
    """The one table with names, father's name and hamlet on the same row."""
    folder = HERE.parent / "02_jati_by_geography"
    sys.path.insert(0, str(folder))
    saved = sys.modules.pop("data", None)
    try:
        spec = importlib.util.spec_from_file_location(
            "mahadalit_06", folder / "mahadalit.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = mod.load()
        if d is None:
            return None
        d["first"] = d["name_hoh"].str.split().str[0]
        d["fat_last"] = d["name_fat"].str.split().str[-1].fillna("")
        d["fat_first"] = d["name_fat"].str.split().str[0].fillna("")
        d.attrs["geo"] = mod.GEO
        return d
    finally:
        sys.modules.pop("data", None)
        if saved is not None:
            sys.modules["data"] = saved
        sys.path.remove(str(folder))


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    source = ladders()

    results, surname_tables = [], []
    census_test_villages = None
    for label, loader, weight, parts in LADDERS:
        ladder = getattr(source, loader)()
        if ladder is None:
            continue
        vsj = nb.village_surname_jati(ladder, "surname+village", weight, parts)
        scored = nb.fit_and_score(vsj, weight)
        if label == "Mahadalit census":
            _, census_test_villages = nb.split_villages(vsj["village"].unique())
        scored["ladder"] = label
        results.append(scored)

        per = nb.per_surname(vsj, weight, scored["alpha"])
        per["ladder"] = label
        surname_tables.append(per)

    table = pd.DataFrame(results)
    table.to_csv(TAB / "held_out.csv", index=False)
    per_surname = pd.concat(surname_tables, ignore_index=True)
    per_surname.to_csv(TAB / "per_surname.csv", index=False)

    summary = {"held_out": table.set_index("ladder").to_dict("index")}

    # The other end of the bracket: everything the roll prints. Only the
    # Mahadalit census carries the father's name and the hamlet on the same row.
    mahadalit = _mahadalit()
    if mahadalit is not None and census_test_villages is not None:
        mahadalit.attrs["test_villages"] = census_test_villages
        chain = [
            ["surname", "fat_last", "fat_first"] + mahadalit.attrs["geo"],
            ["surname"] + mahadalit.attrs["geo"],
            ["surname"],
        ]
        # Score on the very same held-out villages the neighbor rungs use.
        # Deriving a split independently does NOT do this: naampata's ladder
        # covers 27,687 villages and the raw files 28,602, so shuffling the two
        # lists put only 2,509 of ~8,300 test villages in common and the bracket
        # rows described different people.
        # str.cat, not .agg(axis=1): the latter is row-wise Python and turned
        # a two-minute pipeline into an hour on 2.98M rows.
        geo4 = [mahadalit[c] for c in mahadalit.attrs["geo"][:4]]
        village = geo4[0].str.cat(geo4[1:], sep="|")
        test_v = mahadalit.attrs["test_villages"]
        mask = village.isin(test_v).to_numpy()
        summary["ceiling"] = C.ceiling(
            mahadalit, chain, test_mask=mask, villages_held_out=len(test_v)
        )
        summary["ceiling"]["shares_split_with_neighbour_rungs"] = True
        summary["ceiling_all_households"] = C.ceiling(mahadalit, chain)
    (TAB / "summary.json").write_text(json.dumps(summary, indent=2))

    import figures

    figures.bracket(table, FIG / "bracket.png")
    if "ceiling" in summary:
        figures.ceiling(summary["ceiling"], held=table, out=FIG / "ceiling.png")
    figures.per_surname(
        per_surname[per_surname["ladder"] == "land records"],
        FIG / "per_surname.png",
    )

    print(json.dumps(summary, indent=2))
    print("\n=== the commonest surnames, held-out villages ===")
    print(per_surname.round(1).to_string(index=False))
    print(f"\nwrote {TAB} and {FIG}")


if __name__ == "__main__":
    main()
