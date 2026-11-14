"""Snapshot -> parse -> consolidate -> score -> atomically select a full run."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.metadata
import json
import logging
import shutil
from collections import Counter
from pathlib import Path

import pandas as pd

from ..siblings import repo
from . import adapters, quality, storage
from .report import render
from .scoring import connect, score
from .storage import capture, digest, json_bytes, now, snapshot, write_json

LOG = logging.getLogger(__name__)
ANALYSES = {
    "odisha": "09_odisha_village_premium",
    "rajasthan": "12_rajasthan_land_village_premium",
}


def code_manifest(root, store):
    files = sorted(Path(__file__).parent.glob("*.py"))
    files.append(root / "analyses/09_odisha_village_premium/jati.py")
    return {str(p.relative_to(root)): capture(p, store) for p in files}


def census(manifest, store, cache, work, rebuild=False):
    parser = adapters.parser_from_snapshot(manifest, store, work / "parser")
    frame = adapters.frame_from_snapshot(manifest, store).fillna("").astype(str)
    state = manifest["state"]
    if state == "odisha":
        frame_keys = set(
            frame[["district_code", "tahsil_code", "village_code"]].itertuples(
                index=False, name=None
            )
        )
        if len(frame_keys) != len(frame):
            raise ValueError("Duplicate Odisha village frame keys")
        aliases_entry = manifest["dependencies"].get("raw/pdf-village-aliases.json")
        aliases = (
            json.loads((store / aliases_entry["sha256"]).read_text())
            if aliases_entry
            else []
        )
    else:
        if frame["giscode"].duplicated().any():
            raise ValueError("Duplicate Rajasthan sheet frame keys")
        geography = frame.set_index("giscode").to_dict("index")
    cache.mkdir(parents=True, exist_ok=True)
    counts, completion, shards = Counter(), {}, []
    dependencies = {
        k: v["sha256"]
        for k, v in manifest["dependencies"].items()
        if k != "logs/crawl-health.json"
    }
    executing = manifest.get("execution_code", {})

    def code_hash(module):
        key = "src/last_name_basis/land_records/" + Path(module.__file__).name
        entry = executing.get(key)
        return entry["sha256"] if entry else digest(Path(module.__file__).read_bytes())

    version = digest(
        json_bytes(
            {
                "adapters": code_hash(adapters),
                "storage": code_hash(storage),
                "dependencies": dependencies,
            }
        )
    )
    quality_version = code_hash(quality)
    for index, (relative, item) in enumerate(manifest["files"].items()):
        inputs = {k: v for k, v in item.items() if k != "parsed_shard"}
        key = digest(json_bytes([version, relative, inputs]))
        shard = cache / (key + ".parquet")
        metadata_path = cache / (key + ".json")
        metadata = (
            json.loads(metadata_path.read_text()) if metadata_path.exists() else None
        )
        usable = metadata is not None and shard.exists() and not rebuild
        if usable:
            for pdf, entry in metadata["pdf_dependencies"].items():
                try:
                    current = (
                        manifest["frozen_pdf_dependencies"][pdf]
                        if "frozen_pdf_dependencies" in manifest
                        else capture(Path(manifest["source"]) / pdf, store)
                    )
                    if current["sha256"] != entry["sha256"]:
                        usable = False
                except OSError:
                    usable = False
        if not usable:
            if state == "odisha":
                rows, tally, pdfs, complete = adapters.odisha(
                    relative, item, manifest, store, parser, frame_keys, aliases
                )
            else:
                rows, tally, pdfs, complete = adapters.rajasthan(
                    relative, item, store, parser, geography
                )
            if tally["gzip_tail_or_decode_error"] or tally["incomplete_json_tail"]:
                tally[
                    (
                        "active_incomplete_streams"
                        if item["open_at_capture"]
                        else "unverified_incomplete_streams"
                    )
                ] += 1
            temporary = shard.with_suffix(".tmp")
            adapters.write_shard(temporary, rows)
            temporary.replace(shard)
            metadata = {
                "counts": dict(tally),
                "completion": complete,
                "pdf_dependencies": pdfs,
            }
            write_json(metadata_path, metadata)
        if metadata.get("quality_version") != quality_version:
            metadata["counts"].update(
                quality.dispositions(store / item["sha256"], state)
            )
            metadata["quality_version"] = quality_version
            write_json(metadata_path, metadata)
        counts.update(metadata["counts"])
        completion.update(metadata["completion"])
        manifest.setdefault("pdf_dependencies", {}).update(metadata["pdf_dependencies"])
        shards.append(str(shard))
        item["parsed_shard"] = shard.name
        if (index + 1) % 1000 == 0:
            LOG.info(
                "%s parsed %s/%s checkpoint files",
                state,
                index + 1,
                len(manifest["files"]),
            )
    counts["checkpoint_files"] = len(shards)
    counts["expected_units"] = len(frame)
    if state == "rajasthan":
        keys = ["district_code", "tehsil_code", "ri_code", "halka_code", "village_code"]
        complete_villages = set()
        for key, group in frame.groupby(keys, observed=True):
            if all(completion.get(sheet, False) for sheet in group["giscode"]):
                complete_villages.add(adapters.identity(key))
    else:
        complete_villages = {key for key, value in completion.items() if value}
    counts["confirmed_complete_villages"] = len(complete_villages)
    return shards, dict(counts), complete_villages


def prepare(con, shards, complete_villages):
    con.read_parquet(shards).create_view("parsed")
    con.execute("""CREATE TABLE conflicts AS SELECT account FROM parsed
        GROUP BY account HAVING count(DISTINCT list_hash)>1""")
    con.execute("""CREATE TABLE selected_accounts AS
        SELECT account, min(source_unit) source_unit FROM parsed
        WHERE account NOT IN (SELECT account FROM conflicts) GROUP BY account""")
    con.execute("""CREATE TABLE owners AS SELECT p.* FROM parsed p
        JOIN selected_accounts s USING (account, source_unit)""")
    completed = pd.DataFrame({"village": sorted(complete_villages)}, dtype=str)
    con.register("completed", completed)
    con.execute("""CREATE VIEW eligible AS
        SELECT *, 1.0::DOUBLE weight FROM owners WHERE name<>'' AND jati<>''
        AND regexp_matches(name, '[\\p{L}\\p{N}]')
        AND regexp_matches(jati, '[\\p{L}\\p{N}]')""")
    con.execute(
        "CREATE VIEW complete_eligible AS SELECT * FROM eligible "
        "WHERE village IN (SELECT village FROM completed)"
    )
    rows = con.execute("""SELECT (SELECT count(*) FROM parsed),
        (SELECT count(*) FROM conflicts), (SELECT count(*) FROM owners),
        (SELECT count(*) FROM owners WHERE name=''),
        (SELECT count(*) FROM owners WHERE jati=''),
        (SELECT count(*) FROM eligible),
        (SELECT count(DISTINCT village) FROM owners),
        (SELECT count(DISTINCT district) FROM owners),
        (SELECT count(*) FROM owners WHERE account IN
         (SELECT account FROM conflicts))""").fetchone()
    keys = (
        "parsed_shard_entries",
        "cross_sheet_conflicting_accounts",
        "consolidated_owner_entries",
        "empty_name_entries",
        "empty_caste_entries",
        "eligible_entries",
        "villages_with_owner_entries",
        "districts_with_owner_entries",
        "conflicting_entries_retained",
    )
    audit = dict(zip(keys, rows))
    audit["conflicting_entries_excluded"] = con.execute(
        "SELECT count(*) FROM parsed WHERE account IN (SELECT account FROM conflicts)"
    ).fetchone()[0]
    audit["excluded_entries"] = (
        audit["consolidated_owner_entries"] - audit["eligible_entries"]
    )
    audit["name_fill_rate"] = (
        (1 - audit["empty_name_entries"] / rows[2]) if rows[2] else None
    )
    audit["caste_fill_rate"] = (
        (1 - audit["empty_caste_entries"] / rows[2]) if rows[2] else None
    )
    audit["repeated_account_entries_removed"] = con.execute("""SELECT
        (SELECT count(*) FROM parsed
         WHERE account NOT IN (SELECT account FROM conflicts))
        - (SELECT count(*) FROM owners)""").fetchone()[0]
    return audit


def signature_sensitivity(con):
    con.execute("""CREATE TABLE signature_conflicts AS SELECT signature FROM eligible
        WHERE relative<>'' GROUP BY signature HAVING count(DISTINCT jati)>1""")
    con.execute("""CREATE TABLE signature_choices AS
        SELECT row_number() OVER () signature_id,
          min(struct_pack(account := account, slot := slot)) chosen
        FROM eligible WHERE signature NOT IN (SELECT signature FROM signature_conflicts)
        GROUP BY CASE WHEN relative<>'' THEN signature ELSE account||':'||slot END""")
    con.execute("""CREATE VIEW signature_eligible AS
        SELECT CASE WHEN e.relative<>'' THEN 'signature:'||c.signature_id
                    ELSE 'account:'||e.account END account,
               e.village, e.surname, e.jati, e.weight
        FROM eligible e JOIN signature_choices c
        ON e.account=c.chosen.account AND e.slot=c.chosen.slot""")
    result = score(con, "signature_eligible")
    result["unit"] = "matching_owner_signature_with_relative_when_available"
    result["not_verified_unique_people"] = True
    result["holdout"] = "matching_signature_when_relative_present_else_account"
    result["conflicting_signatures_excluded"] = con.execute(
        "SELECT count(*) FROM signature_conflicts"
    ).fetchone()[0]
    return result


def surname_position(con):
    # Relative-name agreement is conditional diagnostic evidence, not a surname label.
    row = con.execute("""WITH tokens AS (
        SELECT string_split(name,' ') n, string_split(relative,' ') r
        FROM eligible WHERE relative<>''), matches AS (
        SELECT list_contains(r,n[1]) first_match, list_contains(r,n[-1]) last_match,
               len(list_intersect(n,r))>0 any_match FROM tokens)
        SELECT count(*), count(*) FILTER (WHERE any_match),
          count(*) FILTER (WHERE first_match), count(*) FILTER (WHERE last_match)
        FROM matches""").fetchone()
    result = dict(
        zip(
            (
                "entries_with_relative",
                "entries_sharing_any_token",
                "entries_sharing_first_token",
                "entries_sharing_last_token",
            ),
            row,
        )
    )

    names = con.execute("""SELECT count(*),
        count(*) FILTER (WHERE len(string_split(name,' '))=1),
        count(*) FILTER (WHERE len(string_split(name,' '))>1)
        FROM eligible""").fetchone()
    result.update(
        zip(("eligible_name_entries", "single_token_names", "multitoken_names"), names)
    )
    return result


def name_representation_sensitivity(con):
    """Change only the name cue; preserve account holdout, labels and every entry."""
    row = con.execute("""WITH forms AS (
        SELECT name, replace(name,' ','') compact, count(*) n
        FROM eligible GROUP BY name), groups AS (
        SELECT compact, count(*) forms, sum(n) entries FROM forms GROUP BY compact)
        SELECT (SELECT count(*) FROM eligible), (SELECT count(*) FROM forms),
          count(*), count(*) FILTER (WHERE forms>1),
          coalesce(sum(entries) FILTER (WHERE forms>1),0)
        FROM groups""").fetchone()
    result = dict(
        zip(
            (
                "eligible_entries",
                "distinct_recorded_names",
                "distinct_spaceless_names",
                "spacing_variant_groups",
                "entries_in_spacing_variant_groups",
            ),
            row,
        )
    )
    for label, expression in (
        ("whole_name", "name"),
        ("whole_name_without_spaces", "replace(name,' ','')"),
    ):
        con.execute(f"""CREATE OR REPLACE TEMP VIEW name_eligible AS
            SELECT account,village,jati,weight,{expression} surname FROM eligible""")
        result[label] = score(con, "name_eligible")
        result[label]["name_cue"] = label
    con.execute("DROP VIEW name_eligible")
    return result


def normalization_sensitivity(con, manifest, store, work):
    """Reuse the old Odisha method on sufficient statistics, without globals edits."""
    entry = manifest["pipeline_code"]["analyses/09_odisha_village_premium/jati.py"]
    source = work / "jati_sensitivity.py"
    source.write_bytes((store / entry["sha256"]).read_bytes())
    norm = adapters.load_module(source, "_lnb_jati_sensitivity")
    counts = con.execute("SELECT jati, count(*) n FROM eligible GROUP BY jati").df()
    counts = counts.set_index("jati")["n"]
    valid, dropped = norm.drop_runaway(counts)
    profiles = con.execute("""SELECT jati,surname,count(*) n FROM eligible
                             GROUP BY jati,surname""").df()
    profiles = {
        label: group.set_index("surname")["n"]
        for label, group in profiles.groupby("jati", observed=True)
    }
    mapping, merged, refused = norm.merge_variants(valid, profiles)
    mapping, carried = norm.carry_across_religion(mapping, valid)
    if len(carried):
        merged = pd.concat([merged, carried], ignore_index=True)
    mapping_frame = pd.DataFrame(
        list(mapping.items()), columns=["original", "normalized"]
    )
    con.register("mapping_frame", mapping_frame)
    stats = con.execute("""SELECT normalized jati, count(*) n,
                count(DISTINCT village) villages FROM eligible e JOIN mapping_frame m
                ON e.jati=m.original GROUP BY normalized""").df()
    keep = set(
        stats.loc[
            (stats.villages >= norm.MIN_JATI_VILLAGES)
            & (
                (stats.n >= norm.MIN_JATI_HOUSEHOLDS)
                | (stats.villages >= norm.MIN_JATI_REACH)
            ),
            "jati",
        ]
    )
    mapping_frame = mapping_frame[mapping_frame.normalized.isin(keep)].copy()
    con.unregister("mapping_frame")
    con.register("mapping_frame", mapping_frame)
    con.execute(
        """CREATE VIEW normalized_eligible AS SELECT e.* REPLACE (m.normalized AS jati)
                   FROM eligible e JOIN mapping_frame m ON e.jati=m.original"""
    )
    for label, frame in [
        ("merge_mapping", mapping_frame),
        ("accepted_merges", merged),
        ("refused_merges", refused),
        ("dropped_labels", dropped),
    ]:
        frame.to_parquet(work / f"{label}.parquet", index=False)
    result = score(con, "normalized_eligible")
    result["interpretation"] = (
        "Exploratory sensitivity: targets use surname profiles from "
        "the full snapshot; not independent prediction evidence."
    )
    result["merged_labels"] = len(merged)
    return result


def file_checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run_state(root, source, state, rebuild=False, frozen=None, execution_code=None):
    private = root / ".local/land-records"
    store = private / "objects"
    if execution_code is None:
        execution_code = code_manifest(root, store)
    manifest = (
        json.loads(frozen.read_text())
        if frozen
        else snapshot(source, state, store, execution_code)
    )
    if frozen:
        manifest["frozen_pdf_dependencies"] = manifest.get("pdf_dependencies", {})
    manifest["execution_code"] = execution_code
    run_id = now().replace(":", "").replace("+0000", "Z")
    work = private / "runs" / state / run_id
    work.mkdir(parents=True)
    write_json(work / "input-manifest.json", manifest)
    LOG.info("%s snapshot: %s files", state, len(manifest["files"]))
    shards, counts, complete = census(
        manifest, store, private / "cache" / state, work, rebuild
    )
    write_json(work / "input-manifest.json", manifest)
    con = connect(work / "analysis.duckdb", work / "spill")
    try:
        counts.update(prepare(con, shards, complete))
        counts["audited_record_denominator"] = counts.get("successful_attempts", 0)
        counts["audited_record_numerator"] = counts.get("audited_successful_records", 0)
        if state == "rajasthan":
            counts["audited_record_numerator"] += counts.get(
                "inferred_plot_links", 0
            ) - counts.get("unresolved_references", 0)
        LOG.info(
            "%s census complete: %s eligible entries", state, counts["eligible_entries"]
        )
        summary = {
            "state": state,
            "run_id": run_id,
            "created_at": now(),
            "audit_mode": "census",
            "sampling_limit": 0,
            "capture_started": manifest["capture_started"],
            "capture_finished": manifest["capture_finished"],
            "counts": counts,
            "primary": score(con),
            "complete_villages": score(con, "complete_eligible"),
            "signature_sensitivity": signature_sensitivity(con),
            "surname_position": surname_position(con),
            "name_representation": name_representation_sensitivity(con),
        }
        by_district = []
        for (district,) in con.execute(
            "SELECT DISTINCT district FROM eligible ORDER BY district"
        ).fetchall():
            LOG.info("%s scoring district %s", state, district)
            con.execute(
                "CREATE OR REPLACE TEMP TABLE district_eligible AS "
                "SELECT account,village,surname,jati,weight FROM eligible "
                "WHERE district=?",
                [district],
            )
            by_district.append(
                {"district": district, **score(con, "district_eligible")}
            )
        summary["by_district"] = by_district
        if state == "odisha":
            summary["normalization_sensitivity"] = normalization_sensitivity(
                con, manifest, store, work
            )
        con.execute(
            "COPY owners TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(work / "owners.parquet")],
        )
        con.execute(
            "COPY eligible TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",
            [str(work / "eligible.parquet")],
        )
    finally:
        con.close()
        (work / "analysis.duckdb").unlink(missing_ok=True)
        (work / "analysis.duckdb.wal").unlink(missing_ok=True)
        shutil.rmtree(work / "spill", ignore_errors=True)
    manifest["environment"] = {
        name: importlib.metadata.version(name)
        for name in (
            "duckdb",
            "pandas",
            "pyarrow",
            "numpy",
            "rapidfuzz",
            "pdfplumber",
            "pypdf",
        )
    }
    manifest["execution_code"] = execution_code
    manifest["completed_at"] = now()
    write_json(
        work / "SCHEMA.json", {field.name: str(field.type) for field in adapters.SCHEMA}
    )
    manifest["artifacts"] = {
        name: file_checksum(work / name)
        for name in ("owners.parquet", "eligible.parquet", "SCHEMA.json")
    }
    write_json(work / "manifest.json", manifest)
    summary["manifest_sha256"] = digest((work / "manifest.json").read_bytes())
    write_json(work / "summary.json", summary)
    render(summary, work)
    return work


def publish(root, runs):
    """Select completed state outputs only after every requested state succeeds."""
    for state, work in runs.items():
        analysis = root / "analyses" / ANALYSES[state]
        tab, fig = analysis / "out/tab", analysis / "out/fig"
        tab.mkdir(parents=True, exist_ok=True)
        fig.mkdir(parents=True, exist_ok=True)
        for source, destination in [
            (work / "summary.json", tab / "summary.json"),
            (work / "scores.csv", tab / "scores.csv"),
            (work / "note.md", analysis / "note.md"),
            (work / "village_premium.png", fig / "village_premium.png"),
        ]:
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            shutil.copyfile(source, temporary)
            temporary.replace(destination)
    latest_path = root / ".local/land-records/latest.json"
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else {}
    latest.update({state: str(work.relative_to(root)) for state, work in runs.items()})
    write_json(latest_path, latest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--states", nargs="+", choices=list(ANALYSES), default=None)
    parser.add_argument(
        "--rebuild", action="store_true", help="Reparse all snapshot shards"
    )
    parser.add_argument("--snapshot", type=Path, help="Replay one saved input manifest")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[3]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    private = root / ".local/land-records"
    private.mkdir(parents=True, exist_ok=True)
    with (private / "refresh.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another land-record refresh is running") from error
        states = args.states or list(ANALYSES)
        frozen_state = None
        if args.snapshot:
            frozen_state = json.loads(args.snapshot.read_text())["state"]
            states = args.states or [frozen_state]
            if frozen_state not in states:
                raise ValueError("Snapshot state is absent from --states")
        execution_code = code_manifest(root, private / "objects")
        runs = {
            state: run_state(
                root,
                repo(f"ror_{state}_2026"),
                state,
                args.rebuild,
                args.snapshot if state == frozen_state else None,
                execution_code,
            )
            for state in states
        }
        publish(root, runs)
        LOG.info("Completed: %s", ", ".join(runs))
