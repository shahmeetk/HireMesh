#!/usr/bin/env python3
"""Health Retry — dense rechecks only while Session Guard reports unhealthy."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    flag = STATUS / "HEALTH_RETRY_NEEDED.json"
    needed = True
    if flag.exists():
        try:
            needed = bool(json.loads(flag.read_text()).get("needed", True))
        except json.JSONDecodeError:
            needed = True
    if not needed:
        print(json.dumps({"ok": True, "skipped": True, "reason": "healthy"}))
        return
    guard = Path(__file__).resolve().parent / "session_guard.py"
    subprocess.run([sys.executable, str(guard)], check=False)
    state = {}
    sp = STATUS / "SESSION_GUARD.json"
    if sp.exists():
        state = json.loads(sp.read_text())
    result = {
        "worker": "health_retry",
        "ts": datetime.now(timezone.utc).isoformat(),
        "healthy": state.get("healthy"),
        "reprobe": True,
    }
    (STATUS / "HEALTH_RETRY_LAST.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
