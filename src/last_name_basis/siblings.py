"""Where the sister repositories this one reads from are checked out.

Several inputs are files inside other repositories rather than downloads. Each
lives under ``$GITHUB_DIR/<owner>/<repo>``, with ``GITHUB_DIR`` defaulting to
``~/Documents/GitHub``. The owner is part of the path because the checkouts are
grouped by GitHub organisation, and one table here is the only place that knows
which organisation each repository belongs to.
"""

from __future__ import annotations

import os
from pathlib import Path

OWNERS = {
    "instate": "appeler",
    "naampy": "appeler",
    "outkast": "appeler",
    "pranaam": "appeler",
    "land": "in-rolls",
    "naampata": "in-rolls",
    "ror_odisha_2026": "in-rolls",
    "ror_rajasthan_2026": "in-rolls",
    "upnaam": "in-rolls",
}


def github_dir() -> Path:
    return Path(os.environ.get("GITHUB_DIR", Path.home() / "Documents/GitHub"))


def repo(name: str) -> Path:
    """The checkout of sister repository ``name``, whether or not it exists."""
    return github_dir() / OWNERS[name] / name
