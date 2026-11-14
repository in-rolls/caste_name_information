"""Behavioral tests for census ingestion and account-held-out evaluation."""

import gzip
import json
import random
from collections import Counter
from types import SimpleNamespace

import pandas as pd
import pytest

from last_name_basis.land_records import adapters
from last_name_basis.land_records.pipeline import prepare, signature_sensitivity
from last_name_basis.land_records.scoring import connect, score
from last_name_basis.land_records.storage import capture, scan


def connection(tmp_path):
    return connect(":memory:", tmp_path / "spill")


def brute(rows, cues):
    errors = supported = 0
    for row in rows:
        training = [r for r in rows if r["account"] != row["account"]]
        same = [r for r in training if all(r[k] == row[k] for k in cues)]
        counts = Counter(r["jati"] for r in same or training)
        if not counts:
            continue
        prediction = min(counts, key=lambda k: (-counts[k], k))
        supported += 1
        errors += prediction != row["jati"]
    return 100 * errors / supported if supported else None


@pytest.mark.parametrize("seed", range(5))
def test_scores_match_exhaustive_account_holdout(tmp_path, seed):
    rng = random.Random(seed)
    rows = [
        {
            "account": str(rng.randrange(8)),
            "surname": str(rng.randrange(5)),
            "village": str(rng.randrange(3)),
            "jati": str(rng.randrange(7)),
            "weight": 1.0,
        }
        for _ in range(60)
    ]
    with connection(tmp_path) as con:
        con.register("eligible", pd.DataFrame(rows))
        result = score(con)
        for label, cues in [
            ("blind", []),
            ("surname", ["surname"]),
            ("village", ["village"]),
            ("surname_village", ["surname", "village"]),
        ]:
            assert result["scores"][label]["error_per_100"] == pytest.approx(
                brute(rows, cues)
            )


def test_single_account_is_unsupported(tmp_path):
    with connection(tmp_path) as con:
        con.register(
            "eligible",
            pd.DataFrame(
                [dict(account="1", surname="x", village="v", jati="a", weight=1.0)]
            ),
        )
        result = score(con)
        assert result["premium"] is None
        assert result["scores"]["surname"]["supported_weight"] == 0


def test_complete_prefix_and_malformed_records_are_counted(tmp_path):
    source = tmp_path / "data.gz"
    source.write_bytes(gzip.compress(b'{"ok":true}\ninvalid\n{"partial":'))
    entry = capture(source, tmp_path / "objects")
    rows, counts = scan(tmp_path / "objects" / entry["sha256"])
    assert rows == [{"ok": True}]
    assert counts["malformed_json"] == 1
    assert counts["incomplete_json_tail"] == 1
    source.write_bytes(gzip.compress(b'{"ok":false}\n'))
    assert scan(tmp_path / "objects" / entry["sha256"])[0] == rows


def test_gzip_interruption_retains_preceding_members(tmp_path):
    source = tmp_path / "cut.gz"
    source.write_bytes(gzip.compress(b'{"n":1}\n') + gzip.compress(b'{"n":2}\n')[:-5])
    rows, counts = scan(source)
    assert rows[0] == {"n": 1}
    assert counts["gzip_tail_or_decode_error"] == 1


def test_account_consolidation_preserves_joint_owner_multiplicity(tmp_path):
    owner = dict(
        name="Test A", relative="Parent A", relation="child", residence="v", jati="J"
    )
    rows = list(
        adapters.owner_rows([owner, owner], "d", "v", "a", "sheet1", "html", False)
    )
    rows += list(
        adapters.owner_rows([owner, owner], "d", "v", "a", "sheet2", "html", False)
    )
    path = tmp_path / "owners.parquet"
    adapters.write_shard(path, rows)
    with connection(tmp_path) as con:
        counts = prepare(con, [str(path)], set())
        assert counts["eligible_entries"] == 2
        assert counts["repeated_account_entries_removed"] == 2
        assert con.execute("SELECT count(*) FROM complete_eligible").fetchone()[0] == 0
        assert signature_sensitivity(con)["rows"] == 1


def test_conflicting_accounts_quarantined(tmp_path):
    rows = []
    for sheet, caste in [("one", "J"), ("two", "K")]:
        rows += list(
            adapters.owner_rows(
                [dict(name="Test A", jati=caste)], "d", "v", "a", sheet, "html", False
            )
        )
    path = tmp_path / "owners.parquet"
    adapters.write_shard(path, rows)
    with connection(tmp_path) as con:
        counts = prepare(con, [str(path)], set())
        assert counts["cross_sheet_conflicting_accounts"] == 1
        assert counts["eligible_entries"] == 0
        assert score(con)["premium"] is None


def test_missing_and_punctuation_fields_are_excluded_without_rare_label_floor(tmp_path):
    rows = list(
        adapters.owner_rows(
            [
                dict(name="Test A", jati="Rare"),
                dict(name="Test B"),
                dict(name="---", jati="J"),
                dict(jati="K"),
            ],
            "d",
            "v",
            "a",
            "sheet",
            "html",
            False,
        )
    )
    path = tmp_path / "owners.parquet"
    adapters.write_shard(path, rows)
    with connection(tmp_path) as con:
        counts = prepare(con, [str(path)], set())
        assert counts["consolidated_owner_entries"] == 4
        assert counts["eligible_entries"] == 1
        assert counts["excluded_entries"] == 3


def test_odisha_option_whitespace_is_identity(tmp_path):
    rows = [
        dict(
            ok=True,
            district_code="1",
            tahsil_code="2",
            village_code="3",
            khatiyan="same label",
            khatiyan_value=value,
            cells=["owner"],
            source={"owner_spans": True},
        )
        for value in ["1 ", "1\t"]
    ]
    source = tmp_path / "source.gz"
    source.write_bytes(
        gzip.compress(("\n".join(json.dumps(r) for r in rows) + "\n").encode())
    )
    store = tmp_path / "objects"
    item = capture(source, store)
    parser = SimpleNamespace(
        split_cell=lambda cell, owner_block: [
            dict(
                name="Test Name",
                relative_name="Parent Name",
                caste="J",
                relation="child",
                residence="v",
            )
        ]
    )
    output, counts, _, complete = adapters.odisha(
        "raw/ror/district_1/tahsil_2/village_3.jsonl.gz",
        item,
        {"source": str(tmp_path)},
        store,
        parser,
        {("1", "2", "3")},
        [],
    )
    assert len({r["account"] for r in output}) == 2
    assert counts["audited_cells"] == counts["saved_cells"] == 2
    assert not any(complete.values())


def test_pdf_bytes_and_printed_provenance_are_both_required(tmp_path):
    root = tmp_path / "source"
    path = root / "raw/pdf/document.pdf"
    path.parent.mkdir(parents=True)
    blob = b"%PDF-1.4\nfixture\n%%EOF"
    path.write_bytes(blob)
    from last_name_basis.land_records.storage import digest

    row = dict(
        village_name="v",
        khatiyan="1",
        source=dict(
            path="raw/pdf/document.pdf",
            sha256=digest(blob),
            n_bytes=len(blob),
            page_count=1,
            provenance={"village_name": "v", "khatiyan": "1"},
        ),
    )
    counts = Counter()
    assert adapters.pdf_valid(row, root, tmp_path / "objects", [], {}, counts)
    row["source"]["provenance"]["village_name"] = "wrong"
    assert not adapters.pdf_valid(row, root, tmp_path / "objects", [], {}, counts)
    assert counts["pdf_validation_failures"] == 1


def test_rajasthan_references_do_not_create_more_owners(tmp_path):
    payload = dict(
        khata="8", owners=[dict(name="Test A", jati="J"), dict(name="Test B", jati="K")]
    )
    rows = [
        dict(
            giscode="sheet",
            plotno="1",
            ok=True,
            data=dict(giscode="sheet", plotno="1", info=json.dumps(payload)),
        ),
        dict(giscode="sheet", plotno="2", ok=True, via="1"),
        dict(giscode="sheet", plotno="3", ok=True, via="missing"),
        dict(giscode="sheet", done=True),
    ]
    source = tmp_path / "source.gz"
    source.write_bytes(
        gzip.compress(("\n".join(json.dumps(r) for r in rows) + "\n").encode())
    )
    store = tmp_path / "objects"
    item = capture(source, store)
    geo = {
        "sheet": {
            k: "1"
            for k in (
                "district_code",
                "tehsil_code",
                "ri_code",
                "halka_code",
                "village_code",
            )
        }
    }
    output, counts, _, complete = adapters.rajasthan(
        "raw/plots/sheet.jsonl.gz",
        item,
        store,
        SimpleNamespace(split_info=json.loads),
        geo,
    )
    assert len(output) == 2
    assert {row["format"] for row in output} == {"json_info"}
    assert counts["repeated_plot_owner_entries"] == 2
    assert counts["unresolved_references"] == 1
    assert complete == {"sheet": False}


def test_incremental_repair_parser_change_and_cold_rebuild(tmp_path, monkeypatch):
    from last_name_basis.land_records import storage
    from last_name_basis.land_records.pipeline import census

    monkeypatch.setattr(storage, "open_files", lambda: set())
    root, store, cache = tmp_path / "source", tmp_path / "objects", tmp_path / "cache"
    checkpoint = root / "raw/ror/district_1/tahsil_2/village_3.jsonl.gz"
    checkpoint.parent.mkdir(parents=True)
    pd.DataFrame(
        [dict(district_code="1", tahsil_code="2", village_code="3")]
    ).to_parquet(root / "raw/villages.parquet")
    parser_text = (
        "def split_cell(cell, owner_block=False):\n"
        '    return [dict(name="Test A",relative_name="Parent A",'
        'caste="J",relation="child",residence="v")]\n'
    )
    (root / "parse_ror.py").write_text(parser_text)
    (root / "pdf_ror.py").write_text("def identity(value):\n    return value\n")
    row = dict(
        ok=True,
        district_code="1",
        tahsil_code="2",
        village_code="3",
        khatiyan_value="1 ",
        cells=["owner"],
    )

    def save(rows):
        checkpoint.write_bytes(
            gzip.compress(("\n".join(json.dumps(r) for r in rows) + "\n").encode())
        )

    def run(manifest, name, rebuild=False):
        shards, counts, _ = census(manifest, store, cache, tmp_path / name, rebuild)
        return (
            pd.concat([pd.read_parquet(p) for p in shards], ignore_index=True),
            counts,
        )

    save([row])
    first = storage.snapshot(root, "odisha", store, {})
    initial, counts = run(first, "first")
    assert len(initial) == 1
    cached, cached_counts = run(first, "cached")
    pd.testing.assert_frame_equal(initial, cached)
    assert counts == cached_counts
    cold, cold_counts = run(first, "cold", True)
    pd.testing.assert_frame_equal(initial, cold)
    assert cold_counts == counts
    save([row, {**row, "khatiyan_value": "2 "}])
    second = storage.snapshot(root, "odisha", store, {})
    grown, _ = run(second, "grown")
    assert len(grown) == 2
    replay, _ = run(first, "replay", True)
    pd.testing.assert_frame_equal(initial, replay)
    save([{**row, "ok": False}])
    repaired = storage.snapshot(root, "odisha", store, {})
    repaired_rows, repaired_counts = run(repaired, "repaired")
    assert len(repaired_rows) == 0
    assert repaired_counts["failed_attempts"] == 1
    save([row])
    (root / "parse_ror.py").write_text(
        "def split_cell(cell, owner_block=False):\n    return []\n"
    )
    updated = storage.snapshot(root, "odisha", store, {})
    changed, changed_counts = run(updated, "changed")
    assert len(changed) == 0
    assert changed_counts["ownerless_successful_records"] == 1


def test_report_handles_empty_census_and_unsupported_scores(tmp_path):
    from last_name_basis.land_records.report import render

    with connection(tmp_path) as con:
        con.register(
            "eligible",
            pd.DataFrame(
                {
                    k: pd.Series(dtype="str")
                    for k in ["account", "surname", "village", "jati"]
                }
            ).assign(weight=pd.Series(dtype=float)),
        )
        result = score(con)
    summary = dict(
        primary=result,
        counts={"name_fill_rate": None},
        state="odisha",
        capture_started="start",
        capture_finished="end",
        by_district=[],
        surname_position={},
        name_representation={
            "whole_name": result,
            "whole_name_without_spaces": result,
            "eligible_entries": 0,
            "spacing_variant_groups": 0,
            "entries_in_spacing_variant_groups": 0,
        },
        run_id="test",
        manifest_sha256="0" * 64,
    )
    render(summary, tmp_path)
    assert (tmp_path / "village_premium.png").stat().st_size > 1000
    assert "unavailable" in (tmp_path / "note.md").read_text()


def test_one_command_runs_both_states_and_single_refresh_preserves_other(
    tmp_path, monkeypatch
):
    from last_name_basis.land_records import pipeline

    monkeypatch.setattr(
        pipeline,
        "__file__",
        str(tmp_path / "src/last_name_basis/land_records/pipeline.py"),
    )
    calls, sources = [], []

    def fake_run(root, source, state, rebuild, frozen, execution_code=None):
        calls.append(state)
        sources.append(source)
        work = root / "runs" / f"{state}-{len(calls)}"
        work.mkdir(parents=True)
        for name in ("summary.json", "scores.csv", "note.md", "village_premium.png"):
            (work / name).write_text("fixture")
        return work

    monkeypatch.setattr(pipeline, "code_manifest", lambda *args: {})
    monkeypatch.setattr(pipeline, "run_state", fake_run)
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path))
    pipeline.main([])
    assert calls == ["odisha", "rajasthan"]
    assert sources == [
        tmp_path / "in-rolls/ror_odisha_2026",
        tmp_path / "in-rolls/ror_rajasthan_2026",
    ]
    pointer = tmp_path / ".local/land-records/latest.json"
    previous = json.loads(pointer.read_text())
    pipeline.main(["--states", "rajasthan"])
    latest = json.loads(pointer.read_text())
    assert latest["odisha"] == previous["odisha"]
    assert latest["rajasthan"] != previous["rajasthan"]

    def failure(*args):
        raise RuntimeError("interrupted")

    monkeypatch.setattr(pipeline, "run_state", failure)
    with pytest.raises(RuntimeError, match="interrupted"):
        pipeline.main([])
    assert json.loads(pointer.read_text()) == latest


def test_dispositions_separate_misses_recovered_failures_and_exact_keys(tmp_path):
    from last_name_basis.land_records.quality import dispositions

    rows = [
        dict(plotno="1", ok=False, reason="timeout"),
        dict(plotno="1", ok=True),
        dict(plotno="2", ok=False, reason="miss"),
        dict(plotno="3", ok=False, reason="DNS failure"),
        dict(done=True),
    ]
    path = tmp_path / "raw.gz"
    path.write_bytes(
        gzip.compress(("\n".join(json.dumps(r) for r in rows) + "\n").encode())
    )
    counts = dispositions(path, "rajasthan")
    assert counts["portal_miss_attempts"] == 1
    assert counts["failed_attempts"] == 2
    assert counts["unresolved_failed_source_keys"] == 1
    assert counts["timeout_unresolved_keys"] == 0
    assert counts["dns_unresolved_keys"] == 1
    rows = [
        dict(khatiyan_value="1 ", ok=False, error="timeout"),
        dict(khatiyan_value="1\t", ok=True),
    ]
    path.write_bytes(
        gzip.compress(("\n".join(json.dumps(r) for r in rows) + "\n").encode())
    )
    assert dispositions(path, "odisha")["unresolved_failed_source_keys"] == 1


def test_failed_scoring_removes_scratch_database_but_preserves_inputs(
    tmp_path, monkeypatch
):
    from last_name_basis.land_records import pipeline

    shard = tmp_path / "input.parquet"
    adapters.write_shard(
        shard,
        list(
            adapters.owner_rows(
                [dict(name="Test A", jati="J")], "d", "v", "a", "sheet", "html", False
            )
        ),
    )
    monkeypatch.setattr(pipeline, "code_manifest", lambda *args: {})
    monkeypatch.setattr(
        pipeline,
        "snapshot",
        lambda *args: dict(
            state="rajasthan",
            files={"sheet": {}},
            capture_started="start",
            capture_finished="end",
        ),
    )
    monkeypatch.setattr(pipeline, "census", lambda *args: ([str(shard)], {}, set()))

    def failure(*args):
        raise RuntimeError("scoring failure")

    monkeypatch.setattr(pipeline, "score", failure)
    with pytest.raises(RuntimeError, match="scoring failure"):
        pipeline.run_state(tmp_path, tmp_path / "source", "rajasthan")
    assert shard.exists()
    assert list(
        tmp_path.glob(".local/land-records/runs/rajasthan/*/input-manifest.json")
    )
    assert not list(
        tmp_path.glob(".local/land-records/runs/rajasthan/*/analysis.duckdb*")
    )


def test_snapshot_detects_a_growing_in_place_rewrite(tmp_path, monkeypatch):
    from pathlib import Path

    from last_name_basis.land_records.storage import digest

    source = tmp_path / "changing.bin"
    source.write_bytes(b"a" * (2 * 1024 * 1024))
    replacement = b"b" * (2 * 1024 * 1024 + 1)
    original_open = Path.open
    changed = False

    class ChangingReader:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def read(self, size):
            nonlocal changed
            result = self.stream.read(size)
            if not changed:
                changed = True
                with original_open(source, "wb") as writer:
                    writer.write(replacement)
            return result

    def opening(path, *args, **kwargs):
        stream = original_open(path, *args, **kwargs)
        return ChangingReader(stream) if path == source and args == ("rb",) else stream

    monkeypatch.setattr(Path, "open", opening)
    entry = capture(source, tmp_path / "objects")
    assert entry["sha256"] == digest(replacement)
    assert entry["bytes"] == len(replacement)


def test_full_state_run_scores_districts_and_writes_verified_artifacts(
    tmp_path, monkeypatch
):
    from last_name_basis.land_records import pipeline

    shard = tmp_path / "input.parquet"
    rows = []
    for district in ("1", "district'2"):
        for account in ("a", "b"):
            rows.extend(
                adapters.owner_rows(
                    [dict(name="Test A", jati="J")],
                    district,
                    district,
                    district + account,
                    "sheet",
                    "json_info",
                    False,
                )
            )
    adapters.write_shard(shard, rows)
    monkeypatch.setattr(pipeline, "code_manifest", lambda *args: {})
    monkeypatch.setattr(
        pipeline,
        "snapshot",
        lambda *args: dict(
            state="rajasthan",
            files={"sheet": {}},
            capture_started="start",
            capture_finished="end",
        ),
    )
    monkeypatch.setattr(
        pipeline,
        "census",
        lambda *args: (
            [str(shard)],
            {"successful_attempts": 4, "audited_successful_records": 4},
            {"1"},
        ),
    )
    work = pipeline.run_state(tmp_path, tmp_path / "source", "rajasthan")
    summary = json.loads((work / "summary.json").read_text())
    assert summary["primary"]["rows"] == 4
    assert [r["rows"] for r in summary["by_district"]] == [2, 2]
    assert summary["counts"]["audited_record_numerator"] == 4
    manifest = json.loads((work / "manifest.json").read_text())
    assert summary["manifest_sha256"] == pipeline.file_checksum(work / "manifest.json")
    for name, checksum in manifest["artifacts"].items():
        assert pipeline.file_checksum(work / name) == checksum
    assert (work / "village_premium.png").exists()
    assert not (work / "analysis.duckdb").exists()


def test_normalization_sensitivity_preserves_primary_labels(tmp_path):
    from pathlib import Path

    from last_name_basis.land_records.pipeline import normalization_sensitivity

    root = Path(__file__).resolve().parents[1]
    relative = "analyses/09_odisha_village_premium/jati.py"
    store = tmp_path / "objects"
    manifest = {"pipeline_code": {relative: capture(root / relative, store)}}
    rows = [
        dict(account=str(i), village=str(i % 2), surname="S", jati="J", weight=1.0)
        for i in range(100)
    ]
    with connection(tmp_path) as con:
        con.register("eligible", pd.DataFrame(rows))
        result = normalization_sensitivity(con, manifest, store, tmp_path)
        assert result["rows"] == 100
        assert result["premium"] == 0
        assert con.execute("SELECT DISTINCT jati FROM eligible").fetchall() == [("J",)]
    assert (tmp_path / "merge_mapping.parquet").exists()


def test_name_length_census_includes_entries_without_relatives(tmp_path):
    from last_name_basis.land_records.pipeline import surname_position

    rows = [
        {"name": "रामलाल", "relative": ""},
        {"name": "राम लाल", "relative": "श्याम लाल"},
        {"name": "Test Full Name", "relative": "Parent Name"},
    ]
    with connection(tmp_path) as con:
        con.register("eligible", pd.DataFrame(rows))
        result = surname_position(con)
    assert result == {
        "eligible_name_entries": 3,
        "single_token_names": 1,
        "multitoken_names": 2,
        "entries_with_relative": 2,
        "entries_sharing_any_token": 2,
        "entries_sharing_first_token": 0,
        "entries_sharing_last_token": 2,
    }


def test_name_representation_changes_only_cue_and_preserves_account_holdout(tmp_path):
    from last_name_basis.land_records.pipeline import name_representation_sensitivity

    rows = [
        dict(account="a", village="v", name="रामलाल", jati="J", weight=1.0),
        dict(account="a", village="v", name="राम लाल", jati="J", weight=1.0),
        dict(account="b", village="v", name="राम लाल", jati="K", weight=1.0),
        dict(account="c", village="w", name="Other Name", jati="K", weight=1.0),
        dict(account="d", village="v", name="Other", jati="J", weight=1.0),
    ]
    with connection(tmp_path) as con:
        con.register("eligible", pd.DataFrame(rows))
        result = name_representation_sensitivity(con)
        assert con.execute("SELECT count(*) FROM eligible").fetchone()[0] == 5
    assert result["eligible_entries"] == 5
    assert result["distinct_recorded_names"] == 4
    assert result["distinct_spaceless_names"] == 3
    assert result["spacing_variant_groups"] == 1
    assert result["entries_in_spacing_variant_groups"] == 3
    for representation in ("whole_name", "whole_name_without_spaces"):
        transformed = [
            {
                **r,
                "surname": (
                    r["name"]
                    if representation == "whole_name"
                    else r["name"].replace(" ", "")
                ),
            }
            for r in rows
        ]
        scored = result[representation]
        assert scored["rows"] == 5
        assert scored["accounts"] == 4
        for label, cues in [
            ("surname", ["surname"]),
            ("surname_village", ["surname", "village"]),
        ]:
            assert scored["scores"][label]["error_per_100"] == pytest.approx(
                brute(transformed, cues)
            )
