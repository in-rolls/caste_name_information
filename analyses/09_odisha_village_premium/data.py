"""Does the village premium travel outside Bihar?

Bihar's land records give this repo its strongest single result: across 141
jatis a surname alone leaves 47 mistakes per 100 and a surname plus a village
leaves 17. Nothing established whether that 30-point collapse is a fact about
surnames and villages or a fact about Bihar.

The Odisha Record of Rights carries a jati and a village for every tenant, so it
can answer the same question with the same protocol. Two limits govern how far
the answer travels, and both are printed beside every number rather than left to
a footnote:

**This is one district, not a state.** The scrape has reached district 24,
Gajapati, and no further. Gajapati is small, heavily Adivasi and on the Andhra
border; its castes are not Odisha's. Nothing here may be labelled "Odisha".

**Each village is a sample.** The fetch caps khatiyans per village, and the cap
has changed between runs, so villages accumulate rather than being censused. The
realised distribution is measured from the data rather than assumed from a
command line, because a constant written here goes stale the moment the scrape
is restarted with a different flag. Village cells are small either way, so
leave-one-out is not optional.

The surname is the **last** token, which is measured rather than assumed. A
token appearing in both a tenant's name and their father's or husband's is an
inherited one, and in Gajapati that token is last 80% of the time, first 11%.
Maharashtra fails the same test in the other direction (analysis 04), so the
test is run per state and never carried over.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TENANTS = HERE / "out/tab/tenants.parquet"

_SPACE = re.compile(r"\s+")


def normalise(value: str) -> str:
    """Strip, collapse whitespace, drop a parenthesised gloss.

    The parser keeps glosses like `କୈବର୍ତ୍ତ (ମାଛଧରା)`, which are the same jati
    written two ways. Merging them is the Odia equivalent of the sud/sood
    problem, and the merge list is published beside the results.
    """
    if not isinstance(value, str):
        return ""
    value = re.sub(r"\([^)]*\)", " ", value)
    return _SPACE.sub(" ", value).strip()


def _github() -> Path:
    return Path(os.environ.get("GITHUB_DIR", Path.home() / "Documents/GitHub"))


def checkpoints() -> Path:
    """Where the Odisha scraper and its checkpoints live.

    One path, deliberately. The scraper briefly existed twice -- once in
    pranaam and once extracted -- and the fallback chain that tolerated it
    resolved to a copy holding the parser but no data. Discovery then failed,
    `load` returned the cached table, and the analysis reported one district
    for weeks without raising. A missing path is now an error.
    """
    return _github() / "ror_odisha_2026"


def materialise() -> None:
    """Parse the scraper's checkpoints into this repo's own table.

    The parser is imported rather than copied, so a fix there reaches here.
    Nothing is written back into that repository: a scrape runs in it, and its
    own `tenants.parquet` is a build artefact of a process this analysis does
    not own.

    Raises:
        FileNotFoundError: If the scraper or its checkpoints are absent.
        ValueError: If the checkpoint tree holds no readable record.
    """
    root = checkpoints()
    source = root / "parse_ror.py"
    if not source.exists():
        raise FileNotFoundError(f"no parse_ror.py under {root}")
    if not (root / "raw" / "ror").is_dir():
        raise FileNotFoundError(f"no fetched checkpoints under {root / 'raw/ror'}")
    spec = importlib.util.spec_from_file_location("parse_ror", source)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["parse_ror"] = module
    spec.loader.exec_module(module)
    # Upstream discovery is used rather than reimplemented here: its glob now
    # carries the tahsil level the fetcher writes, and it salvages the
    # checkpoint a live scrape leaves truncated.
    records = module.read_checkpoints(root / "raw" / "ror")
    if not records:
        raise ValueError(f"no readable records under {root / 'raw/ror'}")
    TENANTS.parent.mkdir(parents=True, exist_ok=True)
    module.build(records).to_parquet(TENANTS, index=False)


def load() -> pd.DataFrame:
    """Tenant rows with a jati, a village and a surname.

    Returns:
        One row per tenant carrying a jati, a village key and a surname.
    """
    if not TENANTS.exists():
        materialise()
    d = pd.read_parquet(TENANTS)
    d["jati"] = d["caste_or"].map(normalise)
    d["name"] = d["name_or"].map(normalise)
    d["village"] = (
        d["district_code"].astype(str)
        + "|"
        + d["tahsil_code"].astype(str)
        + "|"
        + d["village_code"].astype(str)
    )
    tokens = d["name"].str.split()
    d["surname"] = tokens.map(lambda t: t[-1] if isinstance(t, list) and t else "")
    keep = d["jati"].ne("") & d["surname"].ne("")
    out = d.loc[keep].reset_index(drop=True)
    out.attrs["districts"] = sorted(out["district_name"].astype(str).unique())
    out.attrs["sampling"] = village_sampling(out)
    return out


def village_sampling(d: pd.DataFrame) -> dict:
    """How many khatiyans each village actually contributed.

    Not the `--per-village` flag: that is a per-run cap, villages accumulate
    across runs, and the flag has changed between runs. It is now effectively
    off, so a finished village is censused rather than sampled -- but a village
    the scrape is still working through is not, and only the realised
    distribution can tell the two apart.
    """
    per = d.groupby(["district_code", "tahsil_code", "village_code"])[
        "khatiyan"
    ].nunique()
    return {
        "villages": int(len(per)),
        "khatiyans_per_village_median": float(per.median()),
        "khatiyans_per_village_mean": float(per.mean()),
        "khatiyans_per_village_max": int(per.max()),
    }


def surname_position(d: pd.DataFrame) -> dict:
    """Where the inherited token sits, measured from the relative's name.

    Run before any scoring. A last-token rule is an assumption, and analysis 04
    showed it is false in Maharashtra; carrying it into a new state unchecked is
    how that defect happened the first time.
    """
    frame = d[d["relative_name_or"].fillna("").str.strip().ne("")]
    counts = {"first": 0, "middle": 0, "last": 0}
    shared = 0
    for name, relative in zip(frame["name"], frame["relative_name_or"]):
        tokens = name.split()
        relatives = set(normalise(relative).split())
        if len(tokens) < 2:
            continue
        hits = [i for i, t in enumerate(tokens) if t in relatives]
        if not hits:
            continue
        shared += 1
        for i in hits:
            where = "first" if i == 0 else "last" if i == len(tokens) - 1 else "middle"
            counts[where] += 1
    total = sum(counts.values()) or 1
    return {
        "rows_with_a_relative": int(len(frame)),
        "rows_sharing_a_token": shared,
        "share_sharing_a_token": float(shared / max(len(frame), 1)),
        "positions": {k: v / total for k, v in counts.items()},
        "surname_is": max(counts, key=lambda k: counts[k]),
    }


def score(d: pd.DataFrame, keys: list[str], group: str = "jati") -> dict:
    """Leave-one-out mistakes per 100 guessing `group` from `keys`.

    Identical in form to the Bihar ladder, so the two are comparable: a
    household never votes for its own cell, and one whose cell is then empty
    falls back to the commonest group overall rather than being excused.
    """
    groups = sorted(d[group].unique())
    index = {g: i for i, g in enumerate(groups)}
    truth = d[group].map(index).to_numpy()
    # `.agg("|".join, axis=1)` is a Python call per row, which is most of the
    # runtime at five million of them. `str.cat` builds the same strings in one
    # vectorised pass.
    if len(keys) > 1:
        first, *rest = keys
        cell = d[first].astype(str).str.cat([d[k].astype(str) for k in rest], sep="|")
    else:
        cell = d[keys[0]]
    cell_code, _ = pd.factorize(cell, sort=True)

    # The dense (rows x groups) tally the first version built is 248 GB at
    # Odisha's size, so the leave-one-out winner is derived from each cell's
    # two leading groups instead. Removing a row can only demote its own
    # group by one, so the winner is the cell's top group unless the row
    # belongs to it, and then it is whichever of the top two survives. Ties
    # go to the lowest group index, which is what argmax did.
    tally = pd.DataFrame({"cell": cell_code, "grp": truth}).value_counts()
    tally = tally.reset_index(name="n").sort_values(
        ["cell", "n", "grp"], ascending=[True, False, True], kind="stable"
    )
    lead = tally.groupby("cell", sort=True).head(2)
    first = lead.groupby("cell", sort=True).nth(0)
    second = lead.groupby("cell", sort=True).nth(1)

    n_cells = cell_code.max() + 1
    top_group = np.full(n_cells, -1, dtype=np.int64)
    top_count = np.zeros(n_cells, dtype=np.int64)
    next_group = np.full(n_cells, -1, dtype=np.int64)
    next_count = np.zeros(n_cells, dtype=np.int64)
    top_group[first["cell"].to_numpy()] = first["grp"].to_numpy()
    top_count[first["cell"].to_numpy()] = first["n"].to_numpy()
    next_group[second["cell"].to_numpy()] = second["grp"].to_numpy()
    next_count[second["cell"].to_numpy()] = second["n"].to_numpy()

    size = np.bincount(cell_code, minlength=n_cells)
    row_top, row_top_n = top_group[cell_code], top_count[cell_code]
    row_next, row_next_n = next_group[cell_code], next_count[cell_code]

    # The row is removed from its own cell, so its group loses one vote.
    demoted = row_top_n - 1
    runner_up = np.where(row_next < 0, -1, row_next)
    contested = np.where(
        demoted > row_next_n,
        row_top,
        np.where(demoted == row_next_n, np.minimum(row_top, runner_up), runner_up),
    )
    guess = np.where(truth == row_top, contested, row_top)

    prior = np.bincount(truth, minlength=len(groups))
    fallback = int(prior.argmax())
    resolved = size[cell_code] > 1
    guess = np.where(resolved, guess, fallback)
    counts_shape = n_cells

    return {
        "cue": " + ".join(keys),
        "households": int(len(d)),
        "groups": len(groups),
        "cells": int(counts_shape),
        "mistakes_per_100": float(100 * (guess != truth).mean()),
        "share_resolved": float(100 * resolved.mean()),
    }


def blind(d: pd.DataFrame, group: str = "jati") -> float:
    counts = d[group].value_counts()
    return float(100 * (1 - counts.max() / counts.sum()))
