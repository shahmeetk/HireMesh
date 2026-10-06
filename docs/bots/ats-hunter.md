# ATS Hunter

## Use case

Guest Greenhouse/Lever/Workable/Ashby closer

**Mode:** acting (guest ATS)  
**Schedule (Asia/Dubai example):** :41 every 2h  
**Helper script:** `scripts/ats_hunter.py`

## Worked example

**Input:** APPLY_READY guest_ats=true

**Steps:**
1) Prefer Greenhouse/Lever/Workable guest forms
2) Submit confirmable applications
3) Ledger company+URL

**Output artifact:** `status/HUNTER_RESULTS.json`

**Sample brief message:**
> Hunter: 3 guest confirms, 2 blockers → backlog.

*(All company names and contacts in examples are fake.)*

## Schedule

`:41 every 2h` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | APPLY_READY (guest_ats first), APPLIED_* |
| Writes | status/HUNTER_RESULTS.json, APPLIED_* |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **acting (guest ATS)** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
