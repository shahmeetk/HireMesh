"""Hire Mesh lane router (Meet 2026-09-24).

UAE queue: any role that mentions UAE / Dubai / Abu Dhabi / Sharjah / Ajman / RAK
           including onsite, UAE hybrid, OR UAE+remote.
Remote queue: everything else (fully remote / WFA / anywhere / soft EMEA remote /
              USA hybrid / EU hybrid / other non-UAE hybrid) with no UAE location.
Skip: hard citizen / payroll-only / no-remote city locks.
"""
from __future__ import annotations
import re

UAE_RE = re.compile(
    r"\b(uae|u\.a\.e|united arab emirates|dubai|abu dhabi|abudhabi|sharjah|ajman|"
    r"ras al khaimah|ras-al-khaimah|fujairah|umm al quwain|middle east.?uae)\b",
    re.I,
)
HARD_SKIP_RE = re.compile(
    r"(us citizen(ship)? (required|only)|uk citizen(ship)? (required|only)|"
    r"eu citizen(ship)? (required|only)|must be (a )?us citizen|"
    r"united states only|usa only|\bus only\b|india only|"
    r"payroll only|no remote|onsite only|on-site only)",
    re.I,
)


def classify_lane(location: str = "", title: str = "", description: str = "") -> str:
    """Return 'uae' | 'remote' | 'skip'."""
    blob = f"{location or ''} {title or ''} {description or ''}"
    if not blob.strip():
        return "remote"
    # UAE mention always wins (UAE onsite / hybrid / UAE+remote)
    if UAE_RE.search(blob):
        return "uae"
    if HARD_SKIP_RE.search(blob):
        return "skip"
    return "remote"


def is_uae_queue(location: str = "", title: str = "", description: str = "") -> bool:
    return classify_lane(location, title, description) == "uae"
