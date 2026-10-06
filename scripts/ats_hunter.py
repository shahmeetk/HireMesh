#!/usr/bin/env python3
"""ATS Hunter — prefer guest Greenhouse/Lever/Workable/Ashby apply paths.

Reads APPLY_READY.json (guest_ats=true first), attempts confirmable guest ATS
submit, writes status/HUNTER_RESULTS.json and updates APPLIED_* ledgers.
Never invents emails; defers to Mail Guard / EMAIL_SAFE for email fallback.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
QUEUES = ROOT / "queues"
STATUS = ROOT / "status"


def load_ready(limit: int = 20) -> list[dict]:
    path = QUEUES / "APPLY_READY.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    jobs = data if isinstance(data, list) else data.get("jobs", [])
    guest = [j for j in jobs if j.get("guest_ats")]
    other = [j for j in jobs if not j.get("guest_ats")]
    return (guest + other)[:limit]


def already_applied(company: str, url: str) -> bool:
    cos = {l.strip().lower() for l in (ROOT / "APPLIED_COMPANIES.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}
    urls = {l.strip().rstrip("/").lower() for l in (ROOT / "APPLIED_URLS.txt").read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#")}
    return company.strip().lower() in cos or (url or "").rstrip("/").lower() in urls


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    results = []
    for job in load_ready():
        company = job.get("company", "")
        url = job.get("url", "")
        if already_applied(company, url):
            results.append({"company": company, "url": url, "status": "skipped_dedupe"})
            continue
        # Platform-specific submit is delegated to the agent/browser layer.
        results.append({
            "company": company,
            "title": job.get("title"),
            "url": url,
            "ats": job.get("ats") or job.get("source"),
            "status": "queued_for_guest_submit",
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    out = {"worker": "ats_hunter", "ts": datetime.now(timezone.utc).isoformat(), "results": results}
    (STATUS / "HUNTER_RESULTS.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({"ok": True, "n": len(results)}))


if __name__ == "__main__":
    main()
