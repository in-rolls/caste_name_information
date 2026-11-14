"""Source-specific identities and parsers, returning one account owner list."""

from __future__ import annotations

import importlib.util
import json
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .storage import capture, digest, json_bytes, scan

FIELDS = [
    "district",
    "village",
    "account",
    "source_unit",
    "list_hash",
    "slot",
    "name",
    "relative",
    "relation",
    "residence",
    "jati",
    "surname",
    "signature",
    "format",
    "complete",
]
SCHEMA = pa.schema(
    [(key, pa.bool_() if key == "complete" else pa.string()) for key in FIELDS]
)


def clean(value):
    return " ".join(unicodedata.normalize("NFC", str(value or "")).split())


def identity(parts):
    return json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"))


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parser_from_snapshot(manifest, store, work):
    """Import preserved parser bytes, never a parser modified mid-run."""
    work.mkdir(parents=True, exist_ok=True)
    for relative, entry in manifest["dependencies"].items():
        if relative.endswith(".py"):
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((store / entry["sha256"]).read_bytes())
    if manifest["state"] == "odisha":
        parser = load_module(work / "parse_ror.py", "_lnb_odisha_parser")
        parser.pdf = load_module(work / "pdf_ror.py", "_lnb_odisha_pdf")
        return parser
    sys.path.insert(0, str(work / "src"))
    for key in list(sys.modules):
        if key == "rajasthan_ror" or key.startswith("rajasthan_ror."):
            del sys.modules[key]
    return load_module(work / "src/rajasthan_ror/parse.py", "_lnb_rajasthan_parser")


def frame_from_snapshot(manifest, store):
    return pd.read_parquet(
        store / manifest["dependencies"]["raw/villages.parquet"]["sha256"]
    )


def owner_rows(owners, district, village, account, unit, fmt, complete):
    """Order-independent list comparison retains identical co-owner multiplicity."""
    owners = [
        {
            field: clean(owner.get(field))
            for field in ("name", "relative", "relation", "residence", "jati")
        }
        for owner in owners
    ]
    owners.sort(key=lambda row: json_bytes(row))
    list_hash = digest(json_bytes(owners))
    for slot, owner in enumerate(owners):
        signature_fields = [
            village,
            owner["name"],
            owner["relative"],
            owner["relation"],
            owner["residence"],
        ]
        yield {
            **owner,
            "district": district,
            "village": village,
            "account": account,
            "source_unit": unit,
            "list_hash": list_hash,
            "slot": str(slot),
            "surname": owner["name"].split()[-1] if owner["name"] else "",
            "signature": identity(signature_fields),
            "format": fmt,
            "complete": bool(complete),
        }


def pdf_valid(
    row, root, store, aliases, dependencies, counts, pdf_identity=None, frozen=None
):
    source = row.get("source", {})
    try:
        path = (root / source["path"]).resolve()
        if not path.is_relative_to((root / "raw/pdf").resolve()):
            raise ValueError("outside PDF directory")
        entry = frozen[source["path"]] if frozen is not None else capture(path, store)
        dependencies[source["path"]] = entry
        blob = (store / entry["sha256"]).read_bytes()
        if (
            entry["sha256"] != source["sha256"]
            or len(blob) != source["n_bytes"]
            or not blob.startswith(b"%PDF-")
            or not blob.rstrip().endswith(b"%%EOF")
            or source.get("page_count", 0) < 1
        ):
            raise ValueError("PDF bytes or extraction metadata mismatch")
        printed = pdf_identity or clean
        names = {printed(row.get("village_name", ""))}
        for alias in aliases:
            if all(
                str(row.get(k)) == str(alias.get(k))
                for k in (
                    "district_code",
                    "tahsil_code",
                    "village_code",
                    "village_name",
                )
            ):
                names.add(printed(alias["pdf_village_name"]))
        provenance = source["provenance"]
        if printed(provenance["village_name"]) not in names or printed(
            provenance["khatiyan"]
        ) != printed(row["khatiyan"]):
            raise ValueError("PDF printed identity mismatch")
        return True
    except (OSError, KeyError, ValueError, TypeError):
        counts["pdf_validation_failures"] += 1
        return False


def odisha(relative, item, manifest, store, parser, frame_keys, aliases):
    rows, counts = scan(store / item["sha256"])
    path = Path(relative)
    key = (
        path.parent.parent.name.removeprefix("district_"),
        path.parent.name.removeprefix("tahsil_"),
        path.name.removeprefix("village_").removesuffix(".jsonl.gz"),
    )
    district, village = key[0], identity(key)
    accounts, conflicts, dependencies = {}, set(), {}
    for row in rows:
        if not row.get("ok"):
            counts["failed_attempts"] += 1
            continue
        counts["successful_attempts"] += 1
        actual = tuple(
            str(row.get(k, ""))
            for k in ("district_code", "tahsil_code", "village_code")
        )
        value = row.get("khatiyan_value")
        if actual != key or key not in frame_keys:
            counts["wrong_geography"] += 1
            continue
        if not isinstance(value, str) or not value.strip():
            counts["missing_exact_option"] += 1
            continue
        source = row.get("source", {})
        fmt = source.get("format", "html")
        counts[f"{fmt}_successful_records"] += 1
        if fmt not in {"html", "pdf"}:
            counts["unknown_format"] += 1
            continue
        if fmt == "pdf" and not pdf_valid(
            row,
            Path(manifest["source"]),
            store,
            aliases,
            dependencies,
            counts,
            pdf_identity=parser.pdf.identity,
            frozen=manifest.get("frozen_pdf_dependencies"),
        ):
            continue
        cells = row.get("cells")
        if not isinstance(cells, list) or not all(isinstance(c, str) for c in cells):
            counts["invalid_success_payload"] += 1
            continue
        counts["audited_successful_records"] += 1
        counts["saved_cells"] += len(cells)
        owners = []
        for cell in cells:
            counts["audited_cells"] += 1
            try:
                parts = parser.split_cell(
                    cell, owner_block=(fmt == "pdf" or source.get("owner_spans", False))
                )
            except (ValueError, TypeError, IndexError, KeyError):
                counts["parsing_exceptions"] += 1
                continue
            if not parts:
                counts["cells_without_owner_entries"] += 1
            for part in parts:
                owners.append(
                    {
                        "name": part["name"],
                        "relative": part["relative_name"],
                        "jati": part["caste"],
                        "relation": part["relation"],
                        "residence": part["residence"],
                    }
                )
        counts["parsed_owner_entries_before_consolidation"] += len(owners)
        if not owners:
            counts["ownerless_successful_records"] += 1
        account = identity([*key, value])
        output = list(
            owner_rows(owners, district, village, account, relative, fmt, False)
        )
        fingerprint = digest(json_bytes(output))
        if account in accounts:
            counts["duplicate_successful_keys"] += 1
            if accounts[account][0] != fingerprint:
                conflicts.add(account)
        accounts[account] = (fingerprint, output)
    counts["unique_saved_accounts"] = len(accounts)
    counts["conflicting_accounts"] = len(conflicts)
    status = {}
    if "status" in item:
        status = json.loads((store / item["status"]["sha256"]).read_text())
    complete = (
        status.get("identity") == "khatiyan_value"
        and status.get("remaining") == 0
        and status.get("expected", 0) > 0
        and status.get("saved") == status.get("expected") == len(accounts)
        and not conflicts
        and not any(
            counts[k]
            for k in (
                "wrong_geography",
                "malformed_json",
                "gzip_tail_or_decode_error",
                "incomplete_json_tail",
                "pdf_validation_failures",
            )
        )
    )
    counts["confirmed_complete_units"] = int(complete)
    counts["legacy_completion_status"] = int(
        bool(status) and status.get("identity") != "khatiyan_value"
    )
    output = []
    for account, (_, owners) in accounts.items():
        if account not in conflicts:
            output.extend({**row, "complete": complete} for row in owners)
    return output, counts, dependencies, {village: complete}


def rajasthan(relative, item, store, parser, geography):
    rows, counts = scan(store / item["sha256"])
    sheet = Path(relative).name.removesuffix(".jsonl.gz")
    geo = geography.get(sheet)
    if geo is None:
        counts["sheet_not_in_frame"] += len(rows)
        return [], counts, {}, {}
    village = identity(
        [
            geo[k]
            for k in (
                "district_code",
                "tehsil_code",
                "ri_code",
                "halka_code",
                "village_code",
            )
        ]
    )
    good, conflicting = {}, set()
    for row in rows:
        if row.get("done"):
            continue
        if not row.get("ok"):
            counts["failed_attempts"] += 1
            continue
        counts["successful_attempts"] += 1
        plot = str(row.get("plotno", ""))
        if str(row.get("giscode", "")) != sheet or not plot:
            counts["wrong_geography"] += 1
            continue
        if plot in good:
            counts["duplicate_successful_keys"] += 1
            if good[plot] != row:
                conflicting.add(plot)
        good[plot] = row
    direct = {}
    for plot, row in good.items():
        data = row.get("data")
        if not data or plot in conflicting:
            continue
        if str(data.get("giscode")) != sheet or str(data.get("plotno")) != plot:
            counts["wrong_embedded_identity"] += 1
            continue
        counts["audited_successful_records"] += 1
        try:
            direct[plot] = parser.split_info(data.get("info") or "")
        except (ValueError, TypeError):
            counts["parsing_exceptions"] += 1
    accounts = {}
    for plot, row in good.items():
        if plot in conflicting:
            continue
        parsed = direct.get(plot)
        if row.get("via") and not row.get("data"):
            counts["inferred_plot_links"] += 1
            parsed = direct.get(str(row["via"]))
            if parsed is None:
                counts["unresolved_references"] += 1
                continue
            counts["repeated_plot_owner_entries"] += len(parsed["owners"])
            continue
        if parsed is None:
            continue
        owners = parsed["owners"]
        counts["parsed_owner_entries_before_consolidation"] += len(owners)
        if not owners:
            counts["ownerless_successful_records"] += 1
        khata = clean(parsed["khata"])
        if not khata:
            counts["missing_account_identity"] += 1
            continue
        account = identity([village, khata])
        converted = list(
            owner_rows(
                owners,
                str(geo["district_code"]),
                village,
                account,
                relative,
                "json_info",
                False,
            )
        )
        list_hash = digest(json_bytes(converted))
        accounts.setdefault(account, {})[list_hash] = converted
    output = []
    for variants in accounts.values():
        if len(variants) > 1:
            counts["conflicting_accounts"] += 1
        else:
            output.extend(next(iter(variants.values())))
    counts["unique_saved_accounts"] = len(accounts)
    complete = bool(rows and rows[-1].get("done")) and not any(
        counts[k]
        for k in (
            "malformed_json",
            "gzip_tail_or_decode_error",
            "incomplete_json_tail",
            "wrong_geography",
            "wrong_embedded_identity",
            "unresolved_references",
            "conflicting_accounts",
            "parsing_exceptions",
        )
    )
    counts["confirmed_complete_units"] = int(complete)
    output = [{**row, "complete": complete} for row in output]
    return output, counts, {}, {sheet: complete}


def write_shard(path, rows):
    table = pa.Table.from_pylist(rows, schema=SCHEMA)
    pq.write_table(table, path, compression="zstd")
