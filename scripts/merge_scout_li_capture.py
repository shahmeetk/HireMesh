#!/usr/bin/env python3
"""Merge SCOUT_LI_CAPTURE_*.json into APPLY_READY (both lanes) + update MESH_STATUS.job_scout notes."""
from __future__ import annotations

import os
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts"))
from lane_router import classify_lane

DUBAI = timezone(timedelta(hours=4))
HARD = {
    "emirates", "emirates group", "emirates airline", "dnata",
    "fab", "first abu dhabi bank", "americana", "americana foods",
    "oracle", "oracle corporation",
}

def now():
    return datetime.now(DUBAI).strftime("%Y-%m-%dT%H:%M:%S+04:00")

def norm_url(u: str) -> str:
    try:
        p = urlparse((u or "").strip())
        host = (p.netloc or "").lower().removeprefix("www.")
        return urlunparse(("https", host, (p.path or "").rstrip("/").lower(), "", "", ""))
    except Exception:
        return (u or "").strip().lower()

def main(capture_path: Path) -> int:
    cap = json.loads(capture_path.read_text()) if capture_path.exists() else {"linkedin_session": "missing", "jobs": []}
    session = cap.get("linkedin_session") or "unknown"
    raw = cap.get("jobs") or []

    skip_urls = {norm_url(l) for l in (ROOT/"APPLIED_URLS.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}
    skip_co = {l.strip().lower() for l in (ROOT/"APPLIED_COMPANIES.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}

    ready_path = ROOT / "queues/APPLY_READY.json"
    data = json.loads(ready_path.read_text())
    existing = data.get("jobs") or []
    existing_urls = {norm_url(j.get("url") or "") for j in existing}
    existing_urls |= {norm_url(j.get("apply_url") or "") for j in existing}

    added = []
    skipped_ez = int(cap.get("skipped_easy_apply") or 0)
    for j in raw:
        title = (j.get("title") or "").strip()
        company = (j.get("company") or "").strip()
        url = (j.get("apply_url") or j.get("url") or "").strip()
        loc = j.get("location") or ""
        if not title or not url:
            continue
        if j.get("easy_apply") is True:
            skipped_ez += 1
            continue
        # Never queue LinkedIn Easy-Apply-only links as apply URL
        if "linkedin.com" in url.lower() and "/jobs/" in url.lower():
            continue
        lane = (j.get("lane") or "").lower()
        if lane not in ("uae", "remote"):
            lane = classify_lane(loc, title, j.get("description") or "")
            if lane == "skip":
                continue
        nu = norm_url(url)
        if nu in skip_urls or nu in existing_urls:
            continue
        cl = company.lower()
        if cl in skip_co or cl in HARD or any(h in cl for h in HARD):
            continue
        row = {
            "company": company,
            "title": title,
            "url": url,
            "apply_url": url,
            "source": j.get("source") or "linkedin_signed_in",
            "location": loc or ("UAE" if lane == "uae" else "Remote"),
            "fit": j.get("fit") or 60,
            "lane": lane,
            "guest_ats": bool(j.get("guest_ats", False)),
        }
        if j.get("linkedin_url"):
            row["linkedin_url"] = j["linkedin_url"]
        added.append(row)
        existing_urls.add(nu)

    merged = existing + added
    # Daytime: UAE first, then by fit
    hour = datetime.now(DUBAI).hour
    if 8 <= hour < 18:
        merged.sort(key=lambda x: (0 if x.get("lane") == "uae" else 1, -(x.get("fit") or 0)))
    else:
        merged.sort(key=lambda x: (0 if x.get("lane") == "remote" else 1, -(x.get("fit") or 0)))

    ts = now()
    lc = {"uae": 0, "remote": 0, "skip": 0}
    for j in merged:
        lane = (j.get("lane") or "remote").lower()
        lc[lane] = lc.get(lane, 0) + 1
    data.update({"updated": ts, "jobs": merged, "lane_counts": lc})
    ready_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    # Append LI note onto job_scout last without wiping scout metrics
    status_path = ROOT / "status/MESH_STATUS.json"
    mesh = json.loads(status_path.read_text())
    js = mesh.setdefault("workers", {}).setdefault("job_scout", {})
    last = js.get("last") or {}
    base_notes = last.get("notes") or ""
    li_note = (
        f"li_session={session}; li_added={len(added)}; "
        f"li_skipped_easy_apply={skipped_ez}; apply_ready_after_li={len(merged)}; "
        f"lanes_after_li={lc}"
    )
    last.update({
        "worker": "job_scout",
        "ts": ts,
        "ok": True,
        "linkedin_session": session,
        "linkedin_added": len(added),
        "notes": (base_notes + "; " + li_note).strip("; "),
    })
    js["last"] = last
    status_path.write_text(json.dumps(mesh, indent=2, ensure_ascii=False) + "\n")

    # Session Guard if broken
    if session in ("login_wall", "logged_out", "missing"):
        sg_path = ROOT / "status/SESSION_GUARD.json"
        sg = json.loads(sg_path.read_text()) if sg_path.exists() else {}
        blockers = list(sg.get("blockers") or [])
        blockers.append({
            "ts": ts,
            "service": "linkedin",
            "status": session,
            "source": "job_scout",
            "notes": cap.get("notes") or "LinkedIn session broken during Discovery Scout",
        })
        sg.update({
            "updated": ts,
            "linkedin": session,
            "blockers": blockers[-20:],
            "continued_pipeline": True,
        })
        sg_path.write_text(json.dumps(sg, indent=2, ensure_ascii=False) + "\n")

    print("=== LI_MERGE_REPORT ===")
    print(f"session={session}")
    print(f"raw={len(raw)}")
    print(f"added={len(added)}")
    print(f"apply_ready={len(merged)}")
    print(f"lane_counts={lc}")
    print(f"skipped_easy_apply={skipped_ez}")
    for j in added[:8]:
        print(f"  + [{j['lane']}] {j['company']} — {j['title']}")
    return 0

if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "status/SCOUT_LI_CAPTURE_2026-09-24.json"
    raise SystemExit(main(path))
