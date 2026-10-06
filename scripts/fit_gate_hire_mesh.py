#!/usr/bin/env python3
"""Hire Mesh · Fit Gate — re-rank / prune APPLY_READY only (never apply).

Uses lane_router: UAE queue (UAE/Dubai/Abu Dhabi incl. UAE+remote/hybrid),
Remote queue (fully remote / WFA / soft EMEA / USA|EU hybrid), drop only hard skip.

Daytime (08:00–17:59 Asia/Dubai): UAE-queue first, then fit.
Evening/night: remote-queue first, then fit.
min_fit ~0.62 unless queue thin.
"""
from __future__ import annotations

import os

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
QUEUES = ROOT / "queues"
STATUS = ROOT / "status"
INBOX = ROOT / "inbox"
STATUS = ROOT / "status"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from lane_router import classify_lane  # noqa: E402

DUBAI = timezone(timedelta(hours=4))
MIN_FIT_DEFAULT = 0.62
THIN_KEEP = 40
THIN_MIN_FIT = 0.55
VERY_THIN_KEEP = 20
VERY_THIN_MIN_FIT = 0.50

WEIGHTS = {
    "title_family": 0.30,
    "stack_overlap": 0.25,
    "seniority": 0.20,
    "lane_geo": 0.15,
    "freshness": 0.05,
    "submitability": 0.05,
}

FAMILY_RE = re.compile(
    r"\b(platform|cloud|devops|sre|site reliability|aiops|mlops|llmops|"
    r"kubernetes|k8s|observability|infrastructure|infra|ai infrastructure|"
    r"ai platform|llm|engineering manager|head of platform|staff engineer|"
    r"principal|architect)\b",
    re.I,
)
STACK_RE = re.compile(
    r"\b(kubernetes|k8s|aws|gcp|azure|terraform|helm|prometheus|grafana|"
    r"datadog|kafka|istio|cilium|argocd|github actions|ci/?cd|docker|"
    r"linux|python|golang|go\b|rust|spark|airflow|ray|cuda|gpu|"
    r"openai|langchain|vector|rag|mlflow|kubeflow|observability|"
    r"platform|cloud|sre|devops|aiops|mlops|llmops)\b",
    re.I,
)
SENIOR_RE = re.compile(
    r"\b(engineering manager|head of|director|avp|vp\b|vice president|"
    r"staff|principal|architect|lead|senior|sr\.|manager)\b",
    re.I,
)
DEMOTE_RE = re.compile(
    r"\b(sales|account executive|sdr|bdr|customer success|recruiter|talent|"
    r"marketing|intern|internship|junior|graduate|entry.?level|frontend only|"
    r"react native|ios developer|android developer|php|wordpress)\b",
    re.I,
)

HARD_SKIP_COMPANIES = {
    "emirates", "emirates group", "emirates airline", "dnata",
    "fab", "first abu dhabi bank", "national bank of abu dhabi",
    "americana", "americana foods", "americana restaurants",
    "oracle", "oracle corporation",
}


def now_dubai() -> datetime:
    return datetime.now(DUBAI)


def period_label(dt: datetime) -> str:
    h = dt.hour
    if 8 <= h < 18:
        return "day_uae_priority"
    return "night_remote_priority"


def is_daytime(dt: datetime) -> bool:
    return 8 <= dt.hour < 18


def _norm_company(c: str) -> str:
    return re.sub(r"\s+", " ", (c or "").strip().lower())


def load_applied_companies() -> set[str]:
    paths = [
        ROOT / "APPLIED_COMPANIES.txt",
        ROOT / "APPLIED_URLS.txt",
    ]
    out: set[str] = set()
    # companies file
    p = ROOT / "APPLIED_COMPANIES.txt"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                out.add(_norm_company(s))
    return out


def load_applied_urls() -> set[str]:
    out: set[str] = set()
    p = ROOT / "APPLIED_URLS.txt"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip().lower()
            if s and not s.startswith("#"):
                out.add(s.rstrip("/"))
    return out


def title_family_score(title: str) -> float:
    if DEMOTE_RE.search(title or ""):
        return 0.15
    hits = len(FAMILY_RE.findall(title or ""))
    if hits >= 2:
        return 1.0
    if hits == 1:
        return 0.75
    return 0.25


def stack_score(title: str, tags: Any = None) -> float:
    blob = title or ""
    if tags:
        if isinstance(tags, list):
            blob += " " + " ".join(str(x) for x in tags)
        else:
            blob += " " + str(tags)
    hits = len(STACK_RE.findall(blob))
    if hits >= 3:
        return 1.0
    if hits == 2:
        return 0.8
    if hits == 1:
        return 0.55
    return 0.3


def seniority_score(title: str) -> float:
    t = title or ""
    if re.search(r"\b(director|head of|avp|vp\b|vice president)\b", t, re.I):
        return 1.0
    if re.search(r"\b(engineering manager|staff|principal|architect)\b", t, re.I):
        return 0.95
    if re.search(r"\b(lead|senior|sr\.|manager)\b", t, re.I):
        return 0.8
    if SENIOR_RE.search(t):
        return 0.65
    return 0.35


def lane_geo_score(lane: str, daytime: bool) -> float:
    if lane == "uae":
        return 1.0 if daytime else 0.75
    if lane == "remote":
        return 0.75 if daytime else 1.0
    return 0.0


def freshness_score(job: dict) -> float:
    # Prefer known fresh sources; default mid
    src = (job.get("source") or "").lower()
    if src in ("greenhouse", "ashby", "lever", "himalayas", "himalayas_ae", "remotive"):
        return 0.7
    if src in ("remoteok", "arbeitnow", "themuse", "weworkremotely"):
        return 0.55
    return 0.5


def submitability_score(job: dict) -> float:
    if job.get("guest_ats"):
        return 1.0
    url = (job.get("apply_url") or job.get("url") or "").lower()
    if any(x in url for x in ("greenhouse", "ashbyhq", "lever.co", "workable", "teamtailor")):
        return 0.85
    if "mailto:" in url or "@" in url:
        return 0.7
    return 0.45


def composite_score(job: dict, lane: str, daytime: bool) -> float:
    title = job.get("title") or ""
    tags = job.get("tags")
    parts = {
        "title_family": title_family_score(title),
        "stack_overlap": stack_score(title, tags),
        "seniority": seniority_score(title),
        "lane_geo": lane_geo_score(lane, daytime),
        "freshness": freshness_score(job),
        "submitability": submitability_score(job),
    }
    score = sum(WEIGHTS[k] * parts[k] for k in WEIGHTS)
    # Blend scout fit (0-100) lightly so we don't ignore prior ranking
    scout = job.get("fit")
    try:
        scout_n = max(0.0, min(1.0, float(scout) / 100.0))
        score = 0.7 * score + 0.3 * scout_n
    except (TypeError, ValueError):
        pass
    return round(max(0.0, min(1.0, score)), 4)


def sort_key(job: dict, daytime: bool):
    lane = job.get("lane") or "remote"
    score = float(job.get("fit_gate_score") or 0)
    if daytime:
        lane_rank = 0 if lane == "uae" else 1
    else:
        lane_rank = 0 if lane == "remote" else 1
    return (lane_rank, -score)


def main() -> int:
    ts = now_dubai()
    daytime = is_daytime(ts)
    period = period_label(ts)
    apply_path = QUEUES / "APPLY_READY.json"
    raw = json.loads(apply_path.read_text())
    jobs_in = list(raw.get("jobs") or [])
    applied_cos = load_applied_companies()
    applied_urls = load_applied_urls()

    scored: list[dict] = []
    dropped: list[dict] = []
    reasons: Counter = Counter()

    for j in jobs_in:
        title = j.get("title") or ""
        loc = j.get("location") or ""
        company = j.get("company") or ""
        url = (j.get("apply_url") or j.get("url") or "").strip()
        lane = classify_lane(loc, title, j.get("description") or "")

        if _norm_company(company) in HARD_SKIP_COMPANIES or _norm_company(company) in applied_cos:
            reasons["already_applied_or_excluded"] += 1
            dropped.append({**{k: j.get(k) for k in ("company", "title", "location", "url")}, "lane": lane, "reason": "already_applied_or_excluded"})
            continue
        if url and url.rstrip("/").lower() in applied_urls:
            reasons["already_applied_url"] += 1
            dropped.append({**{k: j.get(k) for k in ("company", "title", "location", "url")}, "lane": lane, "reason": "already_applied_url"})
            continue
        if lane == "skip":
            reasons["hard_skip"] += 1
            dropped.append({**{k: j.get(k) for k in ("company", "title", "location", "url")}, "lane": lane, "reason": "hard_skip"})
            continue

        score = composite_score(j, lane, daytime)
        row = dict(j)
        row["lane"] = lane
        row["fit_gate_score"] = score
        scored.append(row)

    min_fit = MIN_FIT_DEFAULT
    kept = [j for j in scored if j["fit_gate_score"] >= min_fit]
    below = [j for j in scored if j["fit_gate_score"] < min_fit]

    if len(kept) < VERY_THIN_KEEP:
        min_fit = VERY_THIN_MIN_FIT
        kept = [j for j in scored if j["fit_gate_score"] >= min_fit]
        below = [j for j in scored if j["fit_gate_score"] < min_fit]
    elif len(kept) < THIN_KEEP:
        min_fit = THIN_MIN_FIT
        kept = [j for j in scored if j["fit_gate_score"] >= min_fit]
        below = [j for j in scored if j["fit_gate_score"] < min_fit]

    for j in below:
        reasons["below_min_fit"] += 1
        dropped.append({
            "company": j.get("company"),
            "title": j.get("title"),
            "location": j.get("location"),
            "fit_gate_score": j.get("fit_gate_score"),
            "lane": j.get("lane"),
            "reason": "below_min_fit",
        })

    kept.sort(key=lambda j: sort_key(j, daytime))

    lane_counts = Counter(j.get("lane") for j in kept)
    out = {
        "updated": ts.isoformat(timespec="seconds"),
        "jobs": kept,
        "lane_counts": {
            "uae": int(lane_counts.get("uae", 0)),
            "remote": int(lane_counts.get("remote", 0)),
            "skip": 0,
        },
        "fit_gate": {
            "min_fit": min_fit,
            "period": period,
            "scored": len(jobs_in),
            "kept": len(kept),
            "dropped": len(dropped),
        },
    }
    apply_path.write_text(json.dumps(out, indent=2) + "\n")

    top_kept = [
        {
            "company": j.get("company"),
            "title": j.get("title"),
            "score": j.get("fit_gate_score"),
            "lane": j.get("lane"),
            "guest_ats": bool(j.get("guest_ats")),
        }
        for j in kept[:8]
    ]

    fit_gate_doc = {
        "updated": ts.isoformat(timespec="seconds"),
        "min_fit": min_fit,
        "weights": WEIGHTS,
        "lane_rule": "UAE queue if UAE/Dubai/Abu Dhabi mention (incl UAE+remote/hybrid); else remote queue; drop hard skip only",
        "last_run": {
            "ts": ts.isoformat(timespec="seconds"),
            "scored": len(jobs_in),
            "kept": len(kept),
            "dropped": len(dropped),
            "drop_rate": round(len(dropped) / max(1, len(jobs_in)), 4),
            "min_fit": min_fit,
            "period": period,
            "drop_reasons": dict(reasons),
            "lane_counts": out["lane_counts"],
            "top_kept": top_kept,
            "queue_empty": len(kept) == 0,
        },
        "geo_policy": {
            "uae_queue": ["uae_onsite", "uae_hybrid", "uae_plus_remote"],
            "remote_queue": [
                "fully_remote", "wfa", "anywhere", "soft_emea_remote",
                "usa_hybrid", "eu_hybrid", "other_non_uae_hybrid",
            ],
            "drop": ["hard_citizen_only", "payroll_only", "onsite_only_no_remote_no_uae"],
            "rule": "If posting mentions UAE/Dubai/Abu Dhabi → UAE queue even when also remote/hybrid.",
            "updated": "2026-09-24",
        },
        "notes": "UAE+remote and UAE+hybrid → UAE queue; USA/EU hybrid → remote queue. Never apply.",
    }
    (STATUS / "FIT_GATE.json").write_text(json.dumps(fit_gate_doc, indent=2) + "\n")
    (STATUS / "FIT_GATE_DROPPED_LAST.json").write_text(
        json.dumps(
            {
                "updated": ts.isoformat(timespec="seconds"),
                "count": len(dropped),
                "reasons": dict(reasons),
                "jobs": dropped[:200],
            },
            indent=2,
        )
        + "\n"
    )

    # MESH_STATUS handshake
    mesh_path = STATUS / "MESH_STATUS.json"
    mesh = json.loads(mesh_path.read_text()) if mesh_path.exists() else {"suite": "Hire Mesh", "workers": {}}
    workers = mesh.setdefault("workers", {})
    fg = workers.setdefault(
        "fit_gate",
        {
            "routine": "fit-gate-hire-mesh",
            "schedule": "18 */2 * * * Asia/Dubai",
            "phase": 2,
            "notes": "Phase2 re-rank APPLY_READY; no apply",
        },
    )
    fg["last"] = {
        "worker": "fit_gate",
        "ts": ts.isoformat(timespec="seconds"),
        "ok": True,
        "notes": (
            f"scored={len(jobs_in)}; kept={len(kept)}; dropped={len(dropped)}; "
            f"drop_rate={round(100*len(dropped)/max(1,len(jobs_in)))}%; "
            f"period={period}; min_fit={min_fit}; "
            f"uae={out['lane_counts']['uae']}; remote={out['lane_counts']['remote']}; "
            f"reasons={dict(reasons)}; no_applications"
        ),
    }
    mesh["updated"] = ts.isoformat(timespec="seconds")
    mesh_path.write_text(json.dumps(mesh, indent=2) + "\n")

    summary = {
        "ok": True,
        "period": period,
        "min_fit": min_fit,
        "scored": len(jobs_in),
        "kept": len(kept),
        "dropped": len(dropped),
        "lane_counts": out["lane_counts"],
        "reasons": dict(reasons),
        "queue_empty": len(kept) == 0,
        "top_kept": top_kept[:5],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
