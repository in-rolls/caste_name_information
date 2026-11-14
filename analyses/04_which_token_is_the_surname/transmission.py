"""Find the family name by asking which token passed between two relatives.

Indian electoral rolls record, for every elector, the name of their father or
husband. A token appearing in both names is a token that moved between two
family members, which is what a family name is. Everything else in the name --
an honorific, a filler, a patronymic, an initial -- does not move.

The search covers every position. Taking the last token is what hid the fact
that Maharashtra writes the surname first: `patil ashwini` with father
`patil ashok`. A last-token scorer reports `ashwini`, a given name, and every
aggregate built on it is about the wrong word.
"""

from __future__ import annotations

import csv
import gzip
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

from last_name_basis.siblings import repo

MIN_TOKEN = 2  # single letters are initials, not names


def roll_path(state: str) -> Path:
    return repo("instate") / f"data/names_{state}.csv.gz"


def shared_tokens(name: str, relative: str) -> list[tuple[int, str]]:
    """Tokens of `name` that also appear in `relative`, with their position."""
    a = name.split()
    b = set(relative.split())
    return [(i, t) for i, t in enumerate(a) if len(t) >= MIN_TOKEN and t in b]


def _position(index: int, length: int) -> str:
    if index == 0:
        return "first"
    if index == length - 1:
        return "last"
    return "middle"


def scan(state: str, limit: int | None = None) -> dict | None:
    """Stream one state's roll and tally, per token, how often it transmits.

    `limit` caps rows read, for a quick look; the full files run to hundreds of
    megabytes gzipped.
    """
    path = roll_path(state)
    if not path.exists():
        return None

    bearers: Counter = Counter()
    transmitted: Counter = Counter()
    positions: dict[str, Counter] = defaultdict(Counter)
    rows_total = rows_usable = rows_shared = 0
    relative_has_surname = 0
    where = Counter()

    with gzip.open(path, "rt") as fh:
        for n_read, row in enumerate(csv.DictReader(fh)):
            if limit and n_read >= limit:
                break
            n = int(row["n_times"])
            rows_total += n
            name = row["english_name"].strip()
            relative = (row.get("father_husband_name") or "").strip()
            tokens = name.split()
            if len(tokens) < 2 or not relative:
                continue
            rows_usable += n
            # A relative recorded as a bare given name has no surname to match
            # against. In Gujarat that is 100% of rows and in Tamil Nadu 96%,
            # so a low score there says nothing about how those places name
            # people -- only about how the roll was written down.
            if len(relative.split()) >= 2:
                relative_has_surname += n

            for token in tokens:
                if len(token) >= MIN_TOKEN:
                    bearers[token] += n

            hits = shared_tokens(name, relative)
            if not hits:
                where["none"] += n
                continue
            rows_shared += n
            # Credit every shared token, not just the first. `ram kumar singh`
            # against `shyam kumar singh` shares both kumar and singh; crediting
            # only the first silently docked every name that happens to follow
            # another inherited one, and read sharma at 0.83 instead of 0.99.
            for index, token in hits:
                transmitted[token] += n
                positions[token][_position(index, len(tokens))] += n
            where[_position(hits[0][0], len(tokens))] += n

    return {
        "state": state,
        "rows_total": rows_total,
        "rows_usable": rows_usable,
        "rows_shared": rows_shared,
        "relative_has_surname": relative_has_surname,
        "bearers": bearers,
        "transmitted": transmitted,
        "positions": positions,
        "where": where,
    }


def by_token(scan_result: dict, min_bearers: int = 2000) -> pd.DataFrame:
    """Per token: how many carry it, and how often it came from a relative."""
    rows = []
    for token, n in scan_result["bearers"].items():
        if n < min_bearers:
            continue
        moved = scan_result["transmitted"].get(token, 0)
        place = scan_result["positions"].get(token)
        rows.append(
            {
                "state": scan_result["state"],
                "token": token,
                "bearers": n,
                "transmitted": moved / n,
                "modal_position": place.most_common(1)[0][0] if place else "none",
            }
        )
    return pd.DataFrame(rows).sort_values("bearers", ascending=False)


def by_state(scan_result: dict) -> dict:
    """One row describing a state's naming convention."""
    usable = max(scan_result["rows_usable"], 1)
    where = scan_result["where"]
    total_placed = sum(v for k, v in where.items() if k != "none") or 1
    return {
        "state": scan_result["state"],
        "rows": scan_result["rows_total"],
        "usable_share": scan_result["rows_usable"] / max(scan_result["rows_total"], 1),
        "relative_has_surname": scan_result["relative_has_surname"] / usable,
        "shared_share": scan_result["rows_shared"] / usable,
        # The score is only interpretable where the relative's name carries a
        # surname at all.
        "method_applies": scan_result["relative_has_surname"] / usable >= 0.5,
        "position_first": where.get("first", 0) / total_placed,
        "position_middle": where.get("middle", 0) / total_placed,
        "position_last": where.get("last", 0) / total_placed,
    }


STATES = [
    "bihar",
    "uttar_pradesh",
    "west_bengal",
    "punjab",
    "maharashtra",
    "gujarat",
    "kerala",
    "tamil_nadu",
    "odisha",
    "rajasthan",
]


def scan_all(
    states: list[str] | None = None,
    limit: int | None = None,
    cache: Path | None = None,
    min_bearers: int = 2000,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Scan several states and return (per-token, per-state) tables.

    A full pass reads hundreds of megabytes per state and takes minutes, so the
    result is cached. Delete the two CSVs to recompute.
    """
    states = states or STATES
    if cache is not None:
        tok_path, state_path = (
            cache / "transmission_by_token.csv",
            cache / "by_state.csv",
        )
        if tok_path.exists() and state_path.exists():
            return pd.read_csv(tok_path), pd.read_csv(state_path)

    tokens, summaries = [], []
    for state in states:
        result = scan(state, limit=limit)
        if result is None or not result["rows_usable"]:
            continue
        tokens.append(by_token(result, min_bearers=min_bearers))
        summaries.append(by_state(result))

    token_table = pd.concat(tokens, ignore_index=True)
    state_table = pd.DataFrame(summaries)
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        token_table.to_csv(cache / "transmission_by_token.csv", index=False)
        state_table.to_csv(cache / "by_state.csv", index=False)
    return token_table, state_table
