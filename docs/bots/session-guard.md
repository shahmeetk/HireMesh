# Session Guard

## Use case

Probe Gmail, LinkedIn, Reactive Resume AI

**Mode:** health-only  
**Schedule (Asia/Dubai example):** 08:36 / 14:36 / 20:36  
**Helper script:** `scripts/session_guard.py`

## Worked example

**Input:** Scheduled health window

**Steps:**
1) Probe Gmail/LinkedIn/RXRESU
2) Write SESSION_GUARD.json
3) Set HEALTH_RETRY_NEEDED

**Output artifact:** `status/SESSION_GUARD.json`

**Sample brief message:**
> Session Guard: healthy (quiet).

*(All company names and contacts in examples are fake.)*

## Schedule

`08:36 / 14:36 / 20:36` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | sessions / RXRESU |
| Writes | status/SESSION_GUARD.json, HEALTH_RETRY_NEEDED.json |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **health-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
