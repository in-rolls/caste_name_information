"""Figures for the concentration analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from last_name_basis.style import ACCENT, INK, MUTED, style_axes  # noqa: E402

LEVEL_STYLE = {
    "as_written": (MUTED, "-", "names as written on the roll"),
    "minus_clear": ("#c2635e", "--", "minus honorifics (devi, kaur, bai...)"),
    "minus_all": (INK, "-", "minus honorifics, singh and kumar"),
}


def concentration(curves: dict[str, np.ndarray], marks: dict, out: Path) -> None:
    """Cumulative share of people against surname rank, at all three levels."""
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    for level, (colour, ls, label) in LEVEL_STYLE.items():
        c = curves[level]
        ax.plot(
            np.arange(1, len(c) + 1),
            c * 100,
            color=colour,
            ls=ls,
            lw=2.6 if level == "minus_all" else 2.0,
            label=label,
            zorder=4,
        )
    ax.axhline(25, color=MUTED, ls=":", lw=1)
    # Stagger the labels: all three markers sit on the 25% line, so at this
    # scale their text overlaps into an unreadable smear.
    offsets = {"as_written": (-7, 11), "minus_clear": (0, -18), "minus_all": (9, 9)}
    for level, rank in marks.items():
        colour = LEVEL_STYLE[level][0]
        ax.plot([rank], [25], "o", color=colour, ms=6, zorder=6)
        ax.annotate(
            f"{rank} names",
            (rank, 25),
            xytext=offsets[level],
            textcoords="offset points",
            fontsize=8.5,
            color=colour,
            ha="right" if level == "as_written" else "left",
        )
    ax.text(1.15, 26.5, "a quarter of everyone", fontsize=8.5, color=MUTED)
    ax.set_xscale("log")
    ax.set_xlim(1, 2e6)
    ax.set_ylim(0, 101)
    ax.set_xlabel("number of surnames, commonest first")
    ax.set_ylabel("share of people covered (%)")
    ax.set_title(
        "How concentrated Indian surnames are depends on what counts as one\n"
        f"{marks['as_written']} tokens cover a quarter of India. "
        f"{marks['as_written']} real family names do not.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def title_share(table: pd.DataFrame, out: Path) -> None:
    """Share of each state whose surname slot holds a title."""
    d = table.sort_values("title_share")
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.6, 0.32 * len(d) + 1.8))
    ax.barh(
        y,
        d["clear_share"] * 100,
        color="#c2635e",
        height=0.62,
        label="honorifics (devi, kaur, bai...)",
    )
    ax.barh(
        y,
        (d["title_share"] - d["clear_share"]) * 100,
        left=d["clear_share"] * 100,
        color=INK,
        height=0.62,
        label="singh and kumar",
    )
    for yi, v in zip(y, d["title_share"]):
        ax.text(v * 100 + 1.2, yi, f"{v:.0%}", va="center", fontsize=8.5, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(d["state"], fontsize=9)
    ax.set_xlim(0, 82)
    ax.set_xlabel("share of the state whose surname slot holds a title (%)")
    ax.set_title(
        "In Punjab, three people in four have no family name on the roll\n"
        "In Tamil Nadu and Kerala, almost everybody does.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def names_for_half(table: pd.DataFrame, out: Path) -> None:
    """Names needed to cover half a state, before and after dropping titles."""
    d = table.sort_values("names_for_half")
    y = np.arange(len(d))[::-1]
    fig, ax = plt.subplots(figsize=(8.0, 0.34 * len(d) + 1.8))
    ax.hlines(
        y, d["names_for_half"], d["names_for_half_real"], color=MUTED, lw=1.4, zorder=1
    )
    ax.scatter(d["names_for_half"], y, s=44, color=MUTED, zorder=3, label="as written")
    ax.scatter(
        d["names_for_half_real"],
        y,
        s=44,
        color=INK,
        zorder=3,
        label="real family names only",
    )
    for yi, a, b in zip(y, d["names_for_half"], d["names_for_half_real"]):
        ax.text(b * 1.18, yi, f"{a:,} → {b:,}", va="center", fontsize=8, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels(d["state"], fontsize=9)
    ax.set_xscale("log")
    ax.set_xlim(1, d["names_for_half_real"].max() * 9)
    ax.set_xlabel("surnames needed to cover half the state (log scale)")
    ax.set_title(
        "Two names are half of Punjab — but both are titles\n"
        "Dropping them multiplies the north's name count and barely moves "
        "the south's.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def variant_band(raw: np.ndarray, merged: np.ndarray, moved: float, out: Path):
    """Is the long tail real, or just spelling? Draw both curves."""
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.plot(
        np.arange(1, len(raw) + 1), raw * 100, color=INK, lw=2, label="names as written"
    )
    ax.plot(
        np.arange(1, len(merged) + 1),
        merged * 100,
        color=ACCENT,
        lw=2,
        ls="--",
        label="after folding in spelling variants",
    )
    ax.set_xscale("log")
    ax.set_xlim(1, 2e6)
    ax.set_ylim(0, 101)
    ax.set_xlabel("number of surnames, commonest first")
    ax.set_ylabel("share of people covered (%)")
    ax.set_title(
        "The long tail is real names, not misspellings\n"
        f"Folding every plausible variant into its common spelling moves "
        f"{moved:.1%} of people.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def sex_marked(table: pd.DataFrame, out: Path) -> None:
    """Who carries a last name that records their sex."""
    d = table.sort_values("women_sex_marked", ascending=False)
    y = np.arange(len(d))[::-1]
    h = 0.36
    fig, ax = plt.subplots(figsize=(8.2, 0.62 * len(d) + 1.9))
    ax.barh(
        y + h / 2, d["women_sex_marked"] * 100, height=h, color=ACCENT, label="women"
    )
    ax.barh(y - h / 2, d["men_sex_marked"] * 100, height=h, color=INK, label="men")
    for yi, wv, mv in zip(y, d["women_sex_marked"], d["men_sex_marked"]):
        ax.text(
            wv * 100 + 1.2,
            yi + h / 2,
            f"{wv:.0%}",
            va="center",
            fontsize=8.5,
            color=ACCENT,
        )
        ax.text(
            mv * 100 + 1.2,
            yi - h / 2,
            f"{mv:.0%}",
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax.set_yticks(y)
    ax.set_yticklabels([s.replace("_", " ").title() for s in d["state"]], fontsize=9.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("share whose last name records their sex, not their family (%)")
    ax.set_title(
        "Four in five women in Bihar have a last name that marks their sex\n"
        "Their brothers carry the family name instead.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
