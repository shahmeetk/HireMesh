#!/usr/bin/env python3
"""Warm Outreach — draft HM/recruiter notes for strong fits. NEVER sends."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
INBOX = ROOT / "inbox"
QUEUES = ROOT / "queues"
CANDIDATE = os.environ.get("CANDIDATE_NAME", "{{CANDIDATE_NAME}}")


def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    path = QUEUES / "APPLY_READY.json"
    jobs = []
    if path.exists():
        data = json.loads(path.read_text())
        jobs = data if isinstance(data, list) else data.get("jobs", [])
    top = sorted(jobs, key=lambda j: j.get("fit_score", 0), reverse=True)[:5]
    lines = ["# Warm-path drafts (DO NOT AUTO-SEND)\n", f"_Generated {datetime.now(timezone.utc).isoformat()}_\n"]
    for j in top:
        company = j.get("company", "Company")
        title = j.get("title", "role")
        lines.append(
            f"### {company} — {title}\n"
            f"Channel: LinkedIn or email (human send only)\n\n"
            f"Hi {{FirstName}},\n\n"
            f"I just applied for the {title} role at {company}. "
            f"I lead Cloud/Platform/AI initiatives and would value 10 minutes to learn what good looks like on your team.\n\n"
            f"Best,\n{CANDIDATE}\n"
        )
    (INBOX / "WARM_PATH.md").write_text("\n".join(lines))
    print(json.dumps({"ok": True, "drafts": len(top)}))


if __name__ == "__main__":
    main()
