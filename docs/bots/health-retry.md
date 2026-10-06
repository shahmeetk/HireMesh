# Health Retry

## Use case

Dense rechecks until Session Guard is healthy; then idle

**Mode:** health-only  
**Schedule (Asia/Dubai example):** :23/:53 08–21 (only when unhealthy)  
**Helper script:** `scripts/health_retry.py`

## Worked example

**Input:** HEALTH_RETRY_NEEDED=true

**Steps:**
1) Re-run Session Guard
2) Exit/skip when healthy

**Output artifact:** `status/HEALTH_RETRY_LAST.json`

**Sample brief message:**
> Health Retry: recovered — pausing dense checks.

*(All company names and contacts in examples are fake.)*

## Schedule

`:23/:53 08–21 (only when unhealthy)` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | HEALTH_RETRY_NEEDED.json |
| Writes | status/HEALTH_RETRY_LAST.json |

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
