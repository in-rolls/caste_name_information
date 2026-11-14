from pathlib import Path

import pandas as pd
import pytest

from last_name_basis.upnaam import iter_resolved_roll, resolved_roll_path


def _write_artifact(path: Path, *, source_rows: list[int] | None = None) -> None:
    rows = source_rows or [0, 1]
    pd.DataFrame(
        {
            "source_row": rows,
            "state": ["maharashtra", "maharashtra"],
            "name_raw": ["patil ashwini", "sattar"],
            "weight": [3, 2],
            "surname": ["patil", None],
            "surname_position": ["first", None],
            "abstained": [False, True],
            "resolver_revision": ["resolver-v1", "resolver-v1"],
        }
    ).to_parquet(path, index=False)


def test_iter_resolved_roll_preserves_validated_rows(tmp_path: Path) -> None:
    path = tmp_path / "maharashtra.parquet"
    _write_artifact(path)
    batches = list(iter_resolved_roll(path, state="maharashtra", batch_size=1))
    result = pd.concat(batches, ignore_index=True)
    assert list(result["source_row"]) == [0, 1]
    assert result["weight"].sum() == 5
    assert result.loc[0, "surname"] == "patil"
    assert result.loc[1, "abstained"]


def test_iter_resolved_roll_rejects_broken_row_contract(tmp_path: Path) -> None:
    path = tmp_path / "maharashtra.parquet"
    _write_artifact(path, source_rows=[0, 2])
    with pytest.raises(ValueError, match="not consecutive"):
        list(iter_resolved_roll(path, state="maharashtra"))


def test_iter_resolved_roll_rejects_wrong_revision(tmp_path: Path) -> None:
    path = tmp_path / "maharashtra.parquet"
    _write_artifact(path)
    frame = pd.read_parquet(path)
    frame["resolver_revision"] = "resolver-v0"
    frame.to_parquet(path, index=False)
    with pytest.raises(ValueError, match="revision"):
        list(iter_resolved_roll(path, state="maharashtra"))


def test_resolved_roll_path_is_state_scoped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_DIR", str(tmp_path))
    assert resolved_roll_path("bihar") == (
        tmp_path / "in-rolls/upnaam/data/derived/resolved/bihar.parquet"
    )
