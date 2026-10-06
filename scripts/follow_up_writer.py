#!/usr/bin/env python3
"""Follow-Up Writer — draft D+3 / D+7 / D+14 nudges. NEVER sends."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
INBOX = ROOT / "inbox"
STATUS = ROOT / "status"
CANDIDATE = os.environ.get("CANDIDATE_NAME", "{{CANDIDATE_NAME}}")


def load_applies() -> list[dict]:
    log = ROOT / "APPLY_LOG.json"
    if not log.exists():
        # fallback markdown parse not implemented; expect JSONL/JSON
        alt = STATUS / "FUNNEL.json"
        if alt.exists():
            data = json.loads(alt.read_text())
            return data.get("applied", [])
        return []
    data = json.loads(log.read_text())
    return data if isinstance(data, list) else data.get("applies", [])


def draft_for(job: dict, day: int) -> str:
    company = job.get("company", "Company")
    title = job.get("title", "the role")
    return (
        f"### {company} — {title} (D+{day})\n"
        f"To: (hiring contact)\n"
        f"Subject: Following up — {title} application\n\n"
        f"Hi,\n\n"
        f"I applied for the {title} role about {day} days ago and remain very interested.\n"
        f"Happy to share a short note on how my Cloud/Platform/AI background maps to your needs.\n\n"
        f"Best,\n{CANDIDATE}\n"
    )


def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    drafts = ["# Follow-up drafts (DO NOT AUTO-SEND)\n", f"_Generated {now.isoformat()}_\n"]
    for job in load_applies():
        ts = job.get("applied_at") or job.get("ts")
        if not ts:
            continue
        try:
            applied = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (now - applied).days
        for day in (3, 7, 14):
            if age >= day and not job.get(f"followed_up_d{day}"):
                drafts.append(draft_for(job, day))
    (INBOX / "FOLLOWUPS.md").write_text("\n".join(drafts))
    print(json.dumps({"ok": True, "sections": len(drafts) - 2}))


if __name__ == "__main__":
    main()
