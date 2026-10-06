#!/usr/bin/env python3
"""Session Guard — probe Gmail / LinkedIn / Reactive Resume AI at set hours.

Writes status/SESSION_GUARD.json. Notifies only on failures.
Never pauses Scout / Apply Engine / ATS Hunter.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"


def probe_rxresu() -> dict:
    # Prefer dedicated probe script if present
    probe = Path(__file__).resolve().parent / "rxresu_ai_probe.py"
    if probe.exists():
        import subprocess, sys
        try:
            subprocess.run([sys.executable, str(probe)], check=False, timeout=60)
        except Exception as e:
            return {"ok": False, "error": str(e)}
    status_path = STATUS / "RXRESU_AI_STATUS.json"
    if status_path.exists():
        try:
            return json.loads(status_path.read_text())
        except json.JSONDecodeError:
            return {"ok": False, "error": "bad_rxresu_status"}
    return {"ok": None, "error": "no_probe_result"}


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    # Agent/browser layer should write Gmail/LinkedIn probe results into harvest file
    harvest = STATUS / "SESSION_GUARD_HARVEST.json"
    gmail = {"ok": None}
    linkedin = {"ok": None}
    if harvest.exists():
        try:
            h = json.loads(harvest.read_text())
            gmail = h.get("gmail", gmail)
            linkedin = h.get("linkedin", linkedin)
        except json.JSONDecodeError:
            pass
    rx = probe_rxresu()
    out = {
        "worker": "session_guard",
        "ts": datetime.now(timezone.utc).isoformat(),
        "gmail": gmail,
        "linkedin": linkedin,
        "reactive_resume_ai": rx,
        "healthy": bool(gmail.get("ok") and linkedin.get("ok") and rx.get("ok")),
    }
    (STATUS / "SESSION_GUARD.json").write_text(json.dumps(out, indent=2))
    # Signal health-retry whether to stay active
    (STATUS / "HEALTH_RETRY_NEEDED.json").write_text(json.dumps({"needed": not out["healthy"], "ts": out["ts"]}))
    print(json.dumps({"ok": True, "healthy": out["healthy"]}))


if __name__ == "__main__":
    main()
