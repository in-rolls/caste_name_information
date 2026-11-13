"""Shared drawing vocabulary, so the analyses read as one argument.

Everything is expressed in mistakes per hundred -- the unit the question is
actually asked in -- and the hundred-square grid is the recurring device.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

INK = "#1c1c1c"
ACCENT = "#b8322f"
MUTED = "#9a9a9a"

# Categorical fill for caste-like groups, ordered so the first colors read as
# the marked categories and the last as the residual.
CATEGORY_FILL = ["#8d2420", "#e0a33e", "#5c7a8f", "#8f6f9e", "#7d9a6b", "#d3d3d3"]


def use_devanagari() -> bool:
    """Append a Devanagari face to the font stack, if one is installed.

    Bihar place names arrive in Devanagari; without this they render as tofu
    boxes. Returns whether a usable face was found, so callers can fall back to
    generic wording rather than printing squares.
    """
    from matplotlib import font_manager, rcParams

    installed = {f.name for f in font_manager.fontManager.ttflist}
    for face in ("Kohinoor Devanagari", "Devanagari Sangam MN", "ITF Devanagari"):
        if face in installed:
            # Devanagari face first: matplotlib falls through the list per
            # glyph, and these faces carry Latin too, so nothing else breaks.
            rcParams["font.family"] = ["sans-serif"]
            rcParams["font.sans-serif"] = [face, "DejaVu Sans"] + [
                f for f in rcParams["font.sans-serif"] if f != face
            ]
            return True
    return False


def style_axes(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(MUTED)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=9)
    ax.grid(axis="y", color="#e6e6e6", lw=0.6)
    ax.set_axisbelow(True)


def allocate(shares: np.ndarray, total: int = 100) -> np.ndarray:
    """Largest-remainder allocation, so a picture of a hundred is exact.

    Allocate across *bands*, not across items: across items the commonest few
    take every square and the long tail vanishes, which in this data is 40% of
    people.
    """
    shares = np.asarray(shares, dtype=float)
    raw = shares / shares.sum() * total
    base = np.floor(raw).astype(int)
    for i in np.argsort(-(raw - base))[: total - base.sum()]:
        base[i] += 1
    return base


def waffle(ax, fills: list[str], size: float = 0.86, lw: float = 1.2) -> None:
    """Draw one hundred squares, filled in reading order."""
    for i, fill in enumerate(fills):
        ax.add_patch(
            plt.Rectangle(
                (i % 10, 9 - i // 10),
                size,
                size,
                facecolor=fill,
                edgecolor="white",
                lw=lw,
            )
        )
    ax.set_xlim(-0.2, 10.1)
    ax.set_aspect("equal")
    ax.axis("off")


def mistake_bands(baseline: float) -> list[tuple[float, str, str]]:
    """Bands of "how many of a hundred would you get wrong", against the rate
    for someone you know nothing about. The last band is the group a name makes
    *harder*, which is a direction rather than a small amount, so it gets its
    own hue instead of a paler red."""
    return [
        (5.0, "#8d2420", "all but settles it"),
        (15.0, "#c99a97", "narrows it a lot"),
        (baseline, "#dcdcdc", "barely helps"),
        (float("inf"), "#8d9aa8", "harder than knowing nothing"),
    ]


def band_of(mistakes: float, bands) -> int:
    return next(i for i, (hi, _, _) in enumerate(bands) if mistakes < hi)
