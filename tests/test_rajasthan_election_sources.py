"""Pinned acquisition preserves the analysis's candidate-category records."""

import gzip
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from conftest import load


def _data():
    return load("11_rajasthan_surname_to_category", "data")


def _cache(tmp_path, monkeypatch, frames):
    data = _data()
    manifest = {}
    paths = {}
    for name, frame in frames.items():
        relative = f"data/{name}.csv.gz"
        payload = gzip.compress(frame.to_csv(index=False).encode(), mtime=0)
        manifest[name] = {
            "provider": "local_elections_rajasthan",
            "ref": "a" * 40,
            "path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        target = tmp_path / "cache/local_elections_rajasthan" / ("a" * 40) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        paths[name] = target
    (tmp_path / "data_sources.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(data, "__file__", str(tmp_path / "data.py"))
    monkeypatch.setenv("INDIA_DATA_HOME", str(tmp_path / "cache"))
    return data, manifest, paths


def test_cached_source_rows_keep_candidate_and_seat_categories(tmp_path, monkeypatch):
    frames = {
        "sarpanch_2020": pd.DataFrame(
            {
                "District": ["AJMER", "AJMER"],
                "NameOfContestingCandidate": ["A SHARMA", "B DEVI"],
                "FatherHusbandOfContestingCandidate": ["C SHARMA", "D RAM"],
                "CategoryOfCandidate": ["OBC", "SC"],
                "CategoryOfGramPanchayat": ["General", "SC (Woman)"],
            }
        ),
        "ward_2020": pd.DataFrame(
            {
                "District": ["AJMER"],
                "NameOfCandidate": ["E MEENA"],
                "CategoryOfWinningCandidate": ["ST"],
                "CategoryOfWard": ["General"],
            }
        ),
    }
    for year in (2005, 2010, 2015):
        frames[f"sarpanch_{year}"] = pd.DataFrame(
            {
                "dist_name": ["AJMER"],
                "name": ["F SINGH"],
                "category": ["GEN"],
                "reservation": ["General"],
            }
        )
    data, _, _ = _cache(tmp_path, monkeypatch, frames)
    with patch(
        "requests.sessions.Session.request", side_effect=AssertionError("network")
    ):
        frame, dropped = data.load()
    assert frame["source"].tolist() == [
        "sarpanch_2020",
        "sarpanch_2020",
        "ward_2020",
        "sarpanch_2005",
        "sarpanch_2010",
        "sarpanch_2015",
    ]
    assert frame["category"].tolist() == ["OBC", "SC", "ST"] + ["General"] * 3
    assert frame["seat"].tolist() == ["General", "SC (Woman)"] + ["General"] * 4
    assert frame["father"].iloc[:2].tolist() == ["C SHARMA", "D RAM"]
    assert frame["father"].iloc[2:].isna().all()
    assert dropped == {"unmappable_category": {}, "no_surname": 0}


def test_corrupt_cache_is_not_used(tmp_path, monkeypatch):
    data, _, paths = _cache(
        tmp_path, monkeypatch, {"sarpanch_2020": pd.DataFrame({"name": ["A"]})}
    )
    paths["sarpanch_2020"].write_bytes(b"changed")
    with patch(
        "requests.sessions.Session.request",
        side_effect=RuntimeError("download required"),
    ):
        with pytest.raises(RuntimeError, match="download required"):
            data.source_paths()


def test_missing_cache_requests_the_pinned_file_and_checksum(tmp_path, monkeypatch):
    data, manifest, paths = _cache(
        tmp_path, monkeypatch, {"sarpanch_2020": pd.DataFrame({"name": ["A"]})}
    )
    spec = manifest["sarpanch_2020"]
    target = paths["sarpanch_2020"]
    target.unlink()
    with patch.object(data.pooch, "retrieve", return_value=str(target)) as retrieve:
        assert data.source_paths() == {"sarpanch_2020": target}
    retrieve.assert_called_once_with(
        url=(
            f"https://raw.githubusercontent.com/in-rolls/{spec['provider']}/"
            f"{spec['ref']}/{spec['path']}"
        ),
        known_hash="sha256:" + spec["sha256"],
        path=target.parent,
        fname=target.name,
    )


def test_all_five_sources_are_pinned_to_the_same_release():
    manifest = json.loads(
        Path(_data().__file__).with_name("data_sources.json").read_text()
    )
    assert set(manifest) == {
        "sarpanch_2020",
        "ward_2020",
        "sarpanch_2005",
        "sarpanch_2010",
        "sarpanch_2015",
    }
    for spec in manifest.values():
        assert spec["provider"] == "local_elections_rajasthan"
        assert spec["ref"] == "854c415c9a4bf3beef393c170419b1bf8f41b189"
        assert len(spec["sha256"]) == 64
