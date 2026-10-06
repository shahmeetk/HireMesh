#!/usr/bin/env python3
"""Probe Reactive Resume AI tailor endpoint. Writes RXRESU_AI_STATUS.json. Exit 0=up, 1=down."""
from __future__ import annotations

import os
import json, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

API = "https://rxresu.me/api/openapi"
MASTER = os.environ.get("RXRESU_MASTER_RESUME_ID", "YOUR_MASTER_RESUME_ID")
KEY_PATH = Path(os.environ.get("RXRESU_API_KEY_PATH", os.path.expanduser("~/.config/rxresu_api_key")))
OUT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve() / "status" / "RXRESU_AI_STATUS.json"
TZ = ZoneInfo("Asia/Dubai")

def now():
    return datetime.now(TZ).isoformat(timespec="seconds")

def api_key():
    return KEY_PATH.read_text().strip()

def req(method, path, payload=None, timeout=90):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"x-api-key": api_key()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read().decode()
            try:
                return resp.status, json.loads(body)
            except Exception:
                return resp.status, body
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {path}: {err[:400]}") from e

def main():
    ts = now()
    result = {
        "ts": ts,
        "api": API,
        "master_resume": MASTER,
        "ai_ok": False,
        "health_ok": None,
        "http_status": None,
        "error": None,
        "application_id": None,
        "tailored_resume_id": None,
        "latency_ms": None,
    }
    # light health: GET master resume
    try:
        t0 = time.time()
        st, _ = req("GET", f"/resumes/{MASTER}", timeout=30)
        result["health_ok"] = st == 200
        result["http_status"] = st
    except Exception as e:
        result["health_ok"] = False
        result["error"] = f"health: {e}"
        OUT.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return 1

    # AI tailor probe
    jd = (
        "PROBE ONLY — Platform / Cloud Engineering leadership. "
        "Keywords: Kubernetes, Terraform, AWS, observability, SRE. "
        "Delete after probe."
    )
    try:
        st, app = req(
            "POST",
            "/applications",
            {
                "company": "RXRESU_AI_PROBE",
                "role": "AI Tailor Healthcheck",
                "location": "Remote",
                "source": "probe",
                "sourceUrl": "https://example.com/rxresu-ai-probe",
                "status": "saved",
                "resumeId": MASTER,
                "jobDescription": jd,
                "tags": ["probe", "do-not-apply"],
                "notes": f"AI probe {ts}",
            },
            timeout=60,
        )
        if isinstance(app, dict):
            app_id = app.get("id") or app.get("applicationId")
        elif isinstance(app, str) and app.strip():
            app_id = app.strip()
        else:
            app_id = None
        result["application_id"] = app_id
        if not app_id:
            raise RuntimeError(f"no application id: {app!r}")
        t1 = time.time()
        st2, tailored = req(
            "POST",
            f"/applications/{app_id}/ai/tailor-resume",
            {"resumeId": MASTER},
            timeout=120,
        )
        result["latency_ms"] = int((time.time() - t1) * 1000)
        result["http_status"] = st2
        rid = tailored.get("resumeId") if isinstance(tailored, dict) else None
        result["tailored_resume_id"] = rid
        result["ai_ok"] = bool(rid) and st2 == 200
        if not result["ai_ok"]:
            result["error"] = f"unexpected tailor payload: {str(tailored)[:300]}"
    except Exception as e:
        result["ai_ok"] = False
        result["error"] = str(e)[:500]
        # try extract HTTP code
        if "HTTP 502" in str(e):
            result["http_status"] = 502
        elif "HTTP 5" in str(e):
            import re
            m = re.search(r"HTTP (\d+)", str(e))
            if m:
                result["http_status"] = int(m.group(1))

    # merge history
    hist = []
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text())
            hist = prev.get("history") or []
            if prev.get("ts"):
                hist = ([{"ts": prev["ts"], "ai_ok": prev.get("ai_ok"), "http_status": prev.get("http_status"), "error": (prev.get("error") or "")[:120]}] + hist)[:40]
        except Exception:
            pass
    result["history"] = hist
    result["consecutive_down"] = 0 if result["ai_ok"] else (1 + sum(1 for h in hist if not h.get("ai_ok")))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("ts", "ai_ok", "health_ok", "http_status", "error", "latency_ms", "consecutive_down")}))
    return 0 if result["ai_ok"] else 1

if __name__ == "__main__":
    sys.exit(main())
