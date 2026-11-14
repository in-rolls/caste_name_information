"""What a surname reveals about caste category in Rajasthan. Entry: `make a11`."""

from __future__ import annotations

import json
import sys
from importlib.resources import files
from pathlib import Path

import data as source
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from last_name_basis.scoring import ranks_above  # noqa: E402

HERE = Path(__file__).resolve().parent
TAB, FIG = HERE / "out/tab", HERE / "out/fig"
MIN_TOKEN = 40
DETERMINISTIC = 0.90
ABSTAIN_BAND = 0.05
TOP_N = 20

# Tokens that are literally the name of a caste or tribe, as it appears in
# Rajasthan's SC, ST and OBC lists or in everyday use, with the spellings the
# files use. A hand list, and the reader is owed the criterion: a word that
# names a community. Clans and gotras within one community -- Shekhawat and
# Ranawat among Rajputs, Godara among Jats, Katara and Ninama among Bhils --
# go in the second set, because they name a lineage rather than a caste,
# though they pin the caste just as well. Sharma and Jain are in the first
# because in Rajasthan they are read as the community and nothing else;
# Choudhary is in neither, being a title several communities take.
JATI_NAMES = {
    # Scheduled Castes
    "meghwal",
    "meghwanshi",
    "bairwa",
    "berwa",
    "regar",
    "raigar",
    "jatav",
    "jatia",
    "jatiya",
    "khatik",
    "mahawar",
    "koli",
    "kori",
    "balai",
    "bunkar",
    "chamar",
    "harijan",
    "bhambhi",
    "bhambi",
    "salvi",
    "valmiki",
    "balmiki",
    "sansi",
    "dhobi",
    "mochi",
    "nayak",
    "dholi",
    "kanjar",
    "bawari",
    "bawariya",
    "dhanka",
    "dhanak",
    "thori",
    "nat",
    # Scheduled Tribes
    "meena",
    "mina",
    "bhil",
    "bheel",
    "damor",
    "damaria",
    "garasia",
    "garasiya",
    "gameti",
    "sahariya",
    "seharia",
    "kathodi",
    "naikda",
    "patelia",
    # Other Backward Classes
    "gurjar",
    "gujar",
    "gujjar",
    "jat",
    "mali",
    "saini",
    "kumhar",
    "kumbhar",
    "kumawat",
    "prajapat",
    "prajapati",
    "nai",
    "sen",
    "sain",
    "teli",
    "lohar",
    "suthar",
    "jangid",
    "jangir",
    "khati",
    "rebari",
    "raika",
    "rabari",
    "dewasi",
    "banjara",
    "swami",
    "yadav",
    "ahir",
    "bishnoi",
    "vishnoi",
    "sirvi",
    "ghanchi",
    "rangrez",
    "dhakad",
    "dhakar",
    "dhaker",
    "kalal",
    "kirar",
    "keer",
    "bagri",
    "damami",
    "lakhara",
    "chhipa",
    "darji",
    "soni",
    "sunar",
    "nath",
    "jogi",
    "yogi",
    "gadri",
    "gadariya",
    "gayri",
    "julaha",
    "pinjara",
    "qureshi",
    "kasai",
    "manihar",
    "lodha",
    "lodhi",
    "kharol",
    "daroga",
    "kathat",
    "mehrat",
    "sindhi",
    # General
    "rajput",
    "sharma",
    "jain",
    "brahmin",
    "brahman",
    "bania",
    "baniya",
    "vaishya",
    "mahajan",
    "agarwal",
    "agrawal",
    "kayastha",
    "vaishnav",
    "paliwal",
    "pareek",
    "purohit",
    "joshi",
    "vyas",
    "dadhich",
    "gaur",
    "audichya",
    "sanadhya",
    "khandelwal",
    "maheshwari",
    "oswal",
}

CLAN_NAMES = {
    # Rajput clans
    "shekhawat",
    "ranawat",
    "chundawat",
    "rathore",
    "rathod",
    "chauhan",
    "sisodia",
    "bhati",
    "solanki",
    "tanwar",
    "panwar",
    "parmar",
    "kachhawa",
    "hada",
    "deora",
    "jadon",
    "naruka",
    # Jat clans
    "godara",
    "punia",
    "beniwal",
    "jakhar",
    "dhaka",
    "saharan",
    # Bhil and Garasia gotras
    "katara",
    "ninama",
    "pargi",
    "ahari",
    "bhagora",
    "dindor",
    "dendor",
    "kharadi",
    "taviyad",
    "maida",
    "roat",
    "kalasua",
    "charpota",
    "koted",
    "manat",
    "dodiyar",
    "bamniya",
    "bamaniya",
    "mahida",
    "nanoma",
    "baranda",
    "vadera",
    "khant",
}


def token_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Every surname carried by at least MIN_TOKEN candidates, with its split.

    In-sample and unweighted, because this is a description of the tokens
    rather than a score: the point is to see which ones are settled, which
    are informative, and which say no more than the base rate.
    """
    cats = source.CATEGORIES
    raw = pd.crosstab(frame["surname"], frame["category"]).reindex(
        columns=cats, fill_value=0
    )
    raw = raw[raw.sum(axis=1) >= MIN_TOKEN]
    n = raw.sum(axis=1)
    share = raw.div(n, axis=0)
    base = frame["category"].value_counts(normalize=True).reindex(cats)

    w = pd.crosstab(
        frame["surname"], frame["category"], values=frame["weight"], aggfunc="sum"
    ).reindex(index=raw.index, columns=cats, fill_value=0.0)
    w_share = w.div(w.sum(axis=1), axis=0)

    majority = share.idxmax(axis=1)
    purity = share.max(axis=1)
    off_base = (purity - majority.map(base)).abs()
    tier = np.where(
        purity >= DETERMINISTIC,
        "deterministic",
        np.where(off_base <= ABSTAIN_BAND, "abstain", "informative"),
    )
    out = pd.DataFrame(
        {
            "token": raw.index,
            "n": n.to_numpy(),
            **{f"share_{c}": share[c].to_numpy() for c in cats},
            "majority": majority.to_numpy(),
            "purity": purity.to_numpy(),
            "tier": tier,
            "majority_reweighted": w_share.idxmax(axis=1).to_numpy(),
            "purity_reweighted": w_share.max(axis=1).to_numpy(),
            "is_jati_name": [t in JATI_NAMES for t in raw.index],
            "is_clan_name": [t in CLAN_NAMES for t in raw.index],
            "devanagari": raw.index.str.contains(f"[{source._DEVANAGARI}]"),
        }
    )
    return out.sort_values("n", ascending=False).reset_index(drop=True)


def outkast_rajasthan() -> pd.DataFrame | None:
    """SECC's Rajasthan cut: per surname, SC / ST / other, birth years pooled."""
    d = pd.read_parquet(
        Path(str(files("outkast"))) / "data/secc/secc_surname_composition.parquet"
    )
    d = d[d["state"].astype(str).str.lower() == "rajasthan"]
    g = d.groupby("last_name")[["n_sc", "n_st", "n_other", "total_support"]].sum()
    g["secc_share_SC"] = g["n_sc"] / g["total_support"]
    g["secc_share_ST"] = g["n_st"] / g["total_support"]
    return g.reset_index().rename(
        columns={"last_name": "token", "total_support": "secc_n"}
    )


def compare_outkast(tokens: pd.DataFrame, secc: pd.DataFrame) -> pd.DataFrame:
    """Tokens both sources hold, with each source's SC and ST share.

    SECC cannot see OBC against General, so the comparison stops at the two
    scheduled categories. The election shares are given raw and re-weighted;
    the re-weighted ones are the like-for-like comparison, since SECC is a
    population count and the raw sample is not.
    """
    m = tokens.merge(secc[["token", "secc_n", "secc_share_SC", "secc_share_ST"]])
    out = m[
        [
            "token",
            "n",
            "secc_n",
            "share_SC",
            "share_ST",
            "secc_share_SC",
            "secc_share_ST",
        ]
    ].rename(columns={"share_SC": "election_share_SC", "share_ST": "election_share_ST"})
    out["gap_SC"] = out["election_share_SC"] - out["secc_share_SC"]
    out["gap_ST"] = out["election_share_ST"] - out["secc_share_ST"]
    return out.sort_values("secc_n", ascending=False).reset_index(drop=True)


def reweighted_shares(frame: pd.DataFrame, tokens: list[str]) -> pd.DataFrame:
    w = pd.crosstab(
        frame["surname"], frame["category"], values=frame["weight"], aggfunc="sum"
    ).reindex(index=tokens, columns=source.CATEGORIES, fill_value=0.0)
    return w.div(w.sum(axis=1), axis=0)


def main() -> None:
    TAB.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    loaded = source.load()
    if loaded is None:
        print(f"skipped: one of {list(source.source_paths().values())} not present")
        return
    frame, dropped = loaded

    # The father/husband name exists only in the 2020-22 contestant file, so
    # the three cues are compared on that subset, re-weighted on its own mix.
    contest = frame[frame["father_surname"].notna()].copy()
    contest["weight"] = source.reweight(contest["category"])
    contest = contest.reset_index(drop=True)

    # A third of names are one word, so for them the "surname" is the given
    # name. The two-word subset shows what a written surname is worth.
    named = frame[frame["tokens_in_name"] >= 2].copy()
    named["weight"] = source.reweight(named["category"])
    named = named.reset_index(drop=True)

    rows = []
    for weighted in (False, True):
        r = source.score(frame, "surname", weighted=weighted)
        rows.append({"sample": "pooled", **r})
        r = source.score(frame, "surname", fold=None, weighted=weighted)
        rows.append({"sample": "pooled", **r})
        r = source.score(named, "surname", weighted=weighted)
        rows.append({"sample": "two_or_more_tokens", **r})
        for cue in ("surname", "father_surname", "both"):
            r = source.score(contest, cue, weighted=weighted)
            rows.append({"sample": "sarpanch_2020", **r})
    for female, g in contest.groupby("female"):
        g = g.reset_index(drop=True)
        label = "sarpanch_2020_women" if female else "sarpanch_2020_men"
        for cue in ("surname", "father_surname", "both"):
            rows.append({"sample": label, **source.score(g, cue)})
    for name, g in frame.groupby("source"):
        if name == "sarpanch_2020":
            continue
        g = g.reset_index(drop=True)
        rows.append({"sample": name, **source.score(g, "surname")})
    scores = pd.DataFrame(rows)
    scores.to_csv(TAB / "scores.csv", index=False)

    split = pd.concat(
        [source.by_category(frame), source.by_category(frame, weighted=True)]
    )
    split.to_csv(TAB / "by_category.csv", index=False)

    auc_rows = []
    for label, target, subset in (
        ("SC vs rest", ["SC"], frame),
        ("ST vs rest", ["ST"], frame),
        (
            "OBC vs General",
            ["OBC"],
            frame[frame["category"].isin(["OBC", "General"])].reset_index(drop=True),
        ),
    ):
        for cue, sub in (("surname", subset),):
            p, pos = source.held_out_probability(sub, cue, target)
            auc_rows.append(
                {
                    "contrast": label,
                    "cue": cue,
                    "people": int(len(sub)),
                    "positives": int(pos.sum()),
                    "ranks_positive_higher": ranks_above(
                        p, pos.astype(float), (~pos).astype(float)
                    ),
                }
            )
    contest_ob = contest[contest["category"].isin(["OBC", "General"])].reset_index(
        drop=True
    )
    for label, target, sub in (
        ("SC vs rest", ["SC"], contest),
        ("ST vs rest", ["ST"], contest),
        ("OBC vs General", ["OBC"], contest_ob),
    ):
        for cue in ("surname", "father_surname"):
            p, pos = source.held_out_probability(sub, cue, target)
            auc_rows.append(
                {
                    "contrast": label,
                    "cue": f"{cue} (sarpanch_2020)",
                    "people": int(len(sub)),
                    "positives": int(pos.sum()),
                    "ranks_positive_higher": ranks_above(
                        p, pos.astype(float), (~pos).astype(float)
                    ),
                }
            )
    auc = pd.DataFrame(auc_rows)
    auc.to_csv(TAB / "ranking.csv", index=False)

    tokens = token_table(frame)
    tokens.to_csv(TAB / "tokens.csv", index=False)

    top = tokens.head(TOP_N).copy()
    top["share_of_candidates"] = top["n"] / len(frame)
    top.to_csv(TAB / "commonest_tokens.csv", index=False)

    secc = outkast_rajasthan()
    agreement = {}
    if secc is not None:
        both = compare_outkast(tokens, secc)
        rw = reweighted_shares(frame, both["token"].tolist())
        both["election_share_SC_reweighted"] = rw["SC"].to_numpy()
        both["election_share_ST_reweighted"] = rw["ST"].to_numpy()
        both.to_csv(TAB / "outkast_compare.csv", index=False)
        agreement = {
            "tokens_in_both": int(len(both)),
            "secc_tokens": int(len(secc)),
            "corr_SC_raw": float(both["election_share_SC"].corr(both["secc_share_SC"])),
            "corr_ST_raw": float(both["election_share_ST"].corr(both["secc_share_ST"])),
            "corr_SC_reweighted": float(
                both["election_share_SC_reweighted"].corr(both["secc_share_SC"])
            ),
            "corr_ST_reweighted": float(
                both["election_share_ST_reweighted"].corr(both["secc_share_ST"])
            ),
            "disagree_by_more_than_20_points": both[
                (both["gap_SC"].abs() > 0.2) | (both["gap_ST"].abs() > 0.2)
            ]["token"].tolist(),
        }

    det = tokens[tokens["tier"] == "deterministic"]
    tiers = tokens["tier"].value_counts().to_dict()
    tier_people = tokens.groupby("tier")["n"].sum().to_dict()
    by_source = frame["source"].value_counts().to_dict()
    sc_ = scores.set_index(["sample", "cue", "fold", "weighting"]).sort_index()

    def s(sample, cue, fold, weighting, col="mistakes_per_100"):
        return float(sc_.loc[(sample, cue, fold, weighting), col])

    summary = {
        "rows": int(len(frame)),
        "by_source": by_source,
        "dropped": dropped,
        "districts": int(frame["district"].nunique()),
        "female_share": float(frame["female"].mean()),
        "single_token_name_share": float((frame["tokens_in_name"] < 2).mean()),
        "devanagari_name_share": float(frame["devanagari_name"].mean()),
        "devanagari_surname_left_share": float(frame["devanagari_surname"].mean()),
        "category_share_raw": frame["category"].value_counts(normalize=True).to_dict(),
        "category_share_assumed": source.RAJASTHAN_SHARES,
        "contest_category_share_raw": contest["category"]
        .value_counts(normalize=True)
        .to_dict(),
        "headline": {
            "raw": {
                "blind": s("pooled", "surname", "district", "raw", "blind_per_100"),
                "surname": s("pooled", "surname", "district", "raw"),
                "surname_self_loo": s("pooled", "surname", "self", "raw"),
                "surname_named": s("two_or_more_tokens", "surname", "district", "raw"),
                "blind_named": s(
                    "two_or_more_tokens", "surname", "district", "raw", "blind_per_100"
                ),
                "surname_contest": s("sarpanch_2020", "surname", "district", "raw"),
                "father_contest": s(
                    "sarpanch_2020", "father_surname", "district", "raw"
                ),
                "both_contest": s("sarpanch_2020", "both", "district", "raw"),
                "blind_contest": s(
                    "sarpanch_2020", "surname", "district", "raw", "blind_per_100"
                ),
            },
            "rajasthan": {
                "blind": s(
                    "pooled", "surname", "district", "rajasthan", "blind_per_100"
                ),
                "surname": s("pooled", "surname", "district", "rajasthan"),
                "surname_self_loo": s("pooled", "surname", "self", "rajasthan"),
                "surname_named": s(
                    "two_or_more_tokens", "surname", "district", "rajasthan"
                ),
                "blind_named": s(
                    "two_or_more_tokens",
                    "surname",
                    "district",
                    "rajasthan",
                    "blind_per_100",
                ),
                "surname_contest": s(
                    "sarpanch_2020", "surname", "district", "rajasthan"
                ),
                "father_contest": s(
                    "sarpanch_2020", "father_surname", "district", "rajasthan"
                ),
                "both_contest": s("sarpanch_2020", "both", "district", "rajasthan"),
                "blind_contest": s(
                    "sarpanch_2020",
                    "surname",
                    "district",
                    "rajasthan",
                    "blind_per_100",
                ),
            },
        },
        "ranking": {
            f"{r.contrast} | {r.cue}": float(r.ranks_positive_higher)
            for r in auc.itertuples()
        },
        "tokens": {
            "min_n": MIN_TOKEN,
            "count": int(len(tokens)),
            "people_covered_share": float(tokens["n"].sum() / len(frame)),
            "tiers": tiers,
            "tier_people_share": {
                k: float(v / len(frame)) for k, v in tier_people.items()
            },
            "deterministic": int(len(det)),
            "deterministic_jati_names": int(det["is_jati_name"].sum()),
            "deterministic_clan_names": int(det["is_clan_name"].sum()),
            "deterministic_neither": det[~det["is_jati_name"] & ~det["is_clan_name"]][
                "token"
            ].tolist(),
            "abstain_given_names": tokens[tokens["tier"] == "abstain"]["token"]
            .head(12)
            .tolist(),
            "deterministic_by_category": det["majority"].value_counts().to_dict(),
            "flip_under_reweighting": tokens[
                tokens["majority"] != tokens["majority_reweighted"]
            ]["token"].tolist(),
        },
        "by_category": {
            w: g.set_index("category")[["share", "wrong_per_100"]].to_dict("index")
            for w, g in split.groupby("weighting")
        },
        "outkast": agreement,
        "top": top.set_index("token")[
            ["n", "share_SC", "share_ST", "share_OBC", "share_General", "tier"]
        ].to_dict("index"),
    }
    summary["gap_closed_share"] = {
        w: float(100 * (h["blind"] - h["surname"]) / h["blind"])
        for w, h in summary["headline"].items()
    }
    (TAB / "summary.json").write_text(json.dumps(summary, indent=2, default=float))

    import figures

    figures.by_cue(scores, FIG / "by_cue.png")
    figures.purity_vs_frequency(tokens, summary, FIG / "tokens.png")
    print(f"wrote {TAB} and {FIG}")


if __name__ == "__main__":
    main()
