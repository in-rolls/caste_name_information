"""Figures for analysis 11."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from last_name_basis.style import ACCENT, INK, MUTED, style_axes  # noqa: E402

TIER_FILL = {"deterministic": "#8d2420", "informative": "#5c7a8f", "abstain": MUTED}


def by_cue(scores, out: Path) -> None:
    """Mistakes per hundred for each cue, on the sample and on Rajasthan.

    Left, the pooled sample with the surname alone. Right, the 2020-22
    sarpanch contestants, the only file naming a father or husband, so the
    three cues are compared on one set of people. Grey is the sample as it
    comes; red is the same rule with rows re-weighted to the state's shares.
    """
    s = scores.set_index(["sample", "cue", "fold", "weighting"])["mistakes_per_100"]
    b = scores.set_index(["sample", "cue", "fold", "weighting"])["blind_per_100"]

    panels = [
        (
            "All candidate records\n ",
            [
                ("knowing nothing", b["pooled", "surname", "district", :]),
                ("last token of the name", s["pooled", "surname", "district", :]),
                (
                    "last token, where the\nname has two or more words",
                    s["two_or_more_tokens", "surname", "district", :],
                ),
            ],
        ),
        (
            "Sarpanch contestants 2020-22,\nthe one file naming a father or husband",
            [
                ("knowing nothing", b["sarpanch_2020", "surname", "district", :]),
                ("surname", s["sarpanch_2020", "surname", "district", :]),
                (
                    "father's or husband's surname",
                    s["sarpanch_2020", "father_surname", "district", :],
                ),
                ("both", s["sarpanch_2020", "both", "district", :]),
            ],
        ),
    ]

    fig, axes = plt.subplots(
        1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1, 1.45]}
    )
    for ax, (title, rows) in zip(axes, panels):
        y = np.arange(len(rows))[::-1].astype(float)
        h = 0.34
        for yi, (label, v) in zip(y, rows):
            raw, rw = float(v["raw"]), float(v["rajasthan"])
            ax.barh(yi + h / 2, raw, height=h, color=MUTED)
            ax.barh(yi - h / 2, rw, height=h, color=ACCENT)
            ax.text(raw + 0.8, yi + h / 2, f"{raw:.0f}", va="center", fontsize=9)
            ax.text(
                rw + 0.8, yi - h / 2, f"{rw:.0f}", va="center", fontsize=9, color=ACCENT
            )
        ax.set_yticks(y)
        ax.set_yticklabels([r[0] for r in rows], fontsize=9.5)
        ax.set_xlim(0, 72)
        ax.set_xlabel("of 100 people, how many you get wrong")
        ax.set_title(title, color=INK, loc="left", fontsize=10.5)
        style_axes(ax)
        ax.grid(axis="y", visible=False)
    axes[0].text(
        1,
        len(panels[0][1]) - 1 + 0.17,
        "sample as it comes",
        va="center",
        fontsize=8,
        color="white",
    )
    axes[0].text(
        1,
        len(panels[0][1]) - 1 - 0.17,
        "re-weighted to Rajasthan",
        va="center",
        fontsize=8,
        color="white",
    )
    fig.suptitle(
        "What a Rajasthani surname gives away about caste category, "
        "scored on districts the guesser has never seen",
        x=0.01,
        y=0.98,
        ha="left",
        color=INK,
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=170)
    plt.close(fig)


def purity_vs_frequency(tokens, summary, out: Path) -> None:
    """Every token carried by 40 or more candidates: how common against how
    settled, coloured by tier.

    The settled names are rare and the common names sit near the base rate.
    A few of the commonest are labelled so the reader can see where the
    ambiguous mass lives.
    """
    fig, ax = plt.subplots(figsize=(9.6, 5.6))
    for tier, fill in TIER_FILL.items():
        t = tokens[tokens["tier"] == tier]
        ax.scatter(
            t["n"],
            100 * t["purity"],
            s=14,
            color=fill,
            alpha=0.75,
            lw=0,
            label=f"{tier} ({len(t)})",
        )
    base = summary["category_share_raw"]
    ax.axhline(100 * max(base.values()), color=MUTED, lw=0.8, ls="--")
    ax.text(
        tokens["n"].max() * 1.6,
        100 * max(base.values()) + 1.5,
        "largest category's\nshare of the sample",
        fontsize=8,
        color=MUTED,
        ha="right",
    )
    for row in tokens.head(12).itertuples():
        ax.annotate(
            row.token,
            (row.n, 100 * row.purity),
            xytext=(4, -9 if row.token in ("sharma", "lal", "kumari") else 3),
            textcoords="offset points",
            fontsize=8.5,
            color=INK,
        )
    ax.set_xscale("log")
    ax.set_xlabel("candidates carrying the surname (log scale)")
    ax.set_ylabel("share of them in the surname's largest category")
    ax.set_ylim(20, 102)
    ax.set_title(
        "The settled surnames are the rare ones; the common ones are Devi, "
        "Singh, Ram, Lal\n"
        f"{summary['tokens']['count']} surnames carried by "
        f"{summary['tokens']['min_n']}+ candidates, each placed by how many carry it "
        "and how one-sided its category is",
        color=INK,
        loc="left",
        fontsize=10.5,
    )
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
