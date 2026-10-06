#!/usr/bin/env python3
"""Hire Mesh · Job Scout — discover + rank ONLY (never apply).

Writes:
  queues/SCOUT_QUEUE.json
  queues/APPLY_READY.json
  status/MESH_STATUS.json  (workers.job_scout.last)
  status/SCOUT_ZERO_STREAK.json

Asia/Dubai daytime: UAE-priority ranking; soft-geo EMEA remote kept as fully-remote content.
No salary floor. Attribute remotive; do not republish.
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
from urllib.parse import urlparse, urlunparse

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
QUEUES = ROOT / "queues"
STATUS = ROOT / "status"
INBOX = ROOT / "inbox"
STATUS = ROOT / "status"
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))
from lane_router import classify_lane  # noqa: E402
from free_discovery_apis import (  # noqa: E402
    remotive,
    himalayas_search,
    remoteok,
    arbeitnow,
    jobicy,
    themuse,
    weworkremotely_rss,
    hn_whos_hiring,
    ats_boards_batch,
    linkedin_guest_both_streams,
)
from SALARY_POLICY import NO_SALARY_FLOOR  # noqa: E402

DUBAI = timezone(timedelta(hours=4))

HARD_SKIP = {
    "emirates", "emirates group", "emirates airline", "dnata",
    "fab", "first abu dhabi bank", "national bank of abu dhabi",
    "americana", "americana foods", "americana restaurants",
    "oracle", "oracle corporation",
}

FAMILY_QUERIES = [
    "platform engineer",
    "cloud architect",
    "devops",
    "sre",
    "kubernetes",
    "mlops",
    "llmops",
    "aiops",
    "ai infrastructure",
    "engineering manager",
    "head of platform",
    "staff platform",
    "principal cloud",
    "observability",
    "platform engineering",
    "cloud platform",
    "site reliability",
    "devops engineer",
    "ai platform",
]

UAE_LIGHT_QUERIES = ["dubai", "uae", "middle east"]

REMOTEOK_TAGS = [
    "devops", "sre", "kubernetes", "cloud", "platform",
    "sysadmin", "engineer", "ai", "ml",
]

GUEST_ATS_HOSTS = (
    "greenhouse.io", "boards.greenhouse.io", "job-boards.greenhouse.io",
    "ashbyhq.com", "jobs.ashbyhq.com",
    "lever.co", "jobs.lever.co",
    "workable.com", "apply.workable.com",
    "ats.rippling.com", "rippling.com",
    "teamtailor.com",
    "personio.de", "personio.com",
    "smartrecruiters.com", "jobs.smartrecruiters.com",
    "bamboohr.com",
    "recruitee.com",
    "join.com",
    "pinpoint.tech", "pinpointhq.com",
    "comeet.com", "comeet.co",
)

FIT_BOOST = [
    (r"\b(engineering manager|head of|director|avp|vp |vice president|staff|principal|architect|lead)\b", 18),
    (r"\b(platform|sre|devops|aiops|mlops|llmops|kubernetes|k8s|observability|cloud|infra|infrastructure)\b", 22),
    (r"\b(ai infrastructure|ai platform|llm|machine learning ops|site reliability)\b", 16),
    (r"\b(senior|sr\.|manager)\b", 8),
]
FIT_DEMOTE = [
    (r"\b(sales|account executive|sdr|bdr|customer success|recruiter|talent|marketing|intern|internship|junior|graduate|entry.?level|clerk|cashier)\b", -45),
    (r"\b(frontend only|react native|ios developer|android developer|php developer|wordpress)\b", -20),
]

# Soft-geo keep: worldwide / WFA / EMEA / MENA / UAE / bare Remote
# Drop hard US-only / India-only / locked local work-auth
HARD_GEO_DROP = [
    r"\bus only\b", r"\busa only\b", r"\bunited states only\b",
    r"\bmust be (located |based )?(in )?(the )?(us|usa|united states|uk|united kingdom|eu|european union)\b",
    r"\b(us|usa|uk|eu) citizen(ship)? required\b",
    r"\brequires? (us|usa|uk|eu) work(ing)? (auth|authorization|permit|visa)\b",
    r"\bindia only\b", r"\bbased in india\b", r"\bmust be in india\b",
    r"\bon[- ]site only\b", r"\bno remote\b",
]


def now_dubai_iso() -> str:
    return datetime.now(DUBAI).strftime("%Y-%m-%dT%H:%M:%S+04:00")


def norm_company(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s&/+.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    for suffix in (" inc", " inc.", " llc", " ltd", " ltd.", " gmbh", " ag", " plc", " pjsc", " co", " corp", " corporation"):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s


def norm_url(u: str) -> str:
    if not u:
        return ""
    try:
        p = urlparse(u.strip())
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (p.path or "").rstrip("/").lower()
        return urlunparse(("https", host, path, "", "", ""))
    except Exception:
        return u.strip().lower().rstrip("/")


def load_skip_sets() -> tuple[set[str], set[str]]:
    companies: set[str] = set()
    urls: set[str] = set()
    for line in (ROOT / "APPLIED_COMPANIES.txt").read_text(errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            companies.add(norm_company(line))
    for line in (ROOT / "APPLIED_URLS.txt").read_text(errors="ignore").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.add(norm_url(line))
    for h in HARD_SKIP:
        companies.add(norm_company(h))
    return companies, urls


def is_guest_ats(url: str) -> bool:
    if not url:
        return False
    host = (urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    for h in GUEST_ATS_HOSTS:
        if host == h or host.endswith("." + h) or h in host:
            return True
    return False


def soft_geo_ok(location: str, title: str = "") -> bool:
    """Keep UAE queue + remote queue; drop only hard skip."""
    return classify_lane(location, title) != "skip"



def fit_score(title: str, location: str = "", tags: Any = None) -> int:
    t = (title or "").lower()
    blob = t
    if tags:
        if isinstance(tags, list):
            blob += " " + " ".join(str(x).lower() for x in tags)
        else:
            blob += " " + str(tags).lower()
    score = 20
    family_hit = False
    for pat, boost in FIT_BOOST:
        if re.search(pat, blob):
            score += boost
            family_hit = True
    for pat, demote in FIT_DEMOTE:
        if re.search(pat, blob):
            score += demote
    # Daytime UAE soft boost (not exclusive — free APIs are mostly remote)
    loc = (location or "").lower()
    if any(x in loc for x in ("uae", "dubai", "abu dhabi", "united arab", "sharjah", "ajman")):
        score += 14  # UAE queue incl. UAE+remote / UAE hybrid
    elif any(x in loc for x in ("remote", "worldwide", "anywhere", "wfa", "emea", "europe", "uk", "germany", "netherlands", "hybrid", "united states", "usa", "eu ")):
        score += 4  # remote lane incl. US/EU hybrid
    score = max(0, min(100, score))
    return score


def family_match(title: str, tags: Any = None) -> bool:
    blob = (title or "").lower()
    if tags:
        if isinstance(tags, list):
            blob += " " + " ".join(str(x).lower() for x in tags)
    keys = (
        "platform", "cloud", "devops", "sre", "aiops", "mlops", "llmops",
        "kubernetes", "k8s", "observability", "infrastructure", "infra",
        "engineering manager", "head of platform", "staff engineer",
        "principal", "architect", "site reliability", "ai infrastructure",
        "ai platform", "llm",
    )
    return any(k in blob for k in keys)



def discover(errors: list[str]) -> list[dict]:
    """Pull from free boards for both UAE and remote lanes.

    Daytime ranking still UAE-priority; remote/WFA content stays in remote lane.
    UAE hybrid counts as UAE; USA/EU/other hybrid kept in remote lane.
    """
    raw: list[dict] = []

    # --- Remotive family ---
    for q in FAMILY_QUERIES:
        try:
            raw.extend(remotive(q, limit=50))
        except Exception as e:
            errors.append(f"remotive[{q}]: {e}")
    for q in UAE_LIGHT_QUERIES:
        try:
            raw.extend(remotive(q, limit=30))
        except Exception as e:
            errors.append(f"remotive_uae[{q}]: {e}")

    # --- Himalayas (worldwide + UAE country=AE) ---
    for q in FAMILY_QUERIES + UAE_LIGHT_QUERIES:
        try:
            raw.extend(himalayas_search(q, page=1))
            if q in ("platform engineer", "cloud architect", "devops", "mlops", "engineering manager"):
                raw.extend(himalayas_search(q, page=2))
        except Exception as e:
            errors.append(f"himalayas[{q}]: {e}")
    for q in ("cloud", "platform", "devops", "sre", "architect", "engineering manager", "ai"):
        try:
            raw.extend(himalayas_search(q, page=1, country="AE"))
        except Exception as e:
            errors.append(f"himalayas_ae[{q}]: {e}")

    # --- RemoteOK tags ---
    for tag in REMOTEOK_TAGS:
        try:
            raw.extend(remoteok(tag))
        except Exception as e:
            errors.append(f"remoteok[{tag}]: {e}")

    # --- Arbeitnow remote ---
    try:
        raw.extend(arbeitnow(remote=True, max_pages=3))
    except Exception as e:
        errors.append(f"arbeitnow: {e}")

    # --- Jobicy (best-effort; often 403) ---
    for tag in ("devops", "sre", "cloud", "python", "software"):
        try:
            raw.extend(jobicy(tag=tag, count=50))
        except Exception as e:
            errors.append(f"jobicy[{tag}]: {e}")

    # --- The Muse ---
    for page in range(0, 3):
        try:
            raw.extend(themuse(category="Software Engineering", page=page))
        except Exception as e:
            errors.append(f"themuse[{page}]: {e}")
    try:
        raw.extend(themuse(category="Software Engineering", page=0, location="Flexible / Remote"))
    except Exception as e:
        errors.append(f"themuse_remote: {e}")

    # --- We Work Remotely RSS ---
    try:
        raw.extend(weworkremotely_rss())
    except Exception as e:
        errors.append(f"wwr: {e}")

    # --- HN Who's Hiring ---
    try:
        raw.extend(hn_whos_hiring())
    except Exception as e:
        errors.append(f"hn: {e}")


    # --- LinkedIn: prefer signed-in browser session (Meet 2026-09-24). ---
    # Guest scrape is FALLBACK only (LI_GUEST=1). Default path = computerUse on
    # linkedin.com/jobs with Meet's logged-in session; skip Easy Apply; open external ATS.
    import os as _os
    if _os.environ.get("LI_GUEST", "").strip() in ("1", "true", "yes"):
        try:
            raw.extend(linkedin_guest_both_streams(uae=True, remote=True))
        except Exception as e:
            errors.append(f"linkedin_guest_fallback: {e}")

    # --- Curated Greenhouse / Lever / Ashby boards ---
    try:
        raw.extend(ats_boards_batch(max_workers=20))
    except Exception as e:
        errors.append(f"ats_batch: {e}")

    return raw



def dedupe_and_filter(raw: list[dict], skip_co: set[str], skip_url: set[str]) -> tuple[list[dict], int]:
    seen_url: set[str] = set()
    seen_co_title: set[str] = set()
    excluded = 0
    out: list[dict] = []
    for j in raw:
        company = (j.get("company") or "unknown").strip()
        title = (j.get("title") or "").strip()
        url = j.get("url") or j.get("apply_url") or ""
        apply_url = j.get("apply_url") or url
        location = j.get("location") or "Remote"
        source = j.get("source") or "unknown"
        if not title or not url:
            excluded += 1
            continue
        nc = norm_company(company)
        nu = norm_url(url)
        nu2 = norm_url(apply_url)
        if nc in skip_co or nc in HARD_SKIP:
            excluded += 1
            continue
        # partial hard-skip contains
        if any(h in nc for h in ("emirates", "dnata", "americana")) or nc == "oracle" or nc.startswith("oracle "):
            excluded += 1
            continue
        if nu in skip_url or nu2 in skip_url:
            excluded += 1
            continue
        if nu in seen_url or (nu2 and nu2 in seen_url):
            excluded += 1
            continue
        ct = f"{nc}::{title.lower()}"
        if ct in seen_co_title:
            excluded += 1
            continue
        if not soft_geo_ok(location, title):
            excluded += 1
            continue
        tags = j.get("tags")
        fit = fit_score(title, location, tags)
        if fit < 25 and not family_match(title, tags):
            excluded += 1
            continue
        seen_url.add(nu)
        if nu2:
            seen_url.add(nu2)
        seen_co_title.add(ct)
        lane = classify_lane(location, title)
        row = {
            "company": company,
            "title": title,
            "url": url,
            "apply_url": apply_url,
            "source": source,
            "location": location,
            "fit": fit,
            "lane": lane,
        }
        out.append(row)
    out.sort(key=lambda x: (-x["fit"], x["company"].lower()))
    return out, excluded


def build_apply_ready(queue: list[dict], cap: int = 120) -> list[dict]:
    ready = []
    for j in queue:
        if j["fit"] < 45 and not family_match(j["title"]):
            continue
        if j["fit"] < 40:
            continue
        row = dict(j)
        row["guest_ats"] = is_guest_ats(row.get("apply_url") or row.get("url") or "")
        ready.append(row)
        if len(ready) >= cap:
            break
    # If thin, loosen to fit>=35 family
    if len(ready) < 40:
        for j in queue:
            if len(ready) >= max(cap, 80):
                break
            if j["fit"] < 35:
                continue
            key = norm_url(j.get("url") or "")
            if any(norm_url(r.get("url") or "") == key for r in ready):
                continue
            row = dict(j)
            row["guest_ats"] = is_guest_ats(row.get("apply_url") or row.get("url") or "")
            ready.append(row)
    return ready[:150]


def update_zero_streak(apply_ready_n: int) -> int:
    path = STATUS / "SCOUT_ZERO_STREAK.json"
    streak = 0
    if path.exists():
        try:
            streak = int(json.loads(path.read_text()).get("streak", 0))
        except Exception:
            streak = 0
    if apply_ready_n == 0:
        streak += 1
    else:
        streak = 0
    path.write_text(json.dumps({
        "streak": streak,
        "updated": now_dubai_iso(),
        "last_apply_ready": apply_ready_n,
    }, indent=2) + "\n")
    return streak


def update_mesh_status(notes: str) -> None:
    path = STATUS / "MESH_STATUS.json"
    data = json.loads(path.read_text()) if path.exists() else {"suite": "Hire Mesh", "workers": {}}
    workers = data.setdefault("workers", {})
    js = workers.setdefault("job_scout", {
        "routine": "job-scout-hire-mesh",
        "schedule": "11 */2 * * * Asia/Dubai",
    })
    js["last"] = {
        "worker": "job_scout",
        "ts": now_dubai_iso(),
        "ok": True,
        "notes": notes,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def main() -> int:
    assert NO_SALARY_FLOOR is True, "salary floor must stay off"
    errors: list[str] = []
    skip_co, skip_url = load_skip_sets()
    raw = discover(errors)
    discovered = len(raw)
    queue, excluded = dedupe_and_filter(raw, skip_co, skip_url)
    ready = build_apply_ready(queue)
    ts = now_dubai_iso()
    QUEUES.mkdir(parents=True, exist_ok=True)
    STATUS.mkdir(parents=True, exist_ok=True)
    (QUEUES / "SCOUT_QUEUE.json").write_text(json.dumps({
        "updated": ts,
        "jobs": [{k: j[k] for k in ("company", "title", "url", "apply_url", "source", "location", "fit", "lane")} for j in queue],
    }, indent=2, ensure_ascii=False) + "\n")
    (QUEUES / "APPLY_READY.json").write_text(json.dumps({
        "updated": ts,
        "jobs": ready,
    }, indent=2, ensure_ascii=False) + "\n")
    streak = update_zero_streak(len(ready))
    src_counts = Counter(j["source"] for j in queue)
    sources = ",".join(sorted(src_counts.keys())) or "none"
    guest_n = sum(1 for j in ready if j.get("guest_ats"))
    lane_uae = sum(1 for j in ready if j.get("lane") == "uae")
    lane_remote = sum(1 for j in ready if j.get("lane") == "remote")
    notes = (
        f"discovered={discovered}; queue={len(queue)}; apply_ready={len(ready)}; "
        f"excluded_or_deduped={excluded}; sources={sources}; "
        f"lane=day_uae_priority; apply_ready_uae={lane_uae}; apply_ready_remote={lane_remote}; "
        f"no_salary_floor; no_applications"
    )
    if streak >= 2:
        notes += f"; zero_usable_streak={streak}"
    update_mesh_status(notes)

    # Report for parent
    top5 = ready[:5] if ready else queue[:5]
    print("=== JOB_SCOUT_REPORT ===")
    print(f"ts={ts}")
    print(f"discovered={discovered}")
    print(f"queue={len(queue)}")
    print(f"apply_ready={len(ready)}")
    print(f"excluded_or_deduped={excluded}")
    print(f"guest_ats_in_apply_ready={guest_n}")
    print(f"zero_streak={streak}")
    print(f"sources={dict(src_counts)}")
    print(f"api_errors={errors[:20]}")
    print("top5:")
    for j in top5:
        print(f"  [{j.get('fit')}] {j.get('company')} — {j.get('title')} ({j.get('source')}, {j.get('location')})")
    print(f"notes={notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
