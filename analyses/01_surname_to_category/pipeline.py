"""Build every table and figure. Single entry point: `make all`."""

from __future__ import annotations

import json
from pathlib import Path

import coverage as cov
import figures
import metrics
import pandas as pd
import report
from data import base_rates, load_cells, per_name
from metrics import (
    add_metrics,
    by_frequency_band,
    confusion,
    entropy_bits,
    headline,
    recall_precision,
    signal_decomposition,
    uninformative_cdf,
    weighted_summary,
)

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", HERE / "out/fig"
ANNOTATE = ("singh", "kumar", "devi", "ram", "sharma", "yadav", "paswan", "jatav")

# Four regimes, four to a row: sits at the base rate / rules out / near a
# coin-flip / rules in.
WAFFLE = [
    "jha",
    "yadav",
    "sharma",
    "tiwari",
    "singh",
    "prasad",
    "devi",
    "kumar",
    "lal",
    "das",
    "ram",
    "kaur",
    "jatav",
    "manjhi",
    "paswan",
    "chamar",
]


def build(scheme: str) -> pd.DataFrame:
    cells = load_cells()
    named = per_name(cells, scheme=scheme)
    return add_metrics(named, base_rates(named))


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    secc = cov.with_roll_frequency(build("secc"))
    census = build("census")
    base = base_rates(secc)

    # `cut` is measured against a prior, so it only means anything alongside the
    # weighting that prior came from. The note asks about a randomly met person,
    # so the shipped table is measured against the roll-weighted prior; mixing
    # the two is how an earlier draft had 9 squares and 16% for one quantity.
    roll_prior = weighted_summary(secc, "share_roll")["base_rates"]
    secc = add_metrics(secc, pd.Series({f"n_{k}": v for k, v in roll_prior.items()}))
    h = headline(secc, base)
    h["caste_entropy_bits"] = entropy_bits((base / base.sum()).to_numpy())

    secc.to_parquet(TAB / "per_name_secc_weighted.parquet", index=False)
    census.to_parquet(TAB / "per_name_census_weighted.parquet", index=False)

    bands = by_frequency_band(secc)
    cdf = uninformative_cdf(secc)
    look = report.lookup_table(secc)
    floors = report.floor_sensitivity()
    shift = report.pooling_shift(secc, census)
    conf = confusion(secc)
    rp = recall_precision(secc, weight="share_roll")
    decomp = signal_decomposition(load_cells())
    h["signal_decomposition"] = decomp
    top50 = secc.head(50)[report.DISPLAY]

    bands.to_csv(TAB / "by_frequency_band.csv", index=False)
    cdf.to_csv(TAB / "uninformative_cdf.csv", index=False)
    look.to_csv(TAB / "lookup.csv")
    floors.to_csv(TAB / "floor_sensitivity.csv", index=False)
    shift.to_csv(TAB / "pooling_shift.csv")
    rp.to_csv(TAB / "recall_precision.csv")
    conf.to_csv(TAB / "confusion.csv")
    top50.to_csv(TAB / "top50_by_frequency.csv", index=False)

    audit = report.surname_position_audit()
    audit.to_csv(TAB / "surname_position_audit.csv", index=False)
    h["surname_position_audit"] = audit.set_index("basis").to_dict("index")

    covr = cov.coverage(secc, "Delhi")
    if covr:
        h["coverage_delhi"] = covr

    # Two weightings of the same table. SECC weights by whose household the
    # census recorded; roll weights by who you would actually meet. Each is
    # summarized against its own prior -- mixing them breaks the arithmetic.
    h["coverage_national"] = cov.national_coverage(build("secc"))

    # The quiz's table. Committed, unlike out/tab, because the deployed app
    # needs it; generated here so it cannot drift from the analysis.
    app = HERE.parent.parent / "app" / "data"
    app.mkdir(parents=True, exist_ok=True)
    quiz = (
        secc[secc["n_roll"].notna()]
        .sort_values("n_roll", ascending=False)
        .head(1000)
        .assign(
            n_not_sc=lambda d: d[["n_st", "n_other"]].sum(axis=1),
        )[["last_name", "n_sc", "n_not_sc", "p_sc", "n_roll"]]
    )
    quiz.to_csv(app / "names.csv", index=False)
    # Accuracy against the mode is dominated by the base rate; this is not.
    h["discrimination"] = {
        "secc": metrics.discrimination(secc),
        "roll": metrics.discrimination(secc, "share_roll"),
        "note": (
            "share of (member, non-member) pairs in which the member's surname "
            "ranks higher; 0.5 is no information"
        ),
    }
    h["weighted"] = {
        "secc": weighted_summary(secc, "share"),
        "roll": weighted_summary(secc, "share_roll"),
    }

    # The same measures, weighted by who you would actually meet rather than by
    # whose household SECC happened to record. The gap is reported, not hidden.
    roll_base_sc = h["weighted"]["roll"]["base_rates"]["sc"]
    # Names that leave the guess harder than for a stranger.
    roll_w = secc["share_roll"].fillna(0)
    roll_w = roll_w / roll_w.sum()
    h["share_harder_than_stranger"] = float(
        roll_w[secc["err"] > h["weighted"]["roll"]["err_blind"]].sum()
    )
    h["share_within_5pts_of_base"] = float(
        secc.loc[(secc["p_sc"] - roll_base_sc).abs() < 0.05, "share_roll"].sum()
        / secc["share_roll"].sum()
    )
    (TAB / "headline.json").write_text(json.dumps(h, indent=2))

    baseline = h["weighted"]["roll"]["err_blind"] * 100
    figures.random_hundred(secc, baseline, FIG / "random_hundred.png")
    figures.name_waffles(secc, WAFFLE, FIG / "name_waffles.png")
    figures.common_and_empty(secc, roll_base_sc, FIG / "common_and_empty.png")
    figures.mistakes_by_rank(
        secc, baseline, FIG / "mistakes_by_rank.png", annotate=ANNOTATE
    )
    figures.mistakes_cdf(secc, baseline, FIG / "mistakes_cdf.png")
    figures.err_vs_blind(secc, FIG / "err_vs_blind.png", annotate=ANNOTATE)

    print(json.dumps(h, indent=2))
    print("\n=== informativeness by how common the name is ===")
    print(report.fmt(bands))
    print("\n=== how common are the uninformative names ===")
    print(report.fmt(cdf))
    print("\n=== lookup ===")
    print(report.fmt(look))
    print("\n=== suppression-floor sensitivity ===")
    print(report.fmt(floors, 4))
    print("\n=== does the headline survive the surname-position bug? ===")
    print(report.fmt(audit, 3))
    print("\n=== pooling: SECC-weighted vs Census-reweighted (biggest movers) ===")
    print(report.fmt(shift))
    print("\n=== where the errors land (guess x truth, share of all people) ===")
    print(report.fmt(conf))
    print("\n=== who the guessing finds and who it misses ===")
    print(report.fmt(rp))
    print("\n=== how much of the name's signal is really geography (bits) ===")
    print(json.dumps(decomp, indent=2))
    print(f"\nwrote {TAB} and {FIG}")


if __name__ == "__main__":
    main()
