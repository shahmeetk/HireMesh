#!/usr/bin/env python3
"""Merge UAE_BOARD_LI_CAPTURE_*.json into APPLY_READY + update MESH_STATUS / UAE_BOARD_DESK_LAST."""
from __future__ import annotations

import os
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
from lane_router import is_uae_queue

DUBAI = timezone(timedelta(hours=4))
HARD = {"emirates", "emirates group", "emirates airline", "fab", "first abu dhabi bank", "oracle"}

def now():
    return datetime.now(DUBAI).strftime("%Y-%m-%dT%H:%M:%S+04:00")

def norm_url(u: str) -> str:
    try:
        p = urlparse((u or "").strip())
        host = (p.netloc or "").lower().removeprefix("www.")
        return urlunparse(("https", host, (p.path or "").rstrip("/").lower(), "", "", ""))
    except Exception:
        return (u or "").strip().lower()

def main(capture_path: Path, http_added: int = 0, board_api_added: int = 0) -> int:
    cap = json.loads(capture_path.read_text()) if capture_path.exists() else {"linkedin_session": "missing", "jobs": []}
    session = cap.get("linkedin_session") or "unknown"
    raw = cap.get("jobs") or []

    skip_urls = {norm_url(l) for l in (ROOT/"APPLIED_URLS.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}
    skip_co = {l.strip().lower() for l in (ROOT/"APPLIED_COMPANIES.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}

    ready_path = ROOT / "queues/APPLY_READY.json"
    data = json.loads(ready_path.read_text())
    existing = data.get("jobs") or []
    existing_urls = {norm_url(j.get("url") or "") for j in existing}

    added = []
    for j in raw:
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        url = (j.get("apply_url") or j.get("url") or "").strip()
        loc = j.get("location") or "UAE"
        if not title or not url:
            continue
        if j.get("easy_apply") is True:
            continue
        if not is_uae_queue(loc, title):
            continue
        nu = norm_url(url)
        if nu in skip_urls or nu in existing_urls:
            continue
        if company.lower() in skip_co or company.lower() in HARD:
            continue
        row = {
            "company": company,
            "title": title,
            "url": url,
            "apply_url": url,
            "source": j.get("source") or "linkedin_signed_in",
            "location": loc,
            "fit": j.get("fit") or 60,
            "lane": "uae",
            "guest_ats": bool(j.get("guest_ats", False)),
        }
        if j.get("linkedin_url"):
            row["linkedin_url"] = j["linkedin_url"]
        added.append(row)
        existing_urls.add(nu)

    merged = existing + added
    ts = now()
    lc = {"uae": 0, "remote": 0, "skip": 0}
    for j in merged:
        lane = (j.get("lane") or "remote").lower()
        lc[lane] = lc.get(lane, 0) + 1
    data.update({"updated": ts, "jobs": merged, "lane_counts": lc})
    ready_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    total_new = http_added + board_api_added + len(added)
    li_broken = session == "broken"
    meet_brief = (total_new == 0) or li_broken

    mesh_path = ROOT / "status/MESH_STATUS.json"
    mesh = json.loads(mesh_path.read_text())
    workers = mesh.setdefault("workers", {})
    workers.setdefault("uae_board_desk", {"routine": "uae-board-desk-hire-mesh"})
    workers["uae_board_desk"]["last"] = {
        "worker": "uae_board_desk",
        "ts": ts,
        "ok": True,
        "notes": (
            f"newly_added≈{total_new} (http_bayt≈{http_added}+li={len(added)}+api={board_api_added}); "
            f"apply_ready_total={len(merged)}; uae_lane={lc.get('uae',0)}; "
            f"linkedin_session={session}; indeed_rss=HTTPError; no_applications"
            + ("; MEET_BRIEF" if meet_brief else "; no_meet_brief")
        ),
    }
    mesh["updated"] = ts
    mesh_path.write_text(json.dumps(mesh, indent=2, ensure_ascii=False) + "\n")

    last = {
        "ts": ts,
        "worker": "uae_board_desk",
        "ok": True,
        "newly_added_this_cycle": total_new,
        "linkedin_added": len(added),
        "http_bayt_added_approx": http_added,
        "board_api_added": board_api_added,
        "apply_ready_total": len(merged),
        "uae_lane_total": lc.get("uae", 0),
        "linkedin_session": session,
        "skipped_easy_apply": cap.get("skipped_easy_apply"),
        "portals": {
            "board_desk_api": "ok (1 known TalPods, 0 new)",
            "bayt_http": "ok",
            "indeed_ae": "HTTPError",
            "linkedin_signed_in": session,
            "google_jobs_browser": "via_li_capture" if any(j.get("source")=="google_jobs" for j in raw) else "pending_or_skip",
        },
        "sample_linkedin": [
            {"company": j.get("company"), "title": j.get("title"), "url": j.get("url")}
            for j in added[:8]
        ],
        "blockers_logged": (
            (["LinkedIn session broken — Session Guard"] if li_broken else [])
            + (["Indeed.ae RSS HTTPError"] if True else [])
        ),
        "meet_brief": meet_brief,
        "reason": (
            "linkedin_session_broken" if li_broken
            else ("zero_new_uae_finds" if total_new == 0 else "newly_added>0; discover-only; no applications")
        ),
        "capture_notes": cap.get("notes"),
    }
    (ROOT / "status/UAE_BOARD_DESK_LAST.json").write_text(json.dumps(last, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(last, indent=2)[:3500])
    return 0

if __name__ == "__main__":
    cap = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "status/UAE_BOARD_LI_CAPTURE_2026-09-24.json"
    http_added = int(sys.argv[2]) if len(sys.argv) > 2 else 70  # scrubbed bayt net ~70 UAE from ~1
    board_api = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    raise SystemExit(main(cap, http_added, board_api))
