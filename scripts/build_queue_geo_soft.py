#!/usr/bin/env python3
"""Shared geo softener — EMEA/UK/EU remote become ok_soft unless JD requires local work auth.
Import or copy into WA build_queue scripts (reset 2026-09-22).
"""
from __future__ import annotations
import re

WORK_AUTH_HARD = re.compile(
    r"(must (have|be)|require[sd]?|only (open|available)|right to work|work (authorization|authorisation|permit)|"
    r"citizen(ship)?|visa sponsorship not|no sponsorship|UK (only|based)|EU (only|based)|"
    r"must (live|reside|be based) (in|within)|onsite (in|at)|hybrid .{0,20}(london|berlin|paris|amsterdam))",
    re.I,
)
EU_UK_REMOTE = re.compile(
    r"(\buk\b|united kingdom|london|berlin|amsterdam|paris|stockholm|warsaw|poland|prague|"
    r"europe|\beu\b|emea|remote\s*[-–—]?\s*(uk|eu|europe|emea))",
    re.I,
)
US_ONLY = re.compile(
    r"(united states|\busa\b|remote\s*[-–—]?\s*(usa|us|united states|canada)|US (only|based)|must be (in|based in) (the )?US)",
    re.I,
)

def soften_geo_reason(reason: str, location: str = "", jd_snippet: str = "", title: str = "") -> str:
    """Map hard skip_eu_uk / skip_unclear → ok_soft when remote-friendly and no work-auth lock."""
    blob = f"{location} {jd_snippet} {title}"
    if reason == "skip_us" or (US_ONLY.search(blob) and "emea" not in blob.lower() and "worldwide" not in blob.lower()):
        if "worldwide" in blob.lower() or "work from anywhere" in blob.lower() or "wfa" in blob.lower():
            return "ok_soft"
        return reason
    if reason in ("skip_eu_uk", "skip_geo_locked", "skip_unclear"):
        if WORK_AUTH_HARD.search(blob):
            return reason  # keep hard skip
        if EU_UK_REMOTE.search(blob) or re.search(r"remote", blob, re.I):
            return "ok_soft"
    return reason
