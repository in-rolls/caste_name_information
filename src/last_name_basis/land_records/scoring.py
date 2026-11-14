"""Exact account-held-out modal prediction with bounded candidate expansion."""

from __future__ import annotations

import logging

import duckdb

LOG = logging.getLogger(__name__)


def connect(path, temp):
    temp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    con.execute("SET memory_limit='2GB'")
    con.execute("SET threads=2")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET temp_directory=?", [str(temp)])
    return con


def predictions(con, table, cells, destination):
    """Remove the whole account; an empty cell falls back to held-out global."""
    cell = "to_json(list_value(" + ",".join(cells) + "))" if cells else "'global'"
    con.execute(f"""CREATE OR REPLACE TEMP TABLE votes AS
        SELECT account, {cell} cell, jati, sum(weight) n
        FROM {table} GROUP BY account, cell, jati""")
    con.execute("""CREATE OR REPLACE TEMP TABLE totals AS
        SELECT cell, jati, sum(n) n,
          row_number() OVER (PARTITION BY cell ORDER BY sum(n) DESC, jati) rank
        FROM votes GROUP BY cell, jati""")
    # If a held-out account touches m labels, at least one of the first m+1
    # labels is untouched. No lower-ranked label can beat that candidate.
    con.execute("""CREATE OR REPLACE TEMP TABLE folds AS
        SELECT account, cell, count(*) m FROM votes GROUP BY account, cell""")
    con.execute("""CREATE OR REPLACE TEMP TABLE prefixes AS
        SELECT f.cell, f.m, t.jati, t.n
        FROM (SELECT DISTINCT cell,m FROM folds) f
        JOIN totals t ON f.cell=t.cell AND t.rank<=f.m+1""")
    con.execute("""CREATE OR REPLACE TEMP TABLE candidates AS
        SELECT f.account, f.cell, t.jati, t.n-coalesce(v.n,0) remaining,
          row_number() OVER (PARTITION BY f.account, f.cell
            ORDER BY t.n-coalesce(v.n,0) DESC, t.jati) winner
        FROM folds f JOIN prefixes t ON f.cell=t.cell AND f.m=t.m
        LEFT JOIN votes v ON v.account=f.account AND v.cell=f.cell AND v.jati=t.jati""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE {destination} AS
        SELECT account, cell, CASE WHEN remaining>0 THEN jati END prediction
        FROM candidates WHERE winner=1""")


def encode(con, table):
    """Collision-free integer codes; ordered label codes preserve lexical ties."""
    for field in ("account", "village", "surname", "jati"):
        order = "ORDER BY raw_key" if field == "jati" else ""
        con.execute(f"""CREATE OR REPLACE TEMP TABLE score_{field}_dictionary AS
            SELECT raw_key, row_number() OVER ({order}) code
            FROM (SELECT DISTINCT {field} AS raw_key FROM {table})""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE score_input AS
        SELECT a.code account, v.code village, s.code surname, j.code jati, e.weight
        FROM {table} e
        JOIN score_account_dictionary a ON e.account=a.raw_key
        JOIN score_village_dictionary v ON e.village=v.raw_key
        JOIN score_surname_dictionary s ON e.surname=s.raw_key
        JOIN score_jati_dictionary j ON e.jati=j.raw_key""")
    for field in ("account", "village", "surname", "jati"):
        con.execute(f"DROP TABLE score_{field}_dictionary")


def score(con, table="eligible"):
    encode(con, table)
    counts = con.execute("""SELECT count(*), coalesce(sum(weight),0),
        count(DISTINCT account), count(DISTINCT village), count(DISTINCT jati)
        FROM score_input""").fetchone()
    output = dict(zip(("rows", "weight", "accounts", "villages", "labels"), counts))
    output.update({"unit": "recorded_owner_entry", "holdout": "entire_account"})
    predictions(con, "score_input", [], "global_predictions")
    results = {}
    for label, cells in [
        ("blind", []),
        ("surname", ["surname"]),
        ("village", ["village"]),
        ("surname_village", ["surname", "village"]),
    ]:
        LOG.info("Scoring %s: %s", table, label)
        if cells:
            predictions(con, "score_input", cells, "local_predictions")
        else:
            con.execute(
                "CREATE OR REPLACE TEMP TABLE local_predictions AS "
                "SELECT * FROM global_predictions"
            )
        total, supported, errors, fallback = con.execute("""
            SELECT coalesce(sum(e.n),0),
              coalesce(sum(CASE WHEN coalesce(p.prediction,g.prediction) IS NOT NULL
                         THEN e.n ELSE 0 END),0),
              coalesce(sum(CASE WHEN coalesce(p.prediction,g.prediction) IS NOT NULL
                      AND coalesce(p.prediction,g.prediction)<>e.jati
                         THEN e.n ELSE 0 END),0),
              coalesce(sum(CASE WHEN p.prediction IS NULL AND g.prediction IS NOT NULL
                         THEN e.n ELSE 0 END),0)
            FROM votes e
            LEFT JOIN local_predictions p ON e.account=p.account AND e.cell=p.cell
            LEFT JOIN global_predictions g ON e.account=g.account
        """).fetchone()
        results[label] = {
            "error_per_100": 100 * errors / supported if supported else None,
            "supported_weight": supported,
            "total_weight": total,
            "fallback_weight": fallback,
            "errors": errors,
        }
    output["scores"] = results
    surname = results["surname"]["error_per_100"]
    village = results["surname_village"]["error_per_100"]
    output["premium"] = surname - village if surname is not None else None
    output["premium_share"] = 100 * output["premium"] / surname if surname else None
    for temporary in (
        "score_input",
        "votes",
        "totals",
        "folds",
        "prefixes",
        "candidates",
        "global_predictions",
        "local_predictions",
    ):
        con.execute(f"DROP TABLE IF EXISTS {temporary}")
    return output
