"""Check generated land-record results without requiring a particular finding."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "analysis", ["09_odisha_village_premium", "12_rajasthan_land_village_premium"]
)
def test_generated_census_reconciles(analysis):
    path = ROOT / "analyses" / analysis / "out/tab/summary.json"
    if not path.exists():
        pytest.skip("analysis not built")
    summary = json.loads(path.read_text())
    if "audit_mode" not in summary:
        pytest.skip("legacy output awaits shared-pipeline rebuild")
    assert summary["audit_mode"] == "census"
    assert summary["sampling_limit"] == 0
    counts = summary["counts"]
    assert counts["consolidated_owner_entries"] == (
        counts["eligible_entries"] + counts["excluded_entries"]
    )
    assert counts["conflicting_entries_retained"] == 0
    assert summary["primary"]["rows"] == counts["eligible_entries"]
    assert len(summary["manifest_sha256"]) == 64
    results = [
        summary["primary"],
        summary["complete_villages"],
        summary["signature_sensitivity"],
        *summary["by_district"],
    ]
    if "normalization_sensitivity" in summary:
        results.append(summary["normalization_sensitivity"])
    for result in results:
        for scored in result["scores"].values():
            assert (
                0
                <= scored["errors"]
                <= scored["supported_weight"]
                <= scored["total_weight"]
            )
            if scored["supported_weight"]:
                assert scored["error_per_100"] == pytest.approx(
                    100 * scored["errors"] / scored["supported_weight"]
                )
        if result["premium"] is not None:
            assert result["premium"] == pytest.approx(
                result["scores"]["surname"]["error_per_100"]
                - result["scores"]["surname_village"]["error_per_100"]
            )
