# Mail Guard

## Use case

Bounce harvest + published hiring-email verify

**Mode:** verify-only  
**Schedule (Asia/Dubai example):** 08:56 / 14:56 / 20:56  
**Helper script:** `scripts/mail_guard.py`

## Worked example

**Input:** Gmail DSN + careers page harvest

**Steps:**
1) Parse bounces
2) Verify published hiring emails
3) Update EMAIL_SAFE

**Output artifact:** `BOUNCES.json + EMAIL_SAFE.json`

**Sample brief message:**
> Mail Guard: 1 bounce remapped; 2 published emails verified.

*(All company names and contacts in examples are fake.)*

## Schedule

`08:56 / 14:56 / 20:56` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | Gmail DSNs, careers pages |
| Writes | status/BOUNCES.json, queues/EMAIL_SAFE.json |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **verify-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
