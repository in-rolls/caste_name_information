"""One aggregate report and figure implementation for both states."""

from __future__ import annotations

import csv

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")


def number(value):
    return "unavailable" if value is None else f"{value:.2f}"


def render(summary, work):
    primary, counts = summary["primary"], summary["counts"]
    surname_error = number(primary["scores"]["surname"]["error_per_100"])
    joint_error = number(primary["scores"]["surname_village"]["error_per_100"])
    with (work / "scores.csv").open("w") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "scope",
                "cue",
                "error_per_100",
                "supported_weight",
                "total_weight",
                "fallback_weight",
                "errors",
            ],
        )
        writer.writeheader()
        for scope, scored in [
            ("state", primary),
            *[(r["district"], r) for r in summary["by_district"]],
        ]:
            for cue, result in scored["scores"].items():
                writer.writerow({"scope": scope, "cue": cue, **result})
    fig, ax = plt.subplots(figsize=(7, 4), layout="constrained")
    cues = ["blind", "surname", "village", "surname_village"]
    values = [primary["scores"][cue]["error_per_100"] for cue in cues]
    ax.bar(
        ["No cue", "Surname", "Village", "Surname + village"],
        [v if v is not None else 0 for v in values],
        color="#35678c",
    )
    for i, value in enumerate(values):
        ax.text(i, (value or 0) + 1, number(value), ha="center", fontsize=9)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Errors per 100 eligible recorded owner entries")
    ax.set_title(
        f"{summary['state'].title()}: recorded caste labels\nEntire accounts held out"
    )
    fig.savefig(work / "village_premium.png", dpi=160)
    plt.close(fig)
    lines = [
        f"# {summary['state'].title()} land records: village premium",
        "",
        f"Snapshot: {summary['capture_started']} to "
        f"{summary['capture_finished']} (UTC).",
        "",
        f"Surname error: **{surname_error}** per 100; "
        f"surname plus village: **{joint_error}**. "
        f"Village premium: **{number(primary['premium'])} percentage points**, "
        "removing "
        f"{number(primary['premium_share'])}% of surname error.",
        "",
        "![Prediction errors](out/fig/village_premium.png)",
        "",
        "## What the records support",
        "",
        "The question concerns people represented in land records. The "
        "measurable unit is a "
        "recorded owner entry after consolidating repeated account lists across plots. "
        "Entries are not verified unique people or households. Joint-owner "
        "multiplicity is "
        "retained; matching names across accounts are not automatically merged.",
        "",
        "The target is the recorded caste field, with Unicode NFC and whitespace "
        "cleanup only. "
        "The final name token is the surname proxy. Rare labels and "
        "parenthetical text remain. "
        "Results describe aggregate predictability, not individual caste identity.",
        "",
        "Each prediction excludes every eligible entry from its account. An "
        "empty cue cell "
        "falls back to the global mode after excluding that same account; a "
        "completely empty "
        "training set is unsupported. Ties follow lexical label order.",
        "",
        "The crawl is unfinished and geography was not selected at random. This "
        "is a census "
        "of saved checkpoint prefixes, not a census of either state or its "
        "landholders. "
        "Missing caste/name fields and extraction failures may be selective. The "
        "direction "
        "of incomplete-coverage bias is unknown. Bihar remains contextual: "
        "target labels, "
        "observation units and scoring protocols differ.",
        "",
        "## Census reconciliation",
        "",
        "| Quantity | Count |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items()):
        rendered = "unavailable" if value is None else f"{value:,}"
        lines.append(f'| {key.replace("_", " ")} | {rendered} |')
    lines += [
        "",
        "Audited successful-record and cell counts above are numerators; saved "
        "successful "
        "attempts and saved cells are their denominators. Failed or invalid "
        "payloads remain "
        "explicit exclusions. Fill rates cover consolidated saved entries, not "
        "the population.",
        "",
        "PDF cells reuse the source decoder’s all-page extraction. Original "
        "bytes, checksums, "
        "page-count metadata, printed account/village identity, and approved "
        "spelling evidence "
        "are retained and verified. This downstream run does not claim an "
        "independent OCR audit.",
        "",
        "Failure counts describe attempts; unresolved-source-key counts remove keys "
        "with a saved successful answer or an explicit portal miss. These are distinct "
        "from ownerless successful captures. Failure categories reflect "
        "logged reasons.",
        "",
        "## Sensitivities",
        "",
        "| Analysis | Entries | Premium (points) |",
        "|---|---:|---:|",
    ]
    for key in (
        "complete_villages",
        "signature_sensitivity",
        "normalization_sensitivity",
    ):
        if key in summary:
            value = summary[key]
            lines.append(
                f"| {key.replace('_', ' ')} | {value['rows']:,} | "
                f"{number(value['premium'])} |"
            )
    lines += [
        "",
        "The signature sensitivity collapses exact within-village matches of "
        "owner name, "
        "relative name, relation and residence when a relative is present. "
        "Conflicting caste "
        "labels are excluded from that sensitivity. Homonyms and absent "
        "relatives prevent "
        "interpreting it as verified person deduplication. Its holdout unit "
        "changes to that "
        "signature; it does not establish a bound on person-level error.",
        "",
        "Odisha normalization, when present, is the former surname-assisted "
        "merge and label-floor "
        "method. It is exploratory because the target construction sees the full "
        "surname "
        "distribution; the recorded-label primary result does not use those merges.",
        "",
        "## Surname proxy diagnostic",
        "",
    ]
    lines += [
        f'- {key.replace("_", " ")}: {value:,}'
        for key, value in summary["surname_position"].items()
    ]
    lines += [
        "",
        "Name-length counts cover every eligible owner entry, including entries "
        "without a relative. A token is whitespace-delimited: joined spellings "
        "count as one token. For a single-token name the final-token proxy is the "
        "entire recorded name; neither one nor several tokens establishes that "
        "a family name is present.",
        "",
        "Token agreement is conditional on an available relative; first and last "
        "matches "
        "can overlap. It does not establish surname position for every owner.",
        "",
        "## Whole-name and spacing comparison",
        "",
        "These checks replace the final-token cue with the entire recorded name, "
        "then compare it with the same name after removing spaces. The eligible "
        "entries, caste labels, weights and account holdout stay fixed. Space "
        "removal gives `रामलाल` and `राम लाल` the same prediction key; it does "
        "not identify word boundaries, recover a surname, or merge owner entries.",
        "",
        "| Name cue | Error per 100 | With village | Premium (points) |",
        "|---|---:|---:|---:|",
    ]
    for label, result in [
        ("Final token", summary["primary"]),
        ("Whole recorded name", summary["name_representation"]["whole_name"]),
        (
            "Whole name without spaces",
            summary["name_representation"]["whole_name_without_spaces"],
        ),
    ]:
        lines.append(
            f"| {label} | {number(result['scores']['surname']['error_per_100'])} | "
            f"{number(result['scores']['surname_village']['error_per_100'])} | "
            f"{number(result['premium'])} |"
        )
    counts = summary["name_representation"]
    lines += [
        "",
        f"Spacing-variant groups: {counts['spacing_variant_groups']:,}; "
        f"entries in those groups: {counts['entries_in_spacing_variant_groups']:,} "
        f"/ {counts['eligible_entries']:,}. A group has more than one distinct "
        "recorded spelling that becomes identical after removing spaces. "
        "Different names can also collide under this transformation, so it is "
        "reported as a sensitivity, not a verified spelling correction.",
        "",
        "## District results",
        "",
        "| District code | Entries | Premium (points) |",
        "|---|---:|---:|",
    ]
    lines += [
        f"| {r['district']} | {r['rows']:,} | {number(r['premium'])} |"
        for r in summary["by_district"]
    ]
    lines += [
        "",
        "District scores recompute the training population within each district. "
        "A pooled "
        "village cue also conveys district and region; pooled and district "
        "premiums answer "
        "different conditioning questions.",
        "",
        f"Run `{summary['run_id']}`; manifest SHA-256 `{summary['manifest_sha256']}`.",
        "",
    ]
    (work / "note.md").write_text("\n".join(lines))
