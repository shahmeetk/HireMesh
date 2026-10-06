#!/usr/bin/env python3
"""Reply Radar — classify inbound recruiter/ATS mail into FUNNEL stages. Never auto-replies."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"

STAGES = ("applied", "replied", "screen", "interview", "offer", "rejected")


def classify(subject: str, body: str) -> str:
    text = f"{subject} {body}".lower()
    if any(k in text for k in ("offer", "compensation package", "welcome aboard")):
        return "offer"
    if any(k in text for k in ("interview", "panel", "onsite", "loop")):
        return "interview"
    if any(k in text for k in ("phone screen", "intro call", "recruiter call", "schedule a call")):
        return "screen"
    if any(k in text for k in ("unfortunately", "not moving forward", "other candidates")):
        return "rejected"
    if any(k in text for k in ("thanks for applying", "received your application", "next steps")):
        return "replied"
    return "replied"


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    harvest = STATUS / "REPLY_RADAR_HARVEST.json"
    items = []
    if harvest.exists():
        data = json.loads(harvest.read_text())
        items = data if isinstance(data, list) else data.get("messages", [])
    funnel_path = STATUS / "FUNNEL.json"
    funnel = {"stages": {s: [] for s in STAGES}, "updated": None}
    if funnel_path.exists():
        try:
            funnel = json.loads(funnel_path.read_text())
        except json.JSONDecodeError:
            pass
    alerts = []
    for m in items:
        stage = classify(m.get("subject", ""), m.get("body", ""))
        row = {
            "company": m.get("company"),
            "subject": m.get("subject"),
            "stage": stage,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        funnel.setdefault("stages", {}).setdefault(stage, []).append(row)
        if stage in ("screen", "interview", "offer"):
            alerts.append(row)
    funnel["updated"] = datetime.now(timezone.utc).isoformat()
    funnel_path.write_text(json.dumps(funnel, indent=2))
    print(json.dumps({"ok": True, "processed": len(items), "alerts": alerts}))


if __name__ == "__main__":
    main()
