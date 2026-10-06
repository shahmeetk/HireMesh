#!/usr/bin/env python3
"""Mail Guard — harvest bounce DSNs and verify published hiring emails.

Writes status/BOUNCES.json and queues/EMAIL_SAFE.json.
Never invents careers@ / hello@ addresses.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
QUEUES = ROOT / "queues"
STATUS = ROOT / "status"

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
# Reject invented/generic guesses
BLOCKED_LOCAL = {"hello", "info", "admin", "support", "team", "hr", "jobs"}


def is_published_hiring(addr: str) -> bool:
    local = addr.split("@", 1)[0].lower()
    if local in BLOCKED_LOCAL:
        return False
    # Prefer explicit hiring local-parts seen on careers pages
    return any(k in local for k in ("career", "recruit", "talent", "hiring", "apply", "people"))


def merge_safe(addresses: list[dict]) -> dict:
    path = QUEUES / "EMAIL_SAFE.json"
    QUEUES.mkdir(parents=True, exist_ok=True)
    existing = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            existing = {}
    by_co = existing.get("by_company", {}) if isinstance(existing, dict) else {}
    for row in addresses:
        co = (row.get("company") or "").strip()
        email = (row.get("email") or "").strip().lower()
        if not co or not email or not is_published_hiring(email):
            continue
        by_co[co] = {"email": email, "source": row.get("source", "careers_page"), "verified_at": datetime.now(timezone.utc).isoformat()}
    out = {"updated": datetime.now(timezone.utc).isoformat(), "by_company": by_co}
    path.write_text(json.dumps(out, indent=2))
    return out


def write_bounces(rows: list[dict]) -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    payload = {"worker": "mail_guard", "ts": datetime.now(timezone.utc).isoformat(), "bounces": rows}
    (STATUS / "BOUNCES.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    # Agent layer supplies harvested DSNs / careers-page emails via stdin or a file.
    harvest_path = STATUS / "MAIL_GUARD_HARVEST.json"
    rows = []
    if harvest_path.exists():
        data = json.loads(harvest_path.read_text())
        rows = data if isinstance(data, list) else data.get("items", [])
    bounces = [r for r in rows if r.get("type") == "bounce"]
    safe = [r for r in rows if r.get("type") == "published_email"]
    write_bounces(bounces)
    merged = merge_safe(safe)
    print(json.dumps({"ok": True, "bounces": len(bounces), "safe_companies": len(merged.get("by_company", {}))}))


if __name__ == "__main__":
    main()
