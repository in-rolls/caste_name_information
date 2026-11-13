"""Figures for the Bihar ladders. Same drawing vocabulary as analysis 01."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from last_name_basis.style import (  # noqa: E402
    ACCENT,
    CATEGORY_FILL,
    INK,
    MUTED,
    allocate,
    style_axes,
    use_devanagari,
    waffle,
)

# Only two lines. The plain five-category series sits within a point of the
# Muslims-split-out one at every rung, so drawing both is collision, not
# information; the note says so in a sentence instead.
SERIES = {
    ("records", "jati"): (INK, "jati — 141 of them"),
    ("records", "category_religion"): (
        ACCENT,
        "broad category — 6 (SC, ST, EBC, BC, upper caste, Muslim)",
    ),
}


def atrophy(table: pd.DataFrame, baselines: dict, out: Path) -> None:
    """Mistakes per hundred as the geography you can place someone in coarsens."""
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    order = ["surname+village", "surname+zone", "surname+district", "surname"]
    x = np.arange(len(order))

    for key, (colour, label) in SERIES.items():
        g = table[(table["ladder"] == key[0]) & (table["target"] == key[1])]
        g = g.set_index("level").reindex(order)
        if g["mistakes_per_100"].isna().all():
            continue
        ax.plot(
            x,
            g["mistakes_per_100"],
            "-o",
            color=colour,
            lw=2.2,
            ms=7,
            label=label,
            zorder=3,
        )
        base = baselines.get(f"{key[0]}/{key[1]}")
        if base is not None:
            ax.axhline(base, color=colour, ls=":", lw=1, alpha=0.55, zorder=1)
            ax.text(
                -0.3,
                base + 1.5,
                f"knowing nothing at all — {base:.0f}",
                fontsize=8.5,
                color=colour,
                va="bottom",
            )
        for xi, yi in zip(x, g["mistakes_per_100"]):
            if not np.isnan(yi):
                ax.annotate(
                    f"{yi:.0f}",
                    (xi, yi),
                    xytext=(0, 9),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8.5,
                    color=colour,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "surname\n+ village",
            "surname\n+ zone",
            "surname\n+ district",
            "surname alone\n(statewide)",
        ],
        fontsize=9.5,
    )
    ax.set_xlim(-0.35, len(order) - 0.15)
    ax.set_ylim(0, 100)
    ax.set_ylabel("of 100 people, how many you get wrong")
    ax.set_title(
        "Caste is a local fact.\n"
        "The same surname tells you far less as the place gets bigger.",
        color=INK,
        loc="left",
        fontsize=12,
    )
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def name_vs_place(table: pd.DataFrame, baselines: dict, out: Path) -> None:
    """Neither the name nor the place is much on its own; together they are."""
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.4), sharey=True)
    combos = [
        ("jati", "jati (141 groups)"),
        ("category_religion", "category, Muslims split out (6 groups)"),
    ]
    for ax, (target, title) in zip(axes, combos):
        g = table[(table["ladder"] == "records") & (table["target"] == target)]
        g = g.set_index("level")
        rows = [
            ("knowing nothing", baselines.get(f"records/{target}"), MUTED),
            ("village alone", g["mistakes_per_100"].get("village"), MUTED),
            ("surname alone", g["mistakes_per_100"].get("surname"), "#5c7a8f"),
            ("surname + village", g["mistakes_per_100"].get("surname+village"), ACCENT),
        ]
        rows = [(lab, v, c) for lab, v, c in rows if v is not None and not np.isnan(v)]
        y = np.arange(len(rows))[::-1]
        ax.barh(y, [v for _, v, _ in rows], color=[c for _, _, c in rows], height=0.6)
        for yi, (lab, v, _) in zip(y, rows):
            ax.text(v + 1.5, yi, f"{v:.0f}", va="center", fontsize=9, color=INK)
        ax.set_yticks(y)
        ax.set_yticklabels([lab for lab, _, _ in rows], fontsize=9.5)
        ax.set_xlim(0, 105)
        ax.set_title(title, color=INK, loc="left", fontsize=10.5)
        ax.set_xlabel("mistakes per 100")
        style_axes(ax)
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        "A name without a place, or a place without a name, is worth little",
        x=0.012,
        ha="left",
        fontsize=12,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out, dpi=170)
    plt.close(fig)


def rung_waffles(
    records: pd.DataFrame,
    source,
    out: Path,
    surname: str = "\u0938\u093f\u0902\u0939",
    label: str = "Singh",
    target_mistakes: float = 13.4,
):
    """A hundred people of one surname, at three geographies.

    Surnames in this ladder are in Devanagari, not Latin: an earlier draft
    matched the string "singh" and hit two stray cells out of the 9,849 that
    \u0938\u093f\u0902\u0939 actually has.
    """
    d = records[records["jati"].notna()].copy()
    d["last"] = d["cell"].str.rsplit("|", n=1).str[-1]

    village = d[(d["level"] == "surname+village") & (d["last"] == surname)]
    if village.empty:
        return
    have_script = use_devanagari()

    # Pick the village whose error is closest to the people-weighted figure for
    # this name. The median *cell* is homogeneous -- half hold a single jati --
    # while the median *person* lives in a mixed one, so picking by cell-median
    # would show zero mistakes against a stated thirteen.
    by_cell = village.groupby("cell", observed=True)["accounts"]
    size = by_cell.sum()
    err = (1 - by_cell.max() / size) * 100
    eligible = err[size >= 50]
    if eligible.empty:
        eligible = err
    typical = (eligible - target_mistakes).abs().idxmin()
    parts = typical.split("|")
    district = parts[0]
    place = f"{parts[2]}, {district}" if have_script else "one village"

    panels = [
        (f"in a typical village\n({place})", village[village["cell"] == typical]),
        (
            (
                "anywhere in that district"
                if not have_script
                else f"anywhere in {district} district"
            ),
            d[
                (d["level"] == "surname+district")
                & (d["last"] == surname)
                & d["cell"].str.startswith(district + "|")
            ],
        ),
        ("anywhere in Bihar", d[(d["level"] == "surname") & (d["last"] == surname)]),
    ]

    # Rank jatis by the largest share they reach in ANY panel, not by total
    # accounts. Totals are dominated by the statewide panel, which left the
    # village's own majority jati uncoloured and the panel 87 squares of gray.
    reach = {}
    for _, g in panels:
        if g.empty:
            continue
        share = g.groupby("jati", observed=True)["accounts"].sum()
        share = share / share.sum()
        for jati, v in share.items():
            reach[jati] = max(reach.get(jati, 0.0), float(v))
    top = [
        j
        for j, _ in sorted(reach.items(), key=lambda kv: -kv[1])[
            : len(CATEGORY_FILL) - 1
        ]
    ]
    colour = {j: CATEGORY_FILL[i] for i, j in enumerate(top)}

    fig, axes = plt.subplots(1, 3, figsize=(10.4, 4.5))
    for ax, (title, g) in zip(axes, panels):
        if g.empty:
            ax.axis("off")
            continue
        share = (
            g.groupby("jati", observed=True)["accounts"]
            .sum()
            .sort_values(ascending=False)
        )
        counts = allocate(share.to_numpy())
        fills = []
        for jati, n in zip(share.index, counts):
            fills += [colour.get(jati, CATEGORY_FILL[-1])] * int(n)
        waffle(ax, fills)
        ax.set_ylim(-2.6, 10.2)
        ax.text(0, 10.7, title, fontsize=10.5, color=INK, va="bottom")
        wrong = round((1 - share.max() / share.sum()) * 100)
        ax.text(
            0,
            -1.2,
            f"guess the commonest jati:\nwrong {wrong} times in 100",
            fontsize=9,
            color=MUTED,
            va="top",
        )

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=colour[j], label=j) for j in top
    ] + [
        plt.Rectangle((0, 0), 1, 1, facecolor=CATEGORY_FILL[-1], label="everyone else")
    ]
    fig.legend(
        handles=handles,
        frameon=False,
        fontsize=9,
        ncol=len(handles),
        loc="lower center",
        bbox_to_anchor=(0.5, -0.02),
    )
    fig.suptitle(
        f"A hundred people called {label}, by how closely you can place them",
        x=0.012,
        ha="left",
        fontsize=12.5,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)


def hamlet_ladder(table: pd.DataFrame, out: Path) -> None:
    """The Mahadalit census, scored one rung below the village.

    Leave-one-out is drawn alongside because the hamlet cells are small -- half
    hold a single household -- and the plug-in figure would flatter them.
    """
    d = table[table["ladder"] == "mahadalit_raw"]
    order = [
        "surname+tola",
        "surname+village",
        "surname+panchayat",
        "surname+block",
        "surname+district",
        "surname",
    ]
    d = d.set_index("level").reindex(order).reset_index()
    x = np.arange(len(d))

    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    ax.plot(
        x,
        d["mistakes_per_100_loo"],
        "-o",
        color=INK,
        lw=2.4,
        ms=7,
        label="leave-one-out",
        zorder=4,
    )
    ax.plot(
        x,
        d["mistakes_per_100"],
        "--o",
        color=MUTED,
        lw=1.6,
        ms=5,
        label="plug-in",
        zorder=3,
    )
    for xi, yi in zip(x, d["mistakes_per_100_loo"]):
        ax.annotate(
            f"{yi:.0f}",
            (xi, yi),
            xytext=(0, 10),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=INK,
        )

    place = table[(table["ladder"] == "mahadalit_raw") & table["place_only"]]
    for level, style in (("tola alone", ":"), ("village alone", "-.")):
        row = place[place["level"] == level]
        if row.empty:
            continue
        v = float(row["mistakes_per_100_loo"].iloc[0])
        ax.axhline(v, color=ACCENT, ls=style, lw=1.2)
        ax.text(
            len(order) - 0.45,
            v + 0.9,
            f"{level}, no name — {v:.0f}",
            fontsize=8.5,
            color=ACCENT,
            ha="right",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(
        [
            "surname\n+ hamlet",
            "surname\n+ village",
            "surname\n+ panchayat",
            "surname\n+ block",
            "surname\n+ district",
            "surname alone\n(statewide)",
        ],
        fontsize=9,
    )
    ax.set_ylim(0, 36)
    ax.set_ylabel("of 100 households, how many you get wrong")
    ax.set_title(
        "Caste is a fact of the hamlet, not just the village\n"
        "Going one level below the village nearly halves the error again.",
        color=INK,
        loc="left",
        fontsize=12,
    )
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)
