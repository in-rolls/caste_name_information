"""Figures for analysis 09."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from last_name_basis.style import ACCENT, INK, MUTED, style_axes  # noqa: E402


def premium(summary: dict, out: Path) -> None:
    """What a village adds, in Bihar and in Odisha.

    The levels are not comparable: Bihar sorts people among 141 jatis and
    Odisha among several thousand labels, and the two records were collected
    differently. The distance between the two bars within each place is the
    quantity that carries across, so the figure draws that distance and labels
    the endpoints rather than inviting a comparison of heights.
    """
    g = summary["odisha"]["as recorded"]
    b = summary["bihar"]
    places = [
        (f"Bihar\n{b['groups']} jatis", b["surname"], b["surname_village"]),
        (
            f"Odisha\n{g['groups']} labels",
            g["surname"],
            g["surname_village"],
        ),
    ]

    fig, ax = plt.subplots(figsize=(9.0, 4.0))
    for i, (_, alone, with_village) in enumerate(places):
        y = len(places) - 1 - i
        ax.plot(
            [with_village, alone], [y, y], color=MUTED, lw=2.4, solid_capstyle="butt"
        )
        ax.scatter([alone], [y], s=70, color=INK, zorder=3)
        ax.scatter([with_village], [y], s=70, color=ACCENT, zorder=3)
        ax.text(alone + 1.2, y, f"{alone:.0f}", va="center", fontsize=10, color=INK)
        ax.text(
            with_village - 1.2,
            y,
            f"{with_village:.0f}",
            va="center",
            ha="right",
            fontsize=10,
            color=ACCENT,
        )
        ax.text(
            (alone + with_village) / 2,
            y + 0.17,
            f"village adds {alone - with_village:.0f}",
            ha="center",
            fontsize=9,
            color=MUTED,
        )

    ax.set_yticks(range(len(places)))
    ax.set_yticklabels([p[0] for p in reversed(places)], fontsize=10)
    ax.set_xlim(0, 60)
    ax.set_ylim(-0.6, len(places) - 0.4)
    ax.set_xlabel("mistakes per 100 households, leave-one-out")
    ax.set_title(
        "Adding a village helps less in Odisha than in Bihar\n"
        "Black: the surname alone. Red: the surname with the village. The two "
        "places sort\npeople into different numbers of groups, so compare the "
        "gaps, not the heights.",
        color=INK,
        loc="left",
        fontsize=11,
    )
    style_axes(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def atrophy(ladders: dict, blinds: dict, out: Path) -> None:
    """Both places on analysis 02's axis: error rising as the place gets bigger.

    The administrative units are not equivalent across the two states, so the
    axis is the rank of a unit's size rather than a common unit, and each rung
    is labeled with both names. What the figure shows is the shape: the two
    lines meet where the place is thrown away and separate as it is restored.
    """
    rungs = ["village", "middle", "larger", "alone"]
    x = range(len(rungs))
    colour = {"Bihar": INK, "Odisha": ACCENT}

    fig, ax = plt.subplots(figsize=(9.4, 5.4))
    # The lines cross, so a fixed offset puts two labels in the same place at
    # the rungs where they nearly touch. Each label goes above or below
    # according to which line is higher at that rung.
    top = [max(v[i] for v in ladders.values()) for i in x]
    for place, values in ladders.items():
        c = colour[place]
        ax.plot(x, values, "-o", color=c, lw=2.2, ms=8, label=place)
        for xi, v in zip(x, values):
            ax.annotate(
                f"{v:.0f}",
                (xi, v),
                textcoords="offset points",
                xytext=(0, 10 if v == top[xi] else -18),
                ha="center",
                fontsize=10,
                color=c,
            )
    # The two blind rates are a point apart, so one label per line printed at
    # the line's own height lands on top of the other. They are stacked by
    # rank instead, and each still carries its own color and number.
    for rank, (place, value) in enumerate(
        sorted(blinds.items(), key=lambda kv: -kv[1])
    ):
        c = colour[place]
        ax.axhline(value, color=c, ls=":", lw=1.1, alpha=0.6)
        ax.text(
            -0.06,
            max(blinds.values()) + 3.0 + rank * 4.2,
            f"knowing nothing, {place} \u2014 {value:.0f}",
            fontsize=8.5,
            color=c,
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(
        [
            "surname\n+ village",
            "surname\n+ zone / RI circle",
            "surname\n+ district / tahsil",
            "surname alone",
        ],
        fontsize=9.5,
    )
    ax.set_xlim(-0.15, len(rungs) - 0.85)
    ax.set_ylim(0, 100)
    ax.set_ylabel("of 100 people, how many you get wrong")
    ax.set_title(
        "Caste is a local fact in both places, and most local in Bihar\n"
        "The lines cross. Odisha is the easier target until the village "
        "arrives, and Bihar\novertakes it there. The units differ across "
        "states, so the axis ranks them by size.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(frameon=False, fontsize=10, loc="lower right")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
