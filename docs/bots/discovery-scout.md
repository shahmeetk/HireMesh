# Discovery Scout

## Use case

Free-API + portal discovery; rank fit/geo into APPLY_READY

**Mode:** discover-only  
**Schedule (Asia/Dubai example):** :11 every 2h  
**Helper script:** `scripts/job_scout_hire_mesh.py`

## Worked example

**Input:** Empty or stale APPLY_READY; excludes loaded

**Steps:**
1) Fetch Remotive/RemoteOK/Himalayas/Arbeitnow/GH boards
2) Classify lane (UAE vs remote) by time of day
3) Dedupe APPLIED_*
4) Write SCOUT_QUEUE + APPLY_READY

**Output artifact:** `queues/APPLY_READY.json with ~N ranked jobs`

**Sample brief message:**
> Scout: +42 apply_ready (28 remote / 14 uae), guest_ats=19. Quiet otherwise.

*(All company names and contacts in examples are fake.)*

## Schedule

`:11 every 2h` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | excludes, SALARY_POLICY, portals |
| Writes | queues/SCOUT_QUEUE.json, queues/APPLY_READY.json, status/MESH_STATUS.json |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **discover-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
