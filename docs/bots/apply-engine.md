# Apply Engine

## Use case

JD-tailor via Reactive Resume → quality gate → ATS or published-email submit

**Mode:** acting (ATS/email)  
**Schedule (Asia/Dubai example):** :26 every 2h  
**Helper script:** `scripts/jd_tailor_resume.py`

## Worked example

**Input:** Top APPLY_READY row: ExampleCorp / Platform Lead

**Steps:**
1) JD tailor strong_emphasis
2) Quality gate
3) Export PDF
4) Guest ATS or EMAIL_SAFE PDF
5) Log

**Output artifact:** `tailored PDF + APPLIED_* + sidecar flags`

**Sample brief message:**
> Engine: ExampleCorp submitted (tailored). 1 fallback_and_flag (AI 502).

*(All company names and contacts in examples are fake.)*

## Schedule

`:26 every 2h` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | APPLY_READY, EMAIL_SAFE, master resume |
| Writes | APPLIED_*, APPLY_LOG, tailored PDFs, TAILOR_FALLBACK_RETRY.jsonl |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **acting (ATS/email)** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
