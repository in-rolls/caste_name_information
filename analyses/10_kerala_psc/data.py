"""Kerala, where the question often has no object.

The rest of this repo asks what a last name gives away about caste. In Kerala
that question frequently has nothing to land on. A name here is typically a
given name followed by initials standing for a father and a house:
`KALPANA A`, `SHYLAJA E T`, `SHAHUL HAMEED C K`. **78% of last tokens are a
single letter**, and none of the first tokens are.

The source is 1.4M Kerala Public Service Commission select lists, the largest
caste-linked name file this project has. Two things about them shape everything
below.

**Community is a reservation category, not observed caste.** A forward caste has
none to claim, so `MENON` and `NAMBOOTHIRI` appear zero times and `NAIR` 794. The
17% of rows with no community are close to, but not the same as, forward caste,
and they are excluded rather than assumed.

**Two of the buckets are religious as much as caste.** Kerala reserves for
Muslim and for Latin Catholic and SIUC communities. Scoring them would make
religion a predictor, which this repo does not do, so the scored set is the
caste-only buckets and the dropped share is reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from last_name_basis.siblings import repo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from last_name_basis.scoring import ranks_above  # noqa: E402

HERE = Path(__file__).resolve().parent
CASTE_BUCKETS = {"Scheduled Caste", "Scheduled Tribe", "OBC or other Hindu", "Forward"}


def source_path() -> Path:
    return (
        repo("pranaam")
        / "scripts/data-acquisition/kerala_psc/raw/psc_candidates.parquet"
    )


def bucket(value: str) -> str:
    """Collapse 12,105 community strings into the categories that can be scored.

    The prefixes carry the structure: `SC-PULAYA`, `E-EZHAVA`, `M-MAPPILA`.
    """
    if not value:
        return "no community given"
    if value.startswith("SC"):
        return "Scheduled Caste"
    if value.startswith("ST"):
        return "Scheduled Tribe"
    if value.startswith("M-") or "MUSLIM" in value or "MAPPILA" in value:
        return "Muslim"
    if value.startswith(("LC", "SIUC")) or "CHRIST" in value or "LATIN" in value:
        return "Christian"
    if "FORWARD" in value:
        return "Forward"
    return "OBC or other Hindu"


def load() -> pd.DataFrame | None:
    """Candidates with a bucketed community and the three cues to be compared."""
    path = source_path()
    if not path.exists():
        return None
    d = pd.read_parquet(path)
    community = d["community"].fillna("").str.strip().str.upper()
    d["bucket"] = community.map(bucket)

    tokens = d["name"].fillna("").str.strip().str.upper().str.split()
    d["tokens"] = tokens
    d["last_token"] = tokens.str[-1]
    d["given_name"] = tokens.str[0]
    # A written surname is a non-initial token that is not the given name.
    # Searching the whole name backwards does not do this: for `KALPANA A` it
    # skips the initial and returns KALPANA, which is the given name, and the
    # cue then scores the same as the given name because it is the given name.
    d["written_surname"] = tokens.map(
        lambda t: (
            next((w for w in reversed(t[1:]) if len(w) > 1), None)
            if isinstance(t, list) and len(t) > 1
            else None
        )
    )
    return d[d["last_token"].notna() & d["given_name"].notna()].reset_index(drop=True)


def name_shape(d: pd.DataFrame) -> dict:
    """How often a Kerala name has a surname to read at all."""
    last_is_initial = d["last_token"].str.len() == 1
    return {
        "candidates": int(len(d)),
        "last_token_is_a_single_letter": float(last_is_initial.mean()),
        "first_token_is_a_single_letter": float(
            (d["given_name"].str.len() == 1).mean()
        ),
        "has_a_written_surname": float(d["written_surname"].notna().mean()),
        "median_tokens": float(d["tokens"].str.len().median()),
    }


def scored_set(d: pd.DataFrame) -> pd.DataFrame:
    """Rows whose community is a caste category rather than a religious one."""
    return d[d["bucket"].isin(CASTE_BUCKETS)].reset_index(drop=True)


def discrimination(d: pd.DataFrame, cue: str) -> dict:
    """How well a cue separates Scheduled Caste candidates from the rest.

    The same statistic analyses 01 and 07 report, from the same routine, so a
    Kerala figure can be set beside a national or a state one.
    """
    frame = d[d[cue].notna()]
    if frame.empty:
        return {"cue": cue, "candidates": 0, "ranks_sc_higher": float("nan")}
    is_sc = (frame["bucket"] == "Scheduled Caste").to_numpy()
    counts = (
        pd.DataFrame({"cue": frame[cue].to_numpy(), "sc": is_sc})
        .groupby("cue")["sc"]
        .agg(["sum", "count"])
    )
    positive = counts["sum"].to_numpy(float)
    negative = (counts["count"] - counts["sum"]).to_numpy(float)
    total = positive + negative
    share_sc = np.divide(positive, total, out=np.zeros_like(positive), where=total > 0)
    return {
        "cue": cue,
        "candidates": int(len(frame)),
        "share_of_all": float(len(frame) / len(d)),
        "distinct_values": int(len(counts)),
        "sc_share": float(is_sc.mean()),
        "ranks_sc_higher": ranks_above(share_sc, positive, negative),
    }
