#!/usr/bin/env python3
"""Hire Mesh · UAE Discovery — UAE-lane discover only (never apply).

Writes/merges into queues/APPLY_READY.json (UAE-tagged rows)
and updates status/MESH_STATUS.json workers.uae_board_desk.last
"""
from __future__ import annotations

import os

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
QUEUES = ROOT / "queues"
STATUS = ROOT / "status"
INBOX = ROOT / "inbox"
STATUS = ROOT / "status"
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lane_router import is_uae_queue, classify_lane  # noqa: E402
from free_discovery_apis import (  # noqa: E402
    remotive, himalayas_search, arbeitnow, greenhouse_jobs,
    linkedin_guest_jobs, LI_FAMILY_QUERIES,
)

DUBAI = timezone(timedelta(hours=4))
UAE_RE = re.compile(r"(dubai|abu dhabi|uae|united arab|sharjah|ajman|ras al khaimah|mena|middle east)", re.I)
HYBRID_OUT_RE = re.compile(r"\b(hybrid|on[- ]?site|onsite)\b", re.I)
REMOTE_OK_RE = re.compile(r"\b(remote|worldwide|wfa|anywhere|work from anywhere)\b", re.I)

UAE_QUERIES = [
    "cloud architect dubai", "platform engineer dubai", "devops dubai",
    "sre dubai", "mlops dubai", "engineering manager dubai",
    "cloud uae", "platform uae", "kubernetes dubai", "ai platform dubai",
]

# Public Greenhouse boards often used by UAE/MENA tech employers
UAE_GH = ["careem", "noon", "talabat", "amazon", "microsoft", "google", "meta", "stripe"]

FIT = re.compile(
    r"(platform|cloud|devops|sre|kubernetes|mlops|llmops|architect|staff|principal|"
    r"head of (platform|engineering|cloud|infra)|director of (platform|engineering|cloud|infra)|"
    r"engineering manager|infrastructure|ai platform)",
    re.I,
)
DROP = re.compile(r"\b(sales|account executive|sdr|bdr|marketing|recruiter)\b", re.I)



def now() -> str:
    return datetime.now(DUBAI).strftime("%Y-%m-%dT%H:%M:%S+04:00")


def norm_url(u: str) -> str:
    try:
        p = urlparse((u or "").strip())
        host = (p.netloc or "").lower().removeprefix("www.")
        return urlunparse(("https", host, (p.path or "").rstrip("/").lower(), "", "", ""))
    except Exception:
        return (u or "").strip().lower()


def is_uae_lane(loc: str, title: str = "") -> bool:
    """UAE onsite, UAE hybrid, and UAE+remote all count."""
    return is_uae_queue(loc, title)



def discover() -> list[dict]:
    raw: list[dict] = []
    for q in UAE_QUERIES:
        try:
            raw.extend(remotive(q, limit=40))
        except Exception:
            pass
        try:
            raw.extend(himalayas_search(q, page=1))
        except Exception:
            pass
    for q in ("cloud", "platform", "devops", "sre", "architect", "engineering manager", "ai", "kubernetes"):
        try:
            raw.extend(himalayas_search(q, page=1, country="AE"))
        except Exception:
            pass
    try:
        # non-remote arbeitnow pages sometimes include MENA; keep only UAE hits
        raw.extend(arbeitnow(remote=False, max_pages=2))
    except Exception:
        pass
    for board in UAE_GH:
        try:
            raw.extend(greenhouse_jobs(board))
        except Exception:
            pass

    # LinkedIn: signed-in browser is primary (Meet). Guest only if LI_GUEST=1.
    import os as _os
    if _os.environ.get("LI_GUEST", "").strip() in ("1", "true", "yes"):
        for q in LI_FAMILY_QUERIES:
            try:
                raw.extend(linkedin_guest_jobs(q, "United Arab Emirates", remote=False, starts=[0, 25]))
            except Exception:
                pass
    return raw


def main() -> int:
    skip_urls = set()
    for line in (ROOT / "APPLIED_URLS.txt").read_text(errors="ignore").splitlines():
        if line.strip() and not line.startswith("#"):
            skip_urls.add(norm_url(line))
    skip_co = set()
    for line in (ROOT / "APPLIED_COMPANIES.txt").read_text(errors="ignore").splitlines():
        if line.strip() and not line.startswith("#"):
            skip_co.add(line.strip().lower())

    raw = discover()
    kept = []
    seen = set()
    for j in raw:
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        url = j.get("url") or j.get("apply_url") or ""
        loc = j.get("location") or ""
        if not title or not url:
            continue
        if not FIT.search(title) or DROP.search(title):
            continue
        if not is_uae_lane(loc, title):
            continue
        # Skip hybrid-outside-UAE (safety)
        if HYBRID_OUT_RE.search(loc) and not UAE_RE.search(loc) and not REMOTE_OK_RE.search(loc):
            continue
        nu = norm_url(url)
        if nu in skip_urls or nu in seen:
            continue
        if company.lower() in skip_co:
            continue
        seen.add(nu)
        kept.append({
            "company": company,
            "title": title,
            "url": url,
            "apply_url": j.get("apply_url") or url,
            "source": j.get("source") or "uae_desk",
            "location": loc,
            "fit": 55,
            "lane": "uae",
            "guest_ats": False,
        })

    QUEUES.mkdir(parents=True, exist_ok=True)
    STATUS.mkdir(parents=True, exist_ok=True)
    ready_path = QUEUES / "APPLY_READY.json"
    existing = []
    if ready_path.exists():
        try:
            existing = (json.loads(ready_path.read_text()).get("jobs") or [])
        except Exception:
            existing = []
    existing_urls = {norm_url(j.get("url") or "") for j in existing}
    added = [j for j in kept if norm_url(j["url"]) not in existing_urls]
    merged = existing + added
    ts = now()
    ready_path.write_text(json.dumps({"updated": ts, "jobs": merged}, indent=2, ensure_ascii=False) + "\n")

    mesh_path = STATUS / "MESH_STATUS.json"
    data = json.loads(mesh_path.read_text()) if mesh_path.exists() else {"suite": "Hire Mesh", "workers": {}}
    workers = data.setdefault("workers", {})
    workers.setdefault("uae_board_desk", {"routine": "uae-board-desk-hire-mesh"})
    workers["uae_board_desk"]["last"] = {
        "worker": "uae_board_desk",
        "ts": ts,
        "ok": True,
        "notes": f"uae_discovered={len(kept)}; newly_added_to_apply_ready={len(added)}; apply_ready_total={len(merged)}; no_applications",
    }
    mesh_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print("=== UAE_BOARD_DESK_REPORT ===")
    print(f"ts={ts}")
    print(f"uae_discovered={len(kept)}")
    print(f"newly_added={len(added)}")
    print(f"apply_ready_total={len(merged)}")
    for j in kept[:5]:
        print(f"  {j['company']} — {j['title']} ({j['source']}, {j['location']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
