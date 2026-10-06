import os
#!/usr/bin/env python3
"""Build QUEUE_REMOTE_NIGHT_SEP22_WA155 — fit-first + STRICT location-first geo."""
import json, re
from pathlib import Path
from datetime import datetime, timezone

base = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
disc = json.loads((base / "DISCOVERY_API_WA155.json").read_text())

# Merge HOT supplemental (dedupe by URL)
def _url_key(h):
    return (h.get("apply_url") or h.get("url") or "").rstrip("/").lower()

seen_urls = {_url_key(h) for h in (disc.get("discovered") or []) if _url_key(h)}
merged_extra = 0
for fname in ("DISCOVERY_HOT_WA155.json", "DISCOVERY_SUPPLEMENT_WA155.json", "FRESH_GUEST_WFA_WA155.json", "DISCOVERY_EXPAND_WA155.json", "DISCOVERY_EXPAND2_WA155.json", "DISCOVERY_NEWBOARDS_WA155.json", "DISCOVERY_WFA_STRICT_WA155.json", "DISCOVERY_WEBSEARCH_WA155.json"):
    fp = base / fname
    if not fp.exists():
        continue
    raw = json.loads(fp.read_text())
    items = raw if isinstance(raw, list) else (raw.get("discovered") or raw.get("jobs") or raw.get("results") or [])
    if not items and isinstance(raw, dict) and (raw.get("gh") or raw.get("ashby")):
        items = list(raw.get("gh") or []) + list(raw.get("ashby") or [])
    for h in items:
        if not isinstance(h, dict):
            continue
        uk = _url_key(h)
        if not uk or uk in seen_urls:
            continue
        seen_urls.add(uk)
        disc.setdefault("discovered", []).append(h)
        merged_extra += 1
disc.setdefault("counts", {})["unique"] = len(disc.get("discovered") or [])
disc["counts"]["hot_merged_extra"] = merged_extra
print(f"Merged +{merged_extra} from hot → unique {disc['counts']['unique']}")

companies = {
    re.sub(r"\b(llc|ltd|inc|corp|co|limited|plc|gmbh)\b", "", x.strip().lower()).strip(" .,")
    for x in (base / "APPLIED_COMPANIES.txt").read_text().splitlines() if x.strip()
}
urls = {x.strip().rstrip("/") for x in (base / "APPLIED_URLS.txt").read_text().splitlines() if x.strip()}

HARD_SKIP = {

    # WA155 do-not-reloop — Socket WA143, Kong WA146, Cognition WA147, Amazon WA148
    "socket", "kong", "cognition", "cognition labs",
    "livekit", "enec", "sysdig", "amazon",

    # WA155 do-not-reloop / already applied night
    "poolside", "alchemy", "decagon", "moxie", "valon", "harvey",
    "moderntreasury", "modern treasury", "writer", "perplexity", "perplexity ai",
    "omni", "extrahop", "nango", "inngest", "zapier", "lightning ai", "lightning",
    "partly", "cohere", "clickhouse", "canonical", "duckduckgo", "calendly",


    # WA140 / WA155 do-not-reloop
    "kestra", "kestra technologies",
    "scribe", "scribehow",
    "resend",
    "knock",
    "cortex", "cortex.io",
    "n8n",
    "langchain", "lang chain",
    "sanity",
    "doit", "doit international",
    "prefect",
    "constructor", "supabase", "posthog",
    "calendly", "cloudzero", "platform.sh", "platformsh", "upsun",
    "mindtel", "shamal", "tencent", "bayt", "cisco", "gbm", "metabase",
    "netomi", "proxify", "snowflake",

    "databricks", "stripe", "gitlab", "fireblocks", "mozilla", "rippling", "together", "together ai", "hightouch",
    "lightning ai", "lightning", "storyblok", "kraken", "autodesk",

    "fab", "emirates", "emirates group", "dnata", "emirates airline", "the emirates group",
    "planetscale", "saas.group", "saas group", "saasgroup",
    "netomi", "livekit", "temporal", "cloudlinux", "proxify",
    "doit", "doit international", "railway", "oyster", "oyster hr",
    "pencil", "deepgram", "amazon", "capgemini", "capgemini invent",
    "weaviate", "roboflow",
    "black pearl", "black pearl consult",
    "chess.com", "contango", "sedona digital", "al tayer", "al tayer insignia",
    "aldar", "safran", "multibank", "rakbank",
    "phantom", "drata", "mesh", "vrchat",

    "posthog", "auxo talent", "auxo", "zaintech", "azizi", "azizi developments",
    "bespin", "bespin global", "bespin global mea", "suadeo",
    "techfindr", "oracle", "revolut",

    "first point group", "landmark group", "landmark", "inception42", "g42",
    "scale ai", "scale",
    "teamware", "teamware solutions", "dxc", "dxc technology",

    # WA99 same-day
    "marc ellis", "focus infotech", "mindpool", "mindpool technologies",
    "accellor",  # CAPTCHA pending but company touched
    "hays", "mashreq", "kpmg", "finance house", "eminds", "digital next uae",
    "astera", "first.tech", "orient insurance", "al futtaim group",
    "nst", "quess", "quess corp",
    "prefect", "stackblitz", "vrchat", "revolut", "cercli", "analog", "drata",
"vlm run", "proxybase", "catalyst", "catalyst wayfare", "catalyst wayfare ai", "albert", "lucia", "aimi", "this dot labs", "cyberatlas", "netbird",
    "astoria", "astoria ai", "starbridge", "coinmarketcap", "coin market cap",
    "tether", "accellor", "netbird",
    "tenchi", "tenchi security", "aiwi", "the ai whistleblower initiative", "mingla",
    "jobgether", "this dot labs", "thisdot", "this dot", "cyberatlas", "tether", "extrahop", "securityscorecard", "webflow", "lithic", "bubble",

    # WA112 / WA121 do-not-reloop
    "staff connect", "staffconnect", "staff connect uae", "binance", "mastra", "capital.com", "capital", "ifs", "pristine", "pristine consultancy",
    "noventiq", "metabase", "oscilar", "platform.sh", "platformsh", "upsun",
    "fivetran", "sendcloud", "aiq", "tii", "technology innovation institute",
    "microsoft", "fanatics", "fanatics momentum", "momentum", "midis", "midis group",
    "e-hosting datafort", "az group", "az-group", "innovo", "innovo group",
    "alibaba", "alibaba cloud", "americana", "oracle",
    "g42", "inception42", "omni g42",
    # WA121 — prior cycle applied/blocker
    "akuity", "quantiphi", "cisco", "cisco (splunk)", "splunk",
    "algolia",
    "solo.io", "soloio", "solo io", "candura", "candura ia", "cloudjune",
    "globant",
    "zscaler", "docker", "docker inc", "twilio", "together ai", "together",
    # WA122 applied
    "grafana", "grafana labs", "grafanalabs", "newtwen",
    # WA123 applied/blocker
    "dremio", "sysdig",
    # WA124 applied
    "synthesia", "ignitetech", "ignite tech", "epam",
    # WA125 applied
    "fireworks", "fireworks ai", "fireworksai",
    # WA126 applied
    "coder", "incident.io", "incidentio", "incident",
    # WA127 applied
    "celonis",
    # WA129 applied
    "clearml", "clear.ml", "clear ml", "wundergraph", "wunder graph",
    # WA132 applied
    "müller's solutions", "mullers solutions", "muller", "müllers", "techcarrot", "tech carrot",
    # WA133 applied
    "optimal group", "optimal", "the optimal group", "damen", "damen shipyards", "damen shipyards group", "qureos",
    # WA134 applied
    "talenzon", "ghobash", "ghobash group", "cns", "gbm", "gbmme", "gbm me",
    "gulf business machines",
    # WA135 applied
    "air arabia", "airarabia", "airarabia group", "air arabia group",
    # WA136 blockers do-not-reloop
    "mindtel", "shamal", "tencent", "tencent cloud",
    # WA155 do-not-reloop extras
    "scaleops",  # Head of Channels sales
    "far.ai", "far ai", "farai",  # WA154 Ashby spam blocker — do not reloop
    "eggai", "egg ai", "sanity", "duckduckgo",
    # WA139 applied + WA155 night skips
    "knock", "cloudzero", "cloud zero",
    "bayt", "metabase",  # CAPTCHA/SSO
}

# Expand hard skip from APPLIED_COMPANIES (company-level dedupe)
for _line in (base / "APPLIED_COMPANIES.txt").read_text().splitlines():
    _c = re.sub(r"\b(llc|ltd|inc|corp|co|limited|plc|gmbh)\b", "", _line.strip().lower()).strip(" .,")
    if _c:
        HARD_SKIP.add(_c)


DO_NOT_RELOOP_URL_SUBSTR = [
    # WA152 probes — do not reloop
    "jobs.ashbyhq.com/far.ai/a5cc0d32-533a-4cee-bc28-3b494f331d34",  # WA154 Ashby spam
    "job-boards.greenhouse.io/reddit/jobs/8018517",  # NL payroll
    "jobs.ashbyhq.com/confluent/4218f1c2-3679-4aff-a458-20ef09817fc4",  # Ontario
    "jobs.ashbyhq.com/oscilar/",  # US+CA auth
    "job-boards.greenhouse.io/cortex/",  # US-only
    "jobs.ashbyhq.com/valon/",  # SF/NY
    "jobs.ashbyhq.com/moderntreasury/",  # I-9
    "job-boards.greenhouse.io/togetherai/",  # Bangalore
    "job-boards.greenhouse.io/scaleops/",  # sales
    # WA155 — recent applies
    "jobs.ashbyhq.com/kong",
    "jobs.ashbyhq.com/cognition",
    "jobs.ashbyhq.com/socket",
    "jobs.ashbyhq.com/livekit",
    # WA137/WA155 night skips — do not reloop
    "calendly/jobs/8628979002",  # Staff Platform Engineer Remote-US
    "snowflake",  # Israel-auth SA attempted WA137
    "jobs.ashbyhq.com/snowflake",
    "jobs.ashbyhq.com/knock",  # WA139 applied

    "netomi", "saasgroup", "saas.group", "planetscale",
    "livekit", "temporal", "cloudlinux", "proxify",
    "doit", "railway", "oyster", "pencil", "deepgram",
    "weaviate", "roboflow",
    # WA103 blockers — do not reloop
    "astoria.ai", "starbridge.ai", "coinmarketcap", "jobs.lever.co/coinmarketcap",
    "careers.tether.io", "accellor", "netbird",
    # WA104 blockers — do not reloop
    "tenchisecurity", "tenchi-security", "aiwiorg", "join.com/companies/aiwiorg", "mingla.com", "mingla.io",
    # WA123-WA126
    "sysdig", "jobs.lever.co/sysdig", "fireworks", "jobs.ashbyhq.com/fireworks",
    "jobs.ashbyhq.com/coder", "jobs.ashbyhq.com/incident", "jobs.ashbyhq.com/synthesia",
    "duckduckgo", "jobs.ashbyhq.com/duckduckgo",
    "celonis", "job-boards.greenhouse.io/celonis", "boards.greenhouse.io/celonis",
]

GUEST_ATS = re.compile(
    r"(greenhouse\.io|boards\.greenhouse\.io|job-boards\.(?:eu\.)?greenhouse\.io|"
    r"ashbyhq\.com|lever\.co|workable\.com|ats\.rippling\.com|"
    r"teamtailor\.com|personio\.(de|com)|smartrecruiters\.com|bamboohr\.com|"
    r"recruitee\.com|join\.com|pinpointhq\.com|comeet\.co|comeet\.com)",
    re.I,
)

# Location-field hard patterns
LOC_US = re.compile(
    r"(united states|\busa\b|\bu\.s\.a?\b|\bus\b|canada|north america|"
    r"san francisco|palo alto|menlo park|mountain view|sunnyvale|seattle|austin|"
    r"new york|\bnyc\b|boston|chicago|denver|los angeles|toronto|vancouver|"
    r"foster city|manhattan|bellevue|dallas|georgia|california|massachusetts|"
    r"remote\s*[\-(]?\s*(usa|us|united states|canada|na)\b)",
    re.I,
)
LOC_EU_UK = re.compile(
    r"(\buk\b|united kingdom|london|berlin|amsterdam|paris|stockholm|warsaw|"
    r"poland|prague|czechia|munich|milan|madrid|spain|italy|germany|france|"
    r"europe|\beu\b|remote\s*[-–—]?\s*(uk|eu|europe))",
    re.I,
)
LOC_INDIA = re.compile(r"(\bindia\b|bangalore|bengaluru|hyderabad|pune|chennai|mumbai|delhi)", re.I)
LOC_OTHER_LOCKED = re.compile(
    r"(singapore|tokyo|japan|seoul|korea|sydney|australia|mexico city|latam|"
    r"argentina|brazil|thailand|bangkok|israel)",
    re.I,
)
LOC_GOOD = re.compile(
    r"(worldwide|anywhere|work from anywhere|\bwfa\b|global remote|"
    r"remote\s*[-–—]?\s*emea|\bemea\b|\bmena\b|\buae\b|dubai|middle east|"
    r"international|remote\s*[-–—]?\s*(world|global)|fully remote|"
    r"50\+?\s*countries|wherever|remote\s*[-–—]?\s*apac|\bapac\b)",
    re.I,
)
LOC_SOFT_REMOTE = re.compile(r"^(remote|remote work|remote\s*[-–—]?)\s*$", re.I)

TITLE_BOOST = re.compile(
    r"(architect|platform|cloud|devops|sre|infrastructure|llmops|aiops|devsecops|"
    r"engineering manager|head of|director|staff|principal|avs?p|solution|finops|"
    r"mlops|ai infra|ai platform|vp |vice president)",
    re.I,
)
WEAK = re.compile(
    r"\b(sales|account executive|\bae\b|sdr|bdr|intern|junior|customer success|"
    r"recruiter|people partner|\bhr\b|marketing|product designer|phd new grad|new grad|"
    r"frontend only|ios engineer|android engineer|creative director|human resources|"
    r"business development|tax platform|advisory partner)\b",
    re.I,
)


def classify_family(title):
    t = (title or "").lower()
    if re.search(r"\b(ai architect|ai infra|ai platform|mlops|llmops|genai|generative ai|agentic|gpu|ml platform|head of ai|llm)\b", t):
        return "ai"
    if re.search(r"\b(platform|sre|site reliability|devops|devsecops|kubernetes|k8s|infrastructure engineer|observability|aiops)\b", t):
        return "platform"
    if re.search(r"\b(cloud|solutions architect|azure|aws|gcp|oci|finops|landing zone)\b", t):
        return "cloud"
    return "platform"

def norm_co(s):
    return re.sub(r"\b(llc|ltd|inc|corp|co|limited|plc|gmbh)\b", "", (s or "").strip().lower()).strip(" .,")

def fit_score(h):
    score = int(h.get("fit") or 0) * 10
    title = h.get("title") or ""
    if TITLE_BOOST.search(title):
        score += 40
    if re.search(r"(head of|director|vp |principal|staff|architect|engineering manager)", title, re.I):
        score += 25
    if re.search(r"(cloud|platform|ai |llm|infra|devops|sre|solution|finops)", title, re.I):
        score += 15
    if h.get("geo_reason") == "ok_good":
        score += 35
    # Remote night bias: WFA/worldwide/EMEA first; MENA/UAE still good
    blob = f"{h.get('location') or ''} {h.get('workplaceType') or ''} {h.get('title') or ''} {h.get('company') or ''}".lower()
    if any(k in blob for k in ("worldwide", "anywhere", "wfa", "work from anywhere", "global remote", "fully remote")):
        score += 55
    elif "emea" in blob or "apac" in blob:
        score += 45
    elif any(k in blob for k in ("mena", "middle east", "dubai", "uae", "gcc")):
        score += 35
    if h.get("guest_ats"):
        score += 20
    # Gmail signed out — deprioritize email-only vs guest ATS
    if h.get("source") == "hn-sep2026-email" and h.get("emails"):
        score += 5
    if h.get("emails") and not h.get("guest_ats"):
        score -= 10
    if h.get("emails") and h.get("guest_ats"):
        score += 5
    if WEAK.search(title):
        score -= 50
    return score

def geo_classify(h):
    loc = (h.get("location") or "").strip()
    wt = str(h.get("workplaceType") or "").strip()
    loc_all = f"{loc} {wt}".strip()
    snippet = (h.get("content_snippet") or "")[:600]

    # 1) Location field wins for hard skips
    if loc_all:
        if LOC_INDIA.search(loc_all):
            return "skip_india"
        if LOC_US.search(loc_all) and not LOC_GOOD.search(loc_all):
            return "skip_us"
        if LOC_EU_UK.search(loc_all) and not LOC_GOOD.search(loc_all):
            # EMEA in location upgrades; bare London/UK without EMEA/worldwide = skip
            return "skip_eu_uk"
        if LOC_OTHER_LOCKED.search(loc_all) and not LOC_GOOD.search(loc_all):
            return "skip_geo_locked"
        if LOC_GOOD.search(loc_all):
            return "ok_good"
        if LOC_SOFT_REMOTE.match(loc) or wt.lower() == "remote":
            return "ok_soft"
        # Ambiguous location string — soft if mentions remote somewhere
        if re.search(r"remote", loc_all, re.I):
            return "ok_soft"

    # 2) No location — use snippet carefully
    if LOC_GOOD.search(snippet) and not LOC_US.search(snippet[:200]):
        return "ok_soft"
    if not loc_all:
        return "ok_soft"
    return "skip_unclear"

skipped = []
apply_ready = []
skip_breakdown = {}

for h in disc.get("discovered") or []:
    co = norm_co(h.get("company") or "")
    url = (h.get("apply_url") or h.get("url") or "").rstrip("/")
    reason = None
    if co in companies or co in HARD_SKIP:
        reason = "company_dedupe"
    elif any(s in url.lower() for s in DO_NOT_RELOOP_URL_SUBSTR):
        reason = "do_not_reloop"
    elif url in urls:
        reason = "url_dedupe"
    elif WEAK.search(h.get("title") or ""):
        reason = "weak_title"
    else:
        reason = geo_classify(h)
        if not reason.startswith("skip_"):
            h = dict(h)
            h["guest_ats"] = bool(GUEST_ATS.search(url))
            h["geo_reason"] = reason
            h["fit_score"] = fit_score(h)
            apply_ready.append(h)
            continue
    skip_breakdown[reason] = skip_breakdown.get(reason, 0) + 1
    if len(skipped) < 500:
        skipped.append({"company": h.get("company"), "title": h.get("title"), "reason": reason, "location": h.get("location"), "url": url[:120]})

apply_ready.sort(key=lambda x: (-x.get("fit_score", 0), x.get("title") or ""))
guest = [x for x in apply_ready if x.get("guest_ats")]
good = [x for x in apply_ready if x.get("geo_reason") == "ok_good"]
soft = [x for x in apply_ready if x.get("geo_reason") == "ok_soft"]

out = {
    "batch": "BATCH_REMOTE_NIGHT_SEP22_WA155",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "mode": "remote_night",
    "discovered": disc.get("counts", {}).get("unique") or len(disc.get("discovered") or []),
    "discovery_counts": disc.get("counts"),
    "apply_ready_count": len(apply_ready),
    "skipped_count": sum(skip_breakdown.values()),
    "skip_breakdown": skip_breakdown,
    "guest_ats_count": len(guest),
    "geo_good_count": len(good),
    "geo_soft_count": len(soft),
    "top": apply_ready[:40],
    "apply_ready": apply_ready,
    "skipped_sample": skipped[:100],
}
(base / "QUEUE_REMOTE_NIGHT_SEP22_WA155.json").write_text(json.dumps(out, indent=2))

def ats_priority(h):
    url = (h.get("apply_url") or h.get("url") or "").lower()
    src = (h.get("source") or "").lower()
    # Prefer HN email / mailto apply — highest throughput for thin remote market
    if h.get("emails") or src.startswith("hn-sep2026") or src.startswith("hn-"):
        return -10
    if "ashby" in url or src == "ashby":
        return 50  # deprioritize — box IP spam-flagged
    if "recruitee" in url or src == "recruitee":
        return -1
    if "join.com" in url or src == "joincom":
        return -1
    if "pinpoint" in url or src == "pinpoint":
        return 0
    if "greenhouse" in url or src == "greenhouse":
        return 0
    if "lever.co" in url or src == "lever":
        return 1
    if "workable" in url or src == "workable":
        return 2
    if "rippling" in url or src == "rippling":
        return 3
    if "smartrecruiters" in url or src == "smartrecruiters":
        return 4
    if h.get("guest_ats"):
        return 5
    return 10

seen_co = set()
apply_q = []
# Prefer geo_good + HN email + non-Ashby guest ATS
ranked = sorted(good + soft, key=lambda h: (ats_priority(h), -h.get("fit_score", 0), h.get("title") or ""))
for h in ranked:
    title = h.get("title") or ""
    if WEAK.search(title):
        continue
    has_email = bool(h.get("emails")) or (h.get("source") or "").startswith("hn-sep2026")
    if not h.get("guest_ats") and h.get("source", "").startswith("jobicy"):
        pass
    elif not h.get("guest_ats") and h.get("geo_reason") != "ok_good" and not has_email:
        continue
    url = (h.get("apply_url") or h.get("url") or "").lower()
    if ("ashby" in url or (h.get("source") or "") == "ashby"):
        non_ash = sum(1 for x in apply_q if "ashby" not in ((x.get("apply_url") or x.get("url") or "").lower()))
        if non_ash < 12:
            continue
    co = norm_co(h.get("company") or "")
    if co in seen_co:
        continue
    seen_co.add(co)
    apply_q.append(h)
    if len(apply_q) >= 25:
        break

(base / "QUEUE_REMOTE_NIGHT_SEP22_WA155_APPLY.json").write_text(json.dumps({
    "batch": "BATCH_REMOTE_NIGHT_SEP22_WA155",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "count": len(apply_q),
    "jobs": apply_q,
}, indent=2))

print("discovered", out["discovered"])
print("apply_ready", len(apply_ready), "guest", len(guest), "good", len(good), "soft", len(soft))
print("skip_breakdown", skip_breakdown)
# Curated top for same-cycle submit (remote WFA/EMEA-first)
curated = []
for h in apply_q:
    locb = f"{h.get('location') or ''} {h.get('workplaceType') or ''}".lower()
    remoteish = any(k in locb for k in ("dubai","abu dhabi","uae","mena","middle east","gcc","emea","worldwide","anywhere","wfa","remote"))
    if h.get("guest_ats") or h.get("emails") or remoteish:
        curated.append(h)
(base / "QUEUE_REMOTE_NIGHT_SEP22_WA155_CURATED.json").write_text(json.dumps({
    "batch": "BATCH_REMOTE_NIGHT_SEP22_WA155",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "count": len(curated),
    "jobs": curated[:15],
}, indent=2))
print("APPLY queue", len(apply_q), "curated", len(curated[:15]))
print("\n=== GEO GOOD ===")
for h in good[:25]:
    print(f"  [{h.get('fit_score')}] guest={h.get('guest_ats')} {h.get('source')} {h.get('company')} — {h.get('title')[:55]} | {h.get('location')} | {(h.get('apply_url') or '')[:80]}")
print("\n=== APPLY Q ===")
for h in apply_q:
    print(f"  [{h.get('fit_score')}] {h.get('geo_reason')} guest={h.get('guest_ats')} {h.get('source')} {h.get('company')} — {h.get('title')[:55]} | {h.get('location')} | {(h.get('apply_url') or '')[:80]}")
