"""Three figures. Frequency-ranked or by-name only; nothing ranked by how well
a name identifies caste."""

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
    allocate,
    band_of,
    mistake_bands,
    style_axes,
)


def mistakes_by_rank(named: pd.DataFrame, baseline: float, out: Path, annotate=()):
    """Mistakes per hundred, against how common the name is.

    The gradient is a step, not a slope: the ten commonest names are the least
    help in the table, and past them the median is flat in rank. Rolling stats
    start after the top ten so the centered window cannot smear the step across
    the very names the step is about.
    """
    d = named.sort_values("n", ascending=False).reset_index(drop=True)
    rank = np.arange(1, len(d) + 1)
    mistakes = d["err"] * 100
    top = mistakes.iloc[:10]

    fig, ax = plt.subplots(figsize=(8.2, 4.9))
    ax.axvspan(0.7, 10.5, color="#f1f1f1", zorder=0)
    ax.axhspan(baseline, 100, color="#eef1f4", zorder=0)
    ax.scatter(
        rank,
        mistakes,
        s=np.clip(d["n"] / d["n"].max() * 260, 3, 260),
        alpha=0.30,
        color=INK,
        linewidths=0,
        zorder=2,
    )
    tail, tail_rank = mistakes.iloc[10:], rank[10:]
    win = 151
    med = tail.rolling(win, center=True, min_periods=25).median()
    lo = tail.rolling(win, center=True, min_periods=25).quantile(0.25)
    hi = tail.rolling(win, center=True, min_periods=25).quantile(0.75)
    ax.fill_between(tail_rank, lo, hi, color=ACCENT, alpha=0.16, lw=0, zorder=1)
    ax.plot(
        tail_rank,
        med,
        color=ACCENT,
        lw=2,
        zorder=3,
        label="rolling median past rank 10 (IQR shaded)",
    )
    ax.plot(
        [1, 10],
        [top.median()] * 2,
        color=ACCENT,
        lw=3,
        zorder=3,
        solid_capstyle="butt",
        label="median of the top 10",
    )
    ax.axhline(baseline, color=INK, ls="--", lw=1.2, zorder=3)
    ax.text(
        60,
        baseline + 1.6,
        f"a stranger — {baseline:.0f} wrong per 100",
        fontsize=8.5,
        color=INK,
    )
    ax.text(
        len(d) * 0.9,
        67,
        "above the line, the name makes it harder",
        fontsize=8.5,
        color="#5b6b7a",
        ha="right",
        va="top",
    )
    for name in annotate:
        hit = d.index[d["last_name"] == name]
        if len(hit):
            r = int(hit[0])
            ax.annotate(
                name,
                (r + 1, mistakes.iloc[r]),
                fontsize=8,
                color=ACCENT,
                xytext=(5, 4),
                textcoords="offset points",
                zorder=4,
            )
    ax.set_xscale("log")
    ax.set_xlim(0.7, len(d) * 1.15)
    ax.set_ylim(-3, 70)
    ax.set_xlabel("surname rank by how many people carry it  (1 = commonest)")
    ax.set_ylabel("of 100 people with this name, how many you get wrong")
    ax.set_title(
        "The ten commonest names are no help at all.\n"
        "Past them almost every name helps — and by about the same amount, "
        "however rare it is.",
        color=INK,
        loc="left",
        fontsize=11,
    )
    ax.legend(frameon=False, fontsize=8, loc="upper center")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def mistakes_cdf(named: pd.DataFrame, baseline: float, out: Path):
    """Cumulative share of people, by how many of a hundred you would get wrong."""
    d = named.dropna(subset=["share_roll"]).sort_values("err").copy()
    w = d["share_roll"] / d["share_roll"].sum()
    mistakes = d["err"] * 100

    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    ax.plot(mistakes, w.cumsum(), color=INK, lw=2)
    for t, colour, msg in (
        (5, ACCENT, "the name all but settles it"),
        (baseline, INK, "no better than a stranger"),
    ):
        share = float(w[mistakes.to_numpy() < t].sum())
        ax.axvline(t, color=colour, ls="--", lw=1)
        ax.annotate(
            f"{share:.0%} of people\n{msg}",
            (t, share),
            xytext=(9, -30),
            textcoords="offset points",
            fontsize=8.5,
            color=colour,
        )
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("of 100 people with this name, how many you get wrong")
    ax.set_ylabel("cumulative share of people")
    ax.set_title("Most people carry a name that barely helps", color=INK, loc="left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def err_vs_blind(named: pd.DataFrame, out: Path, annotate=()):
    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    moved = named["gain"] > 0
    ax.plot([0, 0.9], [0, 0.9], color=MUTED, ls="--", lw=1)
    ax.scatter(
        named.loc[~moved, "err_blind"],
        named.loc[~moved, "err"],
        s=np.clip(named.loc[~moved, "n"] / named["n"].max() * 400, 3, 400),
        alpha=0.30,
        color=INK,
        linewidths=0,
        label="name changes nothing",
    )
    ax.scatter(
        named.loc[moved, "err_blind"],
        named.loc[moved, "err"],
        s=np.clip(named.loc[moved, "n"] / named["n"].max() * 400, 6, 400),
        alpha=0.75,
        color=ACCENT,
        linewidths=0,
        label="name flips the guess",
    )
    for name in annotate:
        row = named[named["last_name"] == name]
        if not row.empty:
            ax.annotate(
                name,
                (row["err_blind"].iloc[0], row["err"].iloc[0]),
                fontsize=8,
                xytext=(5, 3),
                textcoords="offset points",
            )
    ax.text(0.55, 0.60, "on the line =\nname changed nothing", fontsize=8, color=MUTED)
    ax.set_xlabel("error ignoring the name (always guess the commonest category)")
    ax.set_ylabel("error using the name")
    ax.set_title(
        "For almost everyone, the name does not change the guess",
        color=INK,
        loc="left",
    )
    handles = [
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=7,
            color=INK,
            alpha=0.5,
            label=f"name changes nothing ({(~moved).sum()} names,"
            f" {named.loc[~moved, 'share'].sum():.0%} of people)",
        ),
        plt.Line2D(
            [],
            [],
            marker="o",
            ls="",
            ms=7,
            color=ACCENT,
            label=f"name flips the guess ({moved.sum()} names,"
            f" {named.loc[moved, 'share'].sum():.0%} of people)",
        ),
    ]
    ax.legend(handles=handles, frameon=False, fontsize=8, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    fig.savefig(out, dpi=170)
    plt.close(fig)


def random_hundred(named: pd.DataFrame, baseline: float, out: Path, label_top=6):
    """A hundred people drawn at random, shaded by how much their name helps.

    Weighted by how common each surname is on the electoral rolls, so the
    squares are people, not names. That weighting is the point: a randomly met
    person is very likely to be a Devi, a Singh or a Kumar.

    Squares are allocated across the bands, not across names. Allocating across
    names hands every square to the few dozen commonest ones and drops the long
    tail, which is 40% of people. Positions are then scattered with a fixed
    seed: in frequency order the pale squares bunch at the top and read as
    structure where there is none.
    """
    bands = mistake_bands(baseline)
    d = named.dropna(subset=["share_roll"]).copy()
    d["band"] = (d["err"] * 100).map(lambda m: band_of(m, bands))
    shares = np.array(
        [d.loc[d["band"] == i, "share_roll"].sum() for i in range(len(bands))]
    )
    counts = allocate(shares)

    cells = np.repeat(np.arange(len(bands)), counts)
    cells = cells[np.random.default_rng(11).permutation(len(cells))]

    fig, ax = plt.subplots(figsize=(6.6, 7.0))
    for i, band in enumerate(cells):
        x, y = i % 10, 9 - i // 10
        ax.add_patch(
            plt.Rectangle(
                (x, y), 0.86, 0.86, facecolor=bands[band][1], edgecolor="white", lw=1.3
            )
        )
    ax.set_xlim(-0.2, 10.1)
    ax.set_ylim(-0.2, 10.1)
    ax.set_aspect("equal")
    ax.axis("off")

    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=colour, label=f"{label} — {n}")
        for (_, colour, label), n in zip(bands, counts)
    ]
    top = d.nlargest(label_top, "share_roll")
    roster = ",  ".join(
        f"{s / d['share_roll'].sum() * 100:.0f} {n}"
        for n, s in zip(top["last_name"], top["share_roll"])
    )
    ax.set_title(
        "A hundred people, picked at random\n"
        f"Guess the caste of a stranger and you get {baseline:.0f} of 100 wrong.\n"
        "Each square is one person, shaded by how much their last name helps.",
        color=INK,
        loc="left",
        fontsize=11.5,
    )
    ax.legend(
        handles=handles,
        frameon=False,
        fontsize=9,
        ncol=2,
        loc="upper left",
        bbox_to_anchor=(-0.02, -0.02),
        handlelength=1.1,
        handleheight=1.1,
    )
    ax.text(
        0,
        -2.6,
        f"Among the hundred, roughly: {roster}.",
        fontsize=9,
        color=MUTED,
        va="top",
    )
    fig.tight_layout()
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)


def name_waffles(named: pd.DataFrame, names: list[str], out: Path):
    """For each name: a hundred people who have it, colored by caste category."""
    palette = {"sc": ACCENT, "st": "#e0a33e", "other": "#d3d3d3"}
    d = named.set_index("last_name").loc[names].sort_values("p_sc")

    ncol = 4
    nrow = int(np.ceil(len(d) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(9.6, 2.55 * nrow))
    for ax, (nm, r) in zip(axes.ravel(), d.iterrows()):
        counts = allocate(np.array([r["p_sc"], r["p_st"], r["p_other"]]))
        seq = np.repeat(["sc", "st", "other"], counts)
        for i, cat in enumerate(seq):
            ax.add_patch(
                plt.Rectangle(
                    (i % 10, 9 - i // 10),
                    0.82,
                    0.82,
                    facecolor=palette[cat],
                    edgecolor="white",
                    lw=0.9,
                )
            )
        ax.set_xlim(-0.2, 10.1)
        ax.set_ylim(-1.9, 10.2)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.text(0, 10.6, nm, fontsize=11, color=INK, weight="bold")
        # Name the category actually being guessed. Saying “not Dalit” next to
        # the best guess's error rate is wrong for the names where the best
        # guess *is* Dalit -- for jatav that reads 13 when it should read 87.
        said = {"SC": "Dalit", "ST": "Adivasi", "Other": "neither"}[r["guess"]]
        wrong = round(r["err"] * 100)
        ax.text(
            0,
            -1.4,
            f"{counts[0]} of 100 are Dalit\n"
            f"best guess “{said}” → wrong {wrong} time{'' if wrong == 1 else 's'}",
            fontsize=8.4,
            color=MUTED,
            va="top",
        )
    for ax in axes.ravel()[len(d) :]:
        ax.axis("off")
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=palette[k], label=v)
        for k, v in (
            ("sc", "Scheduled Caste"),
            ("st", "Scheduled Tribe"),
            ("other", "neither"),
        )
    ]
    fig.legend(
        handles=handles,
        frameon=False,
        fontsize=9,
        ncol=3,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.012),
    )
    fig.suptitle(
        "A hundred people with each name",
        x=0.02,
        ha="left",
        fontsize=12.5,
        color=INK,
        y=1.0,
    )
    fig.tight_layout(rect=(0, 0.035, 1, 0.975))
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)


def common_and_empty(
    named: pd.DataFrame, base_sc: float, out: Path, tol: float = 0.05, top: int = 15
):
    """The commonest names in India, and how little they narrow anything down."""
    d = named.dropna(subset=["roll_share"])
    near = d[(d["p_sc"] - base_sc).abs() < tol].nlargest(top, "roll_share")
    near = near.iloc[::-1]
    y = np.arange(len(near))

    fig, (a1, a2) = plt.subplots(
        1,
        2,
        figsize=(9.8, 5.6),
        sharey=True,
        gridspec_kw={"width_ratios": [1.05, 1]},
    )
    a1.barh(y, near["roll_share"] * 100, color=INK, alpha=0.82, height=0.62)
    a1.set_yticks(y)
    a1.set_yticklabels(near["last_name"], fontsize=10)
    a1.set_xlabel("share of every surname on India's electoral rolls (%)")
    a1.invert_xaxis()
    a1.yaxis.tick_right()
    a1.tick_params(axis="y", length=0, pad=10)

    a2.axvline(base_sc * 100, color=ACCENT, lw=1.4, ls="--", zorder=1)
    a2.hlines(y, base_sc * 100, near["p_sc"] * 100, color=MUTED, lw=1.4, zorder=2)
    a2.scatter(near["p_sc"] * 100, y, s=64, color=INK, zorder=3)
    a2.set_xlim(0, 100)
    a2.set_ylim(-2.6, len(near) - 0.35)
    a2.set_xlabel("of 100 people with this name, how many are Dalit")
    a2.text(
        base_sc * 100 + 1.6,
        len(near) - 0.5,
        f"everyone\n({base_sc * 100:.0f} in 100)",
        fontsize=8.5,
        color=ACCENT,
    )
    # Two names off this list, marked for scale: without them the huddle at 20
    # looks tight only because the axis was cropped to make it look tight.
    ref_y = -1.5
    a2.axhline(ref_y + 0.75, color="#e6e6e6", lw=1)
    a2.text(0, ref_y - 0.55, "for scale", fontsize=8, color=MUTED, va="top")
    for ref in ("sharma", "paswan"):
        row = named.set_index("last_name").loc[ref]
        x = row["p_sc"] * 100
        a2.scatter([x], [ref_y], s=46, color=MUTED, zorder=3)
        a2.annotate(
            f"{ref} — {x:.0f} in 100",
            (x, ref_y + 0.28),
            ha="center",
            va="bottom",
            fontsize=8.2,
            color=MUTED,
        )
    for ax in (a1, a2):
        style_axes(ax)
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        f"The commonest names in India tell you almost nothing\n"
        f"These {len(near)} names are {near['roll_share'].sum():.0%} of all "
        f"surnames on the rolls, and every one of them sits within\n"
        f"{tol * 100:.0f} points of the rate for the population at large.",
        x=0.012,
        ha="left",
        fontsize=11.5,
        color=INK,
    )
    fig.tight_layout(rect=(0, 0.045, 1, 0.955))
    fig.savefig(out, dpi=170, bbox_inches="tight")
    plt.close(fig)
