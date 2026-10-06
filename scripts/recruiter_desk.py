#!/usr/bin/env python3
"""Recruiter Desk — draft replies to inbound recruiter threads. NEVER sends."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
INBOX = ROOT / "inbox"
STATUS = ROOT / "status"
CANDIDATE = os.environ.get("CANDIDATE_NAME", "{{CANDIDATE_NAME}}")


def main() -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    harvest = STATUS / "RECRUITER_DESK_HARVEST.json"
    threads = []
    if harvest.exists():
        data = json.loads(harvest.read_text())
        threads = data if isinstance(data, list) else data.get("threads", [])
    lines = ["# Recruiter reply drafts (DO NOT AUTO-SEND)\n", f"_Generated {datetime.now(timezone.utc).isoformat()}_\n"]
    for t in threads:
        company = t.get("company", "Company")
        lines.append(
            f"### Thread: {t.get('subject', '(no subject)')}\n"
            f"From: {t.get('from', 'recruiter@example.com')} ({company})\n\n"
            f"Hi {{FirstName}},\n\n"
            f"Thanks for reaching out — I am interested in learning more about the role at {company}. "
            f"I am targeting UAE-based or fully-remote Cloud/Platform/AI leadership roles.\n\n"
            f"Happy to share availability for a short intro.\n\n"
            f"Best,\n{CANDIDATE}\n"
        )
    (INBOX / "RECRUITER_DRAFTS.md").write_text("\n".join(lines))
    print(json.dumps({"ok": True, "drafts": len(threads)}))


if __name__ == "__main__":
    main()
