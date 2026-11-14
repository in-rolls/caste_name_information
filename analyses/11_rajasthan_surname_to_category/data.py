"""What a surname reveals about caste category in Rajasthan.

SECC records Scheduled Caste, Scheduled Tribe, or neither, so nothing built on
it can tell an OBC from a General person, and in Rajasthan those two are about
seven people in ten. Panchayat election records can. Every candidate for a
sarpanch or ward seat declares a category -- SC, ST, OBC or General -- and the
State Election Commission publishes it beside the candidate's name and the name
of their father or husband.

Five files from the release pinned in data_sources.json:

    ContestingSarpanch.csv.gz  68,202 sarpanch candidates, 2020-22, with a
                               father/husband name and a district
    WarnWinningPanch.csv.gz    110,296 ward panch winners, same elections
    sarpanch_{2005,2010,2015}  ~28,000 sarpanch winners from earlier rounds

Two things about them govern how the numbers may be read, and both belong in
the first paragraph of anything written from this:

  * The category is **self-declared**, to stand for a seat. It is what the
    candidate claims, checked to the extent a returning officer checks it.
  * The sample is **shaped by reservation**. A seat reserved for Scheduled
    Tribes draws only ST candidates, and Rajasthan reserves seats in proportion
    to local ST population, so the tribal south sends whole slates of ST
    candidates. ST is 27% of candidates against 13.5% of the state. The raw
    base rate is a fact about the quota, not about Rajasthan, which is why
    every score is reported twice: on the sample as it comes, and re-weighted
    so the four categories sit at the state's own shares.

Rajasthan's OBC/General split is not in any census. The 17.8% SC and 13.5% ST
are Census 2011; the remaining 68.7% is split OBC:General as 50:19, the ratio
the state's backward-class commission and the Mandal-era estimates put it at.
That is an assumption and the note says so.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pooch

CATEGORIES = ["SC", "ST", "OBC", "General"]

# Census 2011 gives SC and ST. OBC and General are not censused anywhere; the
# 50:19 split is the widely cited estimate, normalised to what the census
# leaves over.
_REST = 1 - 0.178 - 0.135
RAJASTHAN_SHARES = {
    "SC": 0.178,
    "ST": 0.135,
    "OBC": _REST * 50 / 69,
    "General": _REST * 19 / 69,
}

_CATEGORY_ALIAS = {"GEN": "General", "GENERAL": "General"}

# The commonest Devanagari last tokens, mapped to the Latin spelling the same
# name takes elsewhere in the file. Everything not listed stays as written and
# forms its own cell; the share left over is reported.
DEVANAGARI_TOKENS = {
    "देवी": "devi",
    "सिंह": "singh",
    "सिह": "singh",
    "राम": "ram",
    "कुमार": "kumar",
    "कौर": "kaur",
    "बाई": "bai",
    "कंवर": "kanwar",
    "कँवर": "kanwar",
    "लाल": "lal",
    "कुमारी": "kumari",
    "मीणा": "meena",
    "खां": "khan",
    "खान": "khan",
    "मेघवाल": "meghwal",
    "शर्मा": "sharma",
    "प्रसाद": "prasad",
    "बानो": "bano",
    "चौधरी": "choudhary",
    "गुर्जर": "gurjar",
    "बैरवा": "bairwa",
    "जाट": "jat",
    "सैनी": "saini",
    "यादव": "yadav",
    "प्रकाश": "prakash",
}

_DISTRICT_FIX = {
    "BANSW ARA": "BANSWARA",
    "P ALI": "PALI",
    "S.MADHOPUR": "S. MADHOPUR",
    "DUNGERPUR": "DUNGARPUR",
    "ANUMANGAR": "HANUMANGARH",
    "BHARA TPUR": "BHARATPUR",
    "KOT A": "KOTA",
    "PRA T APGARH": "PRATAPGARH",
}

_DEVANAGARI = "\u0900-\u097f"
_RELATION = re.compile(r"\b[swdSWD]\s*/\s*[oO0]\b")
_PARENS = re.compile(r"\([^)]*\)")
_NOT_NAME = re.compile(rf"[^\w\s{_DEVANAGARI}]")
_INVISIBLE = re.compile("[\u200b-\u200f]")


def source_paths() -> dict[str, Path]:
    """Fetch verified release files into the shared INDIA_DATA_HOME cache."""
    manifest = json.loads(Path(__file__).with_name("data_sources.json").read_text())
    cache = Path(os.environ.get("INDIA_DATA_HOME", "~/data")).expanduser()
    paths = {}
    for name, spec in manifest.items():
        relative = Path(spec["path"])
        paths[name] = Path(
            pooch.retrieve(
                url=(
                    f"https://raw.githubusercontent.com/in-rolls/{spec['provider']}/"
                    f"{spec['ref']}/{spec['path']}"
                ),
                known_hash="sha256:" + spec["sha256"],
                path=cache / spec["provider"] / spec["ref"] / relative.parent,
                fname=relative.name,
            )
        )
    return paths


def normalise_category(raw: pd.Series) -> pd.DataFrame:
    """Four labels and a sex flag from the dozen spellings the files use.

    `OBC (Woman)`, `OBCW`, `OBC W` and `ST(Woman)` all mean an OBC or ST
    candidate standing for a seat reserved for a woman of that category. The
    suffix goes into `female`; the stem is mapped to SC / ST / OBC / General
    and anything else becomes an empty string for the caller to drop.
    """
    s = raw.fillna("").astype(str).str.strip().str.upper()
    female = s.str.contains(r"\(\s*WOMAN\s*\)|\bW$|[A-Z]W$", regex=True)
    stem = (
        s.str.replace(r"\(\s*WOMAN\s*\)", "", regex=True)
        .str.replace(r"\s*W$", "", regex=True)
        .str.strip()
    )
    label = stem.map(lambda c: _CATEGORY_ALIAS.get(c, c))
    label = label.where(label.isin(CATEGORIES), "")
    return pd.DataFrame({"category": label, "female": female})


def surname_tokens(names: pd.Series) -> pd.Series:
    """Last token of the person's own name, lowercased, punctuation gone.

    The files write relatives into the name field -- `GHASIRAM S/O SURJARAM`,
    `DOLI / HIMMAT SINGH`, `sohni (sona devi )` -- so the name is cut at the
    first slash or parenthesis before the last token is taken. Single letters
    and digits are skipped, as in analysis 08. Devanagari survives the
    character class and is mapped to Latin where the map above knows it.
    """
    s = names.fillna("").astype(str)
    s = s.map(lambda v: _INVISIBLE.sub("", v))
    s = s.str.replace(_RELATION, "/", regex=True)
    s = s.str.split("/").str[0]
    s = s.str.replace(_PARENS, " ", regex=True)
    s = s.str.replace(_NOT_NAME, " ", regex=True).str.lower()
    tokens = s.str.split()

    def last(t):
        for w in reversed(t):
            if len(w) > 1 and not w.isdigit():
                return DEVANAGARI_TOKENS.get(w, w)
        return None

    return tokens.map(last)


def name_length(names: pd.Series) -> pd.Series:
    """How many tokens the person's own name has, after the same cleaning.

    A third of candidates are recorded by one word, `SUNITA` or `KAMLA`, and
    for them the "surname" the last-token rule reads is the given name.
    """
    s = names.fillna("").astype(str)
    s = s.map(lambda v: _INVISIBLE.sub("", v))
    s = s.str.replace(_RELATION, "/", regex=True).str.split("/").str[0]
    s = s.str.replace(_PARENS, " ", regex=True)
    s = s.str.replace(_NOT_NAME, " ", regex=True)
    return s.str.split().map(lambda t: sum(len(w) > 1 and not w.isdigit() for w in t))


def _district(s: pd.Series) -> pd.Series:
    d = s.fillna("").astype(str).str.strip().str.upper()
    return d.map(lambda v: _DISTRICT_FIX.get(v, v))


def _read(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def load() -> tuple[pd.DataFrame, dict] | None:
    """One row per candidate-election, across all five files.

    Returns the pooled frame and a dict of what was dropped, per source. The
    father/husband surname exists only for the 2020-22 sarpanch contestants;
    elsewhere it is missing.
    """
    paths = source_paths()
    if not all(p.exists() for p in paths.values()):
        return None

    parts, dropped = [], {}
    d = _read(paths["sarpanch_2020"])
    parts.append(
        pd.DataFrame(
            {
                "source": "sarpanch_2020",
                "district": _district(d["District"]),
                "name": d["NameOfContestingCandidate"],
                "father": d["FatherHusbandOfContestingCandidate"],
                "raw_category": d["CategoryOfCandidate"],
                "seat": d["CategoryOfGramPanchayat"],
            }
        )
    )
    d = _read(paths["ward_2020"])
    parts.append(
        pd.DataFrame(
            {
                "source": "ward_2020",
                "district": _district(d["District"]),
                "name": d["NameOfCandidate"],
                "father": None,
                "raw_category": d["CategoryOfWinningCandidate"],
                "seat": d["CategoryOfWard"],
            }
        )
    )
    for year in (2005, 2010, 2015):
        d = _read(paths[f"sarpanch_{year}"])
        parts.append(
            pd.DataFrame(
                {
                    "source": f"sarpanch_{year}",
                    "district": _district(d["dist_name"]),
                    "name": d["name"],
                    "father": None,
                    "raw_category": d["category"],
                    "seat": d["reservation"],
                }
            )
        )
    frame = pd.concat(parts, ignore_index=True)

    cat = normalise_category(frame["raw_category"])
    frame["category"] = cat["category"]
    frame["female"] = cat["female"]
    bad = frame["category"] == ""
    dropped["unmappable_category"] = (
        frame.loc[bad, "raw_category"].str.strip().value_counts().to_dict()
    )
    frame = frame[~bad].copy()

    frame["surname"] = surname_tokens(frame["name"])
    frame["tokens_in_name"] = name_length(frame["name"])
    frame["father_surname"] = surname_tokens(frame["father"])
    no_surname = frame["surname"].isna()
    dropped["no_surname"] = int(no_surname.sum())
    frame = frame[~no_surname].copy()

    frame["devanagari_name"] = frame["name"].str.contains(rf"[{_DEVANAGARI}]")
    frame["devanagari_surname"] = frame["surname"].str.contains(rf"[{_DEVANAGARI}]")
    frame["pair"] = np.where(
        frame["father_surname"].notna(),
        frame["surname"] + "|" + frame["father_surname"].fillna(""),
        None,
    )
    frame["weight"] = reweight(frame["category"])
    return frame.reset_index(drop=True), dropped


def reweight(category: pd.Series) -> np.ndarray:
    """Per-row weights that move the sample's four shares to Rajasthan's.

    A row of a category the quota over-samples gets a weight below one, one it
    under-samples a weight above. The weights sum to the number of rows, so a
    weighted count still reads as people.
    """
    share = category.value_counts(normalize=True)
    w = category.map({c: RAJASTHAN_SHARES[c] / share[c] for c in CATEGORIES})
    return (w * len(category) / w.sum()).to_numpy(float)


def _one_hot(frame: pd.DataFrame, weight: np.ndarray) -> np.ndarray:
    truth = frame["category"].map({c: i for i, c in enumerate(CATEGORIES)})
    own = np.zeros((len(frame), len(CATEGORIES)))
    own[np.arange(len(frame)), truth.to_numpy()] = weight
    return own


def held_out_counts(
    frame: pd.DataFrame, key: str, fold: str | None, weight: np.ndarray
) -> np.ndarray:
    """For each row, the weighted category counts of its `key` cell, fitted
    on rows outside its fold.

    `fold` is a column name, and the counts exclude every row sharing the
    fold value -- leave-one-district-out when it is `district`. `fold=None`
    excludes only the row itself, which is ordinary leave-one-out. Rows with
    a missing key get a zero row, which the caller treats as unresolved.
    """
    have = frame[key].notna().to_numpy()
    out = np.zeros((len(frame), len(CATEGORIES)))
    sub = frame[have]
    w = weight[have]
    own = _one_hot(sub, w)

    total = (
        pd.DataFrame(own, columns=CATEGORIES, index=sub[key].to_numpy())
        .groupby(level=0)
        .sum()
    )
    cell = total.reindex(sub[key]).to_numpy()
    if fold is None:
        out[have] = cell - own
        return out
    idx = pd.MultiIndex.from_arrays([sub[fold].to_numpy(), sub[key].to_numpy()])
    per_fold = (
        pd.DataFrame(own, columns=CATEGORIES, index=idx).groupby(level=[0, 1]).sum()
    )
    out[have] = cell - per_fold.reindex(idx).to_numpy()
    return out


def held_out_prior(frame: pd.DataFrame, fold: str | None, weight: np.ndarray):
    """The category totals a guesser would see with this row's fold held out."""
    own = _one_hot(frame, weight)
    total = own.sum(axis=0)
    if fold is None:
        return total[None, :] - own
    per_fold = (
        pd.DataFrame(own, columns=CATEGORIES, index=frame[fold].to_numpy())
        .groupby(level=0)
        .sum()
    )
    return total[None, :] - per_fold.reindex(frame[fold]).to_numpy()


def score(
    frame: pd.DataFrame,
    cue: str,
    *,
    fold: str | None = "district",
    weighted: bool = False,
    min_cell: float = 1.0,
) -> dict:
    """Mistakes per hundred guessing the category from `cue`.

    `cue` is `surname`, `father_surname` or `both`. `both` backs off: the
    (surname, father surname) pair if enough other candidates share it, else
    the surname alone, else the blind guess. `min_cell` is how much support
    -- weighted people -- a cell needs before it is used instead of the blind
    guess; one, as in analyses 08 and 09.

    Every count is fitted with the row's own district held out (or the row
    itself when `fold=None`), so a jati that lives in one district cannot score
    itself. The blind guess is likewise the largest category among the other
    districts.
    """
    w = frame["weight"].to_numpy() if weighted else np.ones(len(frame))
    truth = frame["category"].map({c: i for i, c in enumerate(CATEGORIES)}).to_numpy()
    prior = held_out_prior(frame, fold, w)
    blind = prior.argmax(axis=1)

    if cue == "both":
        keys = ["pair", "surname"]
        frame = frame[frame["father_surname"].notna()]
    else:
        keys = [cue]
        frame = frame[frame[cue].notna()]
    keep = frame.index.to_numpy()
    w, truth, blind = w[keep], truth[keep], blind[keep]

    guess = blind.copy()
    resolved = np.zeros(len(frame), dtype=bool)
    resolved_by = {}
    for key in reversed(keys):
        counts = held_out_counts(frame, key, fold, w)
        ok = counts.sum(axis=1) >= min_cell
        guess = np.where(ok, counts.argmax(axis=1), guess)
        resolved_by[key] = ok
        resolved |= ok
    share = w / w.sum()
    return {
        "cue": cue,
        "fold": fold or "self",
        "weighting": "rajasthan" if weighted else "raw",
        "people": int(len(frame)),
        "blind_per_100": float(100 * (share * (blind != truth)).sum()),
        "mistakes_per_100": float(100 * (share * (guess != truth)).sum()),
        "share_resolved": float(100 * (share * resolved).sum()),
        **{
            f"share_resolved_by_{k}": float(100 * (share * v).sum())
            for k, v in resolved_by.items()
        },
    }


def by_category(frame: pd.DataFrame, cue: str = "surname", weighted=False):
    """The surname guess, split by the candidate's own category.

    The blind guess names the largest category, so it is right about all of
    that one and wrong about every other; this shows what the surname leaves.
    """
    w = frame["weight"].to_numpy() if weighted else np.ones(len(frame))
    truth = frame["category"].map({c: i for i, c in enumerate(CATEGORIES)}).to_numpy()
    blind = held_out_prior(frame, "district", w).argmax(axis=1)
    counts = held_out_counts(frame, cue, "district", w)
    guess = np.where(counts.sum(axis=1) >= 1, counts.argmax(axis=1), blind)
    rows = []
    for i, c in enumerate(CATEGORIES):
        mine = truth == i
        rows.append(
            {
                "category": c,
                "weighting": "rajasthan" if weighted else "raw",
                "share": float(w[mine].sum() / w.sum()),
                "blind_wrong_per_100": float(
                    100 * (w[mine] * (blind[mine] != i)).sum() / w[mine].sum()
                ),
                "wrong_per_100": float(
                    100 * (w[mine] * (guess[mine] != i)).sum() / w[mine].sum()
                ),
                "candidates": int(mine.sum()),
            }
        )
    return pd.DataFrame(rows)


def held_out_probability(frame: pd.DataFrame, cue: str, target: list[str]):
    """P(category in `target` | cue), fitted with the district held out.

    Rows whose cue no other district has seen get the held-out base rate,
    which is what a guesser with nothing but the prior would assign. Returned
    alongside the row's own membership so the ranking statistic can be taken.
    """
    w = np.ones(len(frame))
    counts = held_out_counts(frame, cue, "district", w)
    prior = held_out_prior(frame, "district", w)
    cols = [CATEGORIES.index(c) for c in target]
    seen = counts.sum(axis=1) > 0
    p = np.where(
        seen,
        counts[:, cols].sum(axis=1) / np.where(seen, counts.sum(axis=1), 1),
        prior[:, cols].sum(axis=1) / prior.sum(axis=1),
    )
    return p, frame["category"].isin(target).to_numpy()
