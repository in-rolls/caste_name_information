"""Checkpoint dispositions, separate from extraction and its parser cache."""

from collections import Counter

from .storage import records

KINDS = (
    "timeout",
    "dns",
    "http",
    "pdf_source",
    "pdf_provenance",
    "pdf_decoder",
    "other",
)


def failure_kind(row):
    text = str(row.get("error") or row.get("reason") or "")
    lower = text.lower()
    if "PDFSourceIncompleteError" in text or text.startswith("PDF source:"):
        return "pdf_source"
    if "PDFProvenanceError" in text or "provenance" in lower:
        return "pdf_provenance"
    if "pdf" in lower and ("extract" in lower or "decode" in lower):
        return "pdf_decoder"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "name resolution" in lower or "dns" in lower:
        return "dns"
    if "http" in lower:
        return "http"
    return "other"


def dispositions(path, state):
    """Count attempts and exact unresolved source keys without parsing names."""
    counts = Counter(
        {
            key: 0
            for key in (
                "failed_attempts",
                "portal_miss_attempts",
                "failed_attempts_without_identity",
                "unresolved_failed_source_keys",
                "unique_successful_source_keys",
            )
        }
    )
    for kind in KINDS:
        counts[f"{kind}_failed_attempts"] = 0
        counts[f"{kind}_unresolved_keys"] = 0
    successful, absent, failures = set(), set(), {}
    for row in records(path, Counter()):
        if row.get("done"):
            continue
        key = row.get("khatiyan_value" if state == "odisha" else "plotno")
        valid_key = isinstance(key, str) and bool(key.strip())
        if row.get("ok"):
            if valid_key:
                successful.add(key)
        elif state == "rajasthan" and row.get("reason") == "miss":
            counts["portal_miss_attempts"] += 1
            if valid_key:
                absent.add(key)
        else:
            counts["failed_attempts"] += 1
            kind = failure_kind(row)
            counts[f"{kind}_failed_attempts"] += 1
            if valid_key:
                failures[key] = kind
            else:
                counts["failed_attempts_without_identity"] += 1
    for key, kind in failures.items():
        if key not in successful and key not in absent:
            counts["unresolved_failed_source_keys"] += 1
            counts[f"{kind}_unresolved_keys"] += 1
    counts["unique_successful_source_keys"] = len(successful)
    return dict(counts)
