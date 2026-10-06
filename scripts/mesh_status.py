#!/usr/bin/env python3
"""Update status/MESH_STATUS.json heartbeat for a worker."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", required=True)
    ap.add_argument("--ok", action="store_true")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()
    STATUS.mkdir(parents=True, exist_ok=True)
    path = STATUS / "MESH_STATUS.json"
    data = {"suite": "HireMesh", "workers": {}}
    if path.exists():
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    data.setdefault("workers", {})[args.worker] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ok": bool(args.ok),
        "notes": args.notes,
    }
    path.write_text(json.dumps(data, indent=2))
    print(json.dumps(data["workers"][args.worker]))


if __name__ == "__main__":
    main()
