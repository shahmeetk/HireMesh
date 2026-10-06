#!/usr/bin/env python3
"""Story Bank — weekly STAR refresh from master resume themes + recent JDs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"
CANDIDATE = os.environ.get("CANDIDATE_NAME", "{{CANDIDATE_NAME}}")

TEMPLATES = [
    ("Cloud migration", "Situation: legacy estate. Task: land a multi-cloud landing zone. Action: ... Result: ..."),
    ("Platform reliability", "Situation: noisy on-call. Task: cut MTTR. Action: ... Result: ..."),
    ("AI / LLMOps", "Situation: team wants GenAI in prod. Task: safe platform. Action: ... Result: ..."),
    ("FinOps", "Situation: spend growth. Task: unit economics. Action: ... Result: ..."),
    ("Leadership", "Situation: new org. Task: hire + set operating cadence. Action: ... Result: ..."),
]


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Story Bank — {CANDIDATE}\n",
        f"_Refreshed {datetime.now(timezone.utc).isoformat()}_\n",
        "Use before screens. Keep facts true; fill Actions/Results from your resume.\n",
    ]
    for title, stub in TEMPLATES:
        lines.append(f"## {title}\n{stub}\n")
    # Optional: pull recent JD themes
    ready = ROOT / "queues" / "APPLY_READY.json"
    if ready.exists():
        try:
            data = json.loads(ready.read_text())
            jobs = data if isinstance(data, list) else data.get("jobs", [])
            themes = sorted({j.get("title", "") for j in jobs[:20] if j.get("title")})
            if themes:
                lines.append("## Recent JD title themes\n")
                for t in themes[:12]:
                    lines.append(f"- {t}\n")
        except json.JSONDecodeError:
            pass
    (STATUS / "STORY_BANK.md").write_text("".join(lines))
    print(json.dumps({"ok": True, "stories": len(TEMPLATES)}))


if __name__ == "__main__":
    main()
