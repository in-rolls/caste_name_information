"""Figures for the neighbors analysis."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from last_name_basis.style import (  # noqa: E402
    ACCENT,
    INK,
    MUTED,
    style_axes,
    use_devanagari,
)


def bracket(table: pd.DataFrame, out: Path) -> None:
    """The bracket: nothing, the name, the name plus who lives around you."""
    steps = [
        ("knowing nothing", "blind", MUTED),
        ("the name alone", "surname_only", INK),
        ("the name + neighbours", "surname_plus_neighbours", ACCENT),
    ]
    fig, axes = plt.subplots(
        1, len(table), figsize=(4.6 * len(table), 4.4), squeeze=False
    )
    for ax, (_, row) in zip(axes[0], table.iterrows()):
        y = np.arange(len(steps))[::-1]
        vals = [row[c] for _, c, _ in steps]
        ax.barh(y, vals, color=[c for _, _, c in steps], height=0.55)
        for yi, v in zip(y, vals):
            ax.text(v + 1.2, yi, f"{v:.0f}", va="center", fontsize=10, color=INK)
        ax.set_yticks(y)
        ax.set_yticklabels([lab for lab, _, _ in steps], fontsize=9.5)
        ax.set_xlim(0, 100)
        ax.set_xlabel("mistakes per 100")
        ax.set_title(
            f"{row['ladder']}\n{int(row['jatis'])} jatis, "
            f"{int(row['test_villages']):,} unseen villages",
            color=INK,
            loc="left",
            fontsize=10.5,
        )
        style_axes(ax)
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        "Who lives around you helps — a little, on average",
        x=0.012,
        ha="left",
        fontsize=12.5,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(out, dpi=170)
    plt.close(fig)


def per_surname(table: pd.DataFrame, out: Path) -> None:
    """Where the average hides the answer: which names get rescued."""
    # Land-record surnames are Devanagari; without this they render as tofu.
    use_devanagari()
    d = table.sort_values("saved")
    y = np.arange(len(d))

    fig, ax = plt.subplots(figsize=(8.6, 0.42 * len(d) + 2.1))
    ax.hlines(y, d["with_neighbours"], d["alone"], color=MUTED, lw=1.3, zorder=1)
    ax.scatter(d["alone"], y, s=52, color=MUTED, zorder=3, label="name alone")
    helped = (d["saved"] > 0).to_numpy()
    ax.scatter(
        d["with_neighbours"].to_numpy()[helped],
        y[helped],
        s=52,
        color=ACCENT,
        zorder=3,
        label="+ neighbours, helps",
    )
    ax.scatter(
        d["with_neighbours"].to_numpy()[~helped],
        y[~helped],
        s=52,
        color="#8d9aa8",
        zorder=3,
        label="+ neighbours, hurts",
    )
    for yi, (a, b) in zip(y, zip(d["alone"], d["with_neighbours"])):
        ax.text(
            max(a, b) + 1.6, yi, f"{a - b:+.0f}", va="center", fontsize=8.5, color=INK
        )
    ax.set_yticks(y)
    ax.set_yticklabels(d["surname"], fontsize=10)
    ax.set_xlim(0, 100)
    ax.set_xlabel("mistakes per 100, in a village never seen before")
    ax.set_title(
        "The names that say nothing are the ones neighbours rescue\n"
        "Names that already identify you gain nothing, and a few get worse.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.set_ylim(-1.4, len(d) - 0.4)
    ax.legend(frameon=False, fontsize=9, loc="lower right", ncol=2)
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def ceiling(result: dict, held: pd.DataFrame, out: Path) -> None:
    """The whole bracket, from knowing nothing to everything the roll prints."""
    mah = held.set_index("ladder").loc["Mahadalit census"]
    steps = [
        ("knowing nothing", mah["blind"], MUTED),
        ("the surname alone", mah["surname_only"], INK),
        ("surname + neighbours", mah["surname_plus_neighbours"], "#8d9aa8"),
        (
            "+ a caste register of\nthe same population",
            result["mistakes_per_100"],
            ACCENT,
        ),
    ]
    y = np.arange(len(steps))[::-1]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    ax.barh(y, [v for _, v, _ in steps], color=[c for _, _, c in steps], height=0.56)
    for yi, (_, v, _) in zip(y, steps):
        ax.text(v + 1.0, yi, f"{v:.0f}", va="center", fontsize=10.5, color=INK)
    ax.set_yticks(y)
    ax.set_yticklabels([lab for lab, _, _ in steps], fontsize=10)
    ax.set_xlim(0, 72)
    ax.set_xlabel("of 100 households, how many you get wrong")
    ax.set_title(
        "The name is weak. The name plus a register is not.\n"
        f"{result['villages_held_out']:,} Bihar villages never seen during "
        f"fitting, {result['groups']} jatis, Scheduled Caste households.\n"
        "Caste is not printed on any roll -- the labels come from a census.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
