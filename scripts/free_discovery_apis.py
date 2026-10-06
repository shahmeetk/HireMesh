"""Free remote/UAE job discovery APIs for {{CANDIDATE_NAME}} Hire Mesh (2026-09-24).

No salary floor. Callers still apply company/URL dedupe + soft-geo + fit.
Respect Remotive ToS: attribute source=remotive; do not republish to other boards.
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable
import html as _html
import time as _time

UA = {
    "User-Agent": "HireMeshBot/1.0 (personal job search; +mailto:candidate@example.com)",
    "Accept": "application/json, text/xml, */*",
}
BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "application/json, text/xml, */*",
}

TITLE_KEEP = re.compile(
    r"(platform|cloud|devops|sre|site.?reliability|kubernetes|k8s|mlops|llmops|aiops|"
    r"observability|infrastructure|architect|staff|principal|head of|director|"
    r"engineering manager|ai (platform|infra)|finops|devsecops|production engineer)",
    re.I,
)
TITLE_DROP = re.compile(
    r"\b(sales|account executive|\bae\b|sdr|bdr|intern|junior|customer success|"
    r"recruiter|marketing|designer|new grad|people partner|\bhr\b)\b",
    re.I,
)


def _get(url: str, timeout: int = 20, headers: dict | None = None) -> Any:
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        ctype = (r.headers.get("Content-Type") or "").lower()
        if "json" in ctype or (raw[:1] in (b"{", b"[") and b"<" not in raw[:20]):
            return json.loads(raw.decode())
        return raw


def _get_json(url: str, timeout: int = 20, headers: dict | None = None) -> Any:
    data = _get(url, timeout=timeout, headers=headers)
    if isinstance(data, (bytes, bytearray)):
        return json.loads(data.decode())
    return data


def remotive(search: str, limit: int = 50) -> list[dict]:
    q = urllib.parse.urlencode({"search": search, "limit": limit})
    data = _get_json(f"https://remotive.com/api/remote-jobs?{q}")
    jobs = data.get("jobs") if isinstance(data, dict) else data
    out = []
    for j in jobs or []:
        out.append({
            "company": j.get("company_name") or "unknown",
            "title": j.get("title") or "",
            "url": j.get("url") or "",
            "apply_url": j.get("url") or "",
            "source": "remotive",
            "location": j.get("candidate_required_location") or "Remote",
            "salary": j.get("salary") or "",
        })
    return out


def jobicy(tag: str = "devops", geo: str = "anywhere", count: int = 50) -> list[dict]:
    q = urllib.parse.urlencode({"count": count, "tag": tag, "geo": geo})
    try:
        data = _get_json(f"https://jobicy.com/api/v2/remote-jobs?{q}", headers=BROWSER_UA)
    except Exception:
        return []
    jobs = (data.get("jobs") if isinstance(data, dict) else None) or []
    out = []
    for j in jobs:
        out.append({
            "company": j.get("companyName") or j.get("company") or "unknown",
            "title": j.get("jobTitle") or j.get("title") or "",
            "url": j.get("url") or j.get("jobUrl") or "",
            "apply_url": j.get("url") or j.get("jobUrl") or "",
            "source": "jobicy",
            "location": j.get("jobGeo") or geo,
            "salary": j.get("annualSalaryMin") or j.get("salary") or "",
        })
    return out


def himalayas_search(q: str, page: int = 1, country: str | None = None, worldwide: bool | None = None) -> list[dict]:
    params: dict[str, Any] = {"q": q, "page": page, "sort": "recent"}
    if country:
        params["country"] = country
    if worldwide is True:
        params["worldwide"] = "true"
    qs = urllib.parse.urlencode(params)
    data = _get_json(f"https://himalayas.app/jobs/api/search?{qs}")
    jobs = data if isinstance(data, list) else (data.get("jobs") or data.get("data") or [])
    out = []
    for j in jobs or []:
        if not isinstance(j, dict):
            continue
        url = j.get("applicationLink") or j.get("url") or ""
        company = j.get("companyName")
        if not company:
            c = j.get("company")
            company = c.get("name") if isinstance(c, dict) else c
        loc = j.get("location") or "Remote"
        src = "himalayas_ae" if country and str(country).upper() == "AE" else "himalayas"
        out.append({
            "company": company or "unknown",
            "title": j.get("title") or "",
            "url": url,
            "apply_url": url,
            "source": src,
            "location": loc,
            "salary": j.get("maxSalary") or j.get("salary") or "",
        })
    return out


# Back-compat alias used by older scout
def himalayas_search_legacy(q: str, page: int = 1) -> list[dict]:
    return himalayas_search(q, page=page)


def remoteok(tag: str = "devops") -> list[dict]:
    data = _get_json(f"https://remoteok.com/api?tag={urllib.parse.quote(tag)}")
    out = []
    for j in data or []:
        if not isinstance(j, dict) or not j.get("id") or j.get("id") == "metadata":
            continue
        out.append({
            "company": j.get("company") or "unknown",
            "title": j.get("position") or j.get("title") or "",
            "url": j.get("url") or j.get("apply_url") or "",
            "apply_url": j.get("apply_url") or j.get("url") or "",
            "source": "remoteok",
            "location": j.get("location") or "Remote",
            "salary": j.get("salary_max") or j.get("salary") or "",
        })
    return out


def arbeitnow(remote: bool = True, max_pages: int = 3) -> list[dict]:
    out: list[dict] = []
    for page in range(1, max_pages + 1):
        q = urllib.parse.urlencode({"remote": "true" if remote else "false", "page": page})
        try:
            data = _get_json(f"https://www.arbeitnow.com/api/job-board-api?{q}")
        except Exception:
            break
        jobs = (data.get("data") if isinstance(data, dict) else None) or []
        if not jobs:
            break
        for j in jobs:
            if not isinstance(j, dict):
                continue
            url = j.get("url") or ""
            loc = j.get("location") or ("Remote" if j.get("remote") else "")
            if j.get("remote") and loc and "remote" not in loc.lower():
                loc = f"Remote / {loc}"
            elif j.get("remote") and not loc:
                loc = "Remote"
            out.append({
                "company": j.get("company_name") or "unknown",
                "title": j.get("title") or "",
                "url": url,
                "apply_url": url,
                "source": "arbeitnow",
                "location": loc or "Remote",
                "salary": "",
                "tags": j.get("tags") or [],
                "remote": bool(j.get("remote")),
            })
        links = (data.get("links") if isinstance(data, dict) else None) or {}
        if not links.get("next"):
            break
    return out


def themuse(category: str = "Software Engineering", page: int = 0, location: str | None = None) -> list[dict]:
    params: dict[str, Any] = {"category": category, "page": page}
    if location:
        params["location"] = location
    qs = urllib.parse.urlencode(params)
    data = _get_json(f"https://www.themuse.com/api/public/jobs?{qs}")
    results = (data.get("results") if isinstance(data, dict) else None) or []
    out = []
    for j in results:
        locs = j.get("locations") or []
        loc_names = ", ".join(x.get("name") for x in locs if isinstance(x, dict) and x.get("name")) or "Remote"
        comps = j.get("company") or {}
        company = comps.get("name") if isinstance(comps, dict) else "unknown"
        refs = j.get("refs") or {}
        url = refs.get("landing_page") if isinstance(refs, dict) else ""
        out.append({
            "company": company or "unknown",
            "title": j.get("name") or "",
            "url": url or "",
            "apply_url": url or "",
            "source": "themuse",
            "location": loc_names,
            "salary": "",
        })
    return out


def weworkremotely_rss() -> list[dict]:
    raw = _get("https://weworkremotely.com/categories/remote-programming-jobs.rss", headers=BROWSER_UA)
    if isinstance(raw, (dict, list)):
        return []
    root = ET.fromstring(raw)
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        company, role = "unknown", title
        if ":" in title:
            company, role = [x.strip() for x in title.split(":", 1)]
        out.append({
            "company": company,
            "title": role,
            "url": link,
            "apply_url": link,
            "source": "weworkremotely",
            "location": "Remote",
            "salary": "",
        })
    return out


def hn_whos_hiring(keywords: Iterable[str] | None = None) -> list[dict]:
    keywords = list(keywords or [
        "platform", "devops", "sre", "kubernetes", "cloud", "mlops", "llmops",
        "infrastructure", "remote", "worldwide", "emea",
    ])
    search = _get_json(
        "https://hn.algolia.com/api/v1/search?query="
        + urllib.parse.quote("Who's Hiring")
        + "&tags=story&hitsPerPage=5"
    )
    story_id = None
    for h in search.get("hits") or []:
        title = (h.get("title") or "")
        if "who's hiring" in title.lower() and h.get("objectID"):
            story_id = h["objectID"]
            break
    if not story_id:
        return []
    comments = _get_json(
        f"https://hn.algolia.com/api/v1/search?tags=comment,story_{story_id}&hitsPerPage=100"
    )
    out = []
    for c in comments.get("hits") or []:
        text = c.get("comment_text") or ""
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain).strip()
        if not plain:
            continue
        low = plain.lower()
        if not any(k.lower() in low for k in keywords):
            continue
        head = plain.split("|")[0].split("-")[0].strip()[:80]
        company = head.split(" ")[0] if head else "HN"
        url = f"https://news.ycombinator.com/item?id={c.get('objectID')}"
        m = re.search(r"https?://[^\s<]+", text)
        if m:
            url = re.sub(r"[)\],.]+$", "", m.group(0))
        title_guess = " / ".join(k for k in keywords if k.lower() in low)[:80] or "Engineering"
        out.append({
            "company": company,
            "title": f"HN Hiring · {title_guess}",
            "url": url,
            "apply_url": url,
            "source": "hn_whos_hiring",
            "location": "Remote" if ("remote" in low or "worldwide" in low) else "See post",
            "salary": "",
            "tags": ["hn"],
        })
    return out[:80]


def greenhouse_jobs(board: str) -> list[dict]:
    out: list[dict] = []
    for base in (
        f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs",
        f"https://boards-api.eu.greenhouse.io/v1/boards/{board}/jobs",
    ):
        try:
            data = _get_json(base, timeout=15)
        except Exception:
            continue
        for j in data.get("jobs") or []:
            loc = ""
            locs = j.get("location")
            if isinstance(locs, dict):
                loc = locs.get("name") or ""
            out.append({
                "company": board,
                "title": j.get("title") or "",
                "url": j.get("absolute_url") or "",
                "apply_url": j.get("absolute_url") or "",
                "source": "greenhouse",
                "location": loc or "See posting",
                "salary": "",
                "tags": ["ats", "greenhouse"],
            })
        if out:
            break
    return out


def lever_jobs(slug: str) -> list[dict]:
    try:
        data = _get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=15)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for j in data:
        cats = j.get("categories") or {}
        loc = cats.get("location") if isinstance(cats, dict) else ""
        out.append({
            "company": slug,
            "title": j.get("text") or "",
            "url": j.get("hostedUrl") or j.get("applyUrl") or "",
            "apply_url": j.get("applyUrl") or j.get("hostedUrl") or "",
            "source": "lever",
            "location": loc or "See posting",
            "salary": "",
            "tags": ["ats", "lever"],
        })
    return out


def ashby_jobs(slug: str) -> list[dict]:
    try:
        data = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=15)
    except Exception:
        return []
    out = []
    for j in data.get("jobs") or []:
        loc = j.get("location") or ""
        if not loc and isinstance(j.get("address"), dict):
            loc = j["address"].get("postalAddress") or ""
        out.append({
            "company": slug,
            "title": j.get("title") or "",
            "url": j.get("jobUrl") or j.get("applyUrl") or "",
            "apply_url": j.get("applyUrl") or j.get("jobUrl") or "",
            "source": "ashby",
            "location": loc or "See posting",
            "salary": "",
            "tags": ["ats", "ashby"],
        })
    return out


def _title_ok(title: str) -> bool:
    if not title:
        return False
    if TITLE_DROP.search(title) and not TITLE_KEEP.search(title):
        return False
    return bool(TITLE_KEEP.search(title))


def _soft_geo_keep(location: str) -> bool:
    """Keep UAE (incl UAE+remote/hybrid) and remote lane; drop hard auth locks only."""
    try:
        from lane_router import classify_lane
        return classify_lane(location or "") != "skip"
    except Exception:
        loc = (location or "").lower()
        if not loc:
            return True
        if any(x in loc for x in ("uae", "dubai", "abu dhabi", "sharjah")):
            return True
        if "citizen" in loc and "only" in loc:
            return False
        return True


def load_ats_slugs(path: str | Path | None = None) -> dict:
    path = Path(path or Path(__file__).with_name("ats_board_slugs.json"))
    if not path.exists():
        return {"ashby": [], "lever": [], "greenhouse": []}
    return json.loads(path.read_text())


def ats_boards_batch(
    ashby_slugs: list[str] | None = None,
    lever_slugs: list[str] | None = None,
    gh_boards: list[str] | None = None,
    max_workers: int = 24,
) -> list[dict]:
    slugs = load_ats_slugs()
    ashby_slugs = ashby_slugs if ashby_slugs is not None else slugs.get("ashby") or []
    lever_slugs = lever_slugs if lever_slugs is not None else slugs.get("lever") or []
    gh_boards = gh_boards if gh_boards is not None else slugs.get("greenhouse") or []
    tasks = []
    for s in ashby_slugs:
        tasks.append(("ashby", s, ashby_jobs))
    for s in lever_slugs:
        tasks.append(("lever", s, lever_jobs))
    for s in gh_boards:
        tasks.append(("greenhouse", s, greenhouse_jobs))
    out: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fn, slug): (kind, slug) for kind, slug, fn in tasks}
        for fut in as_completed(futs):
            try:
                hits = fut.result() or []
            except Exception:
                continue
            for j in hits:
                title = j.get("title") or ""
                if not _title_ok(title):
                    continue
                if not _soft_geo_keep(j.get("location") or ""):
                    continue
                out.append(j)
    return out


# Aliases matching older scout imports
himalayas_search_compat = himalayas_search


if __name__ == "__main__":
    for name, fn in [
        ("remotive", lambda: remotive("platform")),
        ("jobicy", lambda: jobicy("kubernetes")),
        ("himalayas", lambda: himalayas_search("platform engineer")),
        ("himalayas_ae", lambda: himalayas_search("cloud", country="AE")),
        ("remoteok", lambda: remoteok("devops")),
        ("arbeitnow", lambda: arbeitnow(max_pages=1)),
        ("themuse", lambda: themuse(page=0)),
        ("wwr", lambda: weworkremotely_rss()[:3]),
        ("hn", lambda: hn_whos_hiring()[:3]),
        ("gh", lambda: greenhouse_jobs("datadog")[:2]),
        ("ashby", lambda: ashby_jobs("openai")[:2]),
    ]:
        try:
            hits = fn()
            print(name, len(hits), (hits[0].get("title") if hits else None))
        except Exception as e:
            print(name, "ERR", e)




LI_FAMILY_QUERIES = [
    "Cloud Architect OR Solutions Architect OR Platform Engineer",
    "Engineering Manager OR Head of Platform OR Staff Platform",
    "SRE OR DevOps OR DevSecOps OR Site Reliability",
    "MLOps OR LLMOps OR AI Platform OR AI Infrastructure",
    "Principal Architect OR Staff Engineer Platform OR FinOps",
]


def linkedin_guest_jobs(
    keywords: str,
    location: str = "United Arab Emirates",
    *,
    remote: bool = False,
    starts: Iterable[int] | None = None,
    skip_easy_apply: bool = True,
    pause_s: float = 0.8,
) -> list[dict]:
    """LinkedIn jobs-guest search. Prefer non-Easy-Apply (external ATS) cards.

    Easy Apply-only cards are dropped when skip_easy_apply=True — Apply Engine
    must open the employer ATS, not LinkedIn Easy Apply.
    """
    starts = list(starts) if starts is not None else [0, 25]
    out: list[dict] = []
    for start in starts:
        params = {
            "keywords": keywords,
            "location": location,
            "f_TPR": "r1209600",  # past 2 weeks
            "start": str(start),
        }
        if remote:
            params["f_WT"] = "2"  # remote filter
        q = urllib.parse.urlencode(params)
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{q}"
        try:
            raw = _get(url, timeout=25, headers={
                **BROWSER_UA,
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "en-US,en;q=0.9",
            })
        except Exception:
            break
        if isinstance(raw, (bytes, bytearray)):
            h = raw.decode("utf-8", errors="ignore")
        else:
            h = str(raw)
        # Split into cards; each base-card / base-search-card block
        chunks = re.split(r'(?=<div[^>]+class="[^"]*base-card)', h)
        if len(chunks) < 2:
            # fallback: global regex (may include Easy Apply — filter by nearby text)
            chunks = [h]
        for chunk in chunks:
            low = chunk.lower()
            if skip_easy_apply and "easy apply" in low:
                continue
            links = re.findall(r'href="(https://[a-z.]*linkedin\.com/jobs/view/[^"?]+)', chunk)
            titles = re.findall(r'base-search-card__title[^>]*>([^<]+)', chunk)
            companies = re.findall(r'base-search-card__subtitle[^>]*>\s*<a[^>]*>([^<]+)', chunk)
            locs = re.findall(r'job-search-card__location[^>]*>([^<]+)', chunk)
            if not links:
                continue
            for i, link in enumerate(links):
                title = _html.unescape((titles[i] if i < len(titles) else "").strip())
                company = _html.unescape((companies[i] if i < len(companies) else "").strip())
                loc = _html.unescape((locs[i] if i < len(locs) else location).strip())
                if not title:
                    continue
                if not TITLE_KEEP.search(title) or TITLE_DROP.search(title):
                    continue
                out.append({
                    "company": company or "Unknown",
                    "title": title,
                    "url": link.split("?")[0],
                    "apply_url": link.split("?")[0],
                    "location": loc or ("Remote" if remote else location),
                    "source": "linkedin_guest",
                    "note": "non_easy_apply_preferred; resolve external ATS before apply",
                    "lane_hint": "remote" if remote else "uae",
                })
        _time.sleep(pause_s)
    # dedupe by url
    seen = set()
    uniq = []
    for j in out:
        u = (j.get("url") or "").lower()
        if u in seen:
            continue
        seen.add(u)
        uniq.append(j)
    return uniq


def linkedin_guest_both_streams(
    queries: Iterable[str] | None = None,
    *,
    uae: bool = True,
    remote: bool = True,
) -> list[dict]:
    """Pull LinkedIn non-Easy-Apply for UAE and/or remote streams."""
    queries = list(queries) if queries is not None else LI_FAMILY_QUERIES
    out: list[dict] = []
    if uae:
        for q in queries:
            try:
                out.extend(linkedin_guest_jobs(q, "United Arab Emirates", remote=False))
            except Exception:
                pass
            try:
                out.extend(linkedin_guest_jobs(q, "Dubai, United Arab Emirates", remote=False, starts=[0]))
            except Exception:
                pass
    if remote:
        for q in queries:
            # append remote keyword for worldwide remote non-EA
            rq = f"({q}) remote"
            try:
                out.extend(linkedin_guest_jobs(rq, "Worldwide", remote=True, starts=[0, 25]))
            except Exception:
                pass
            try:
                out.extend(linkedin_guest_jobs(q, "EMEA", remote=True, starts=[0]))
            except Exception:
                pass
    return out



# Scout-facing aliases for Discovery Scout imports
jobicy = jobicy
themuse = themuse
weworkremotely_rss = weworkremotely_rss
hn_whos_hiring = hn_whos_hiring
ats_boards_batch = ats_boards_batch
linkedin_guest_jobs = linkedin_guest_jobs
linkedin_guest_both_streams = linkedin_guest_both_streams
LI_FAMILY_QUERIES = LI_FAMILY_QUERIES
