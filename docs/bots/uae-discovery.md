# UAE Discovery

## Use case

Daytime Bayt/GulfTalent/GCC careers → APPLY_READY lane=uae

**Mode:** discover-only  
**Schedule (Asia/Dubai example):** 08:56–16:56 / 2h  
**Helper script:** `scripts/uae_board_desk_hire_mesh.py`

## Worked example

**Input:** Daytime window; UAE boards

**Steps:**
1) Pull Himalayas country=AE + UAE HTTP supplements
2) Force lane=uae; drop fully-remote-only
3) Merge into APPLY_READY

**Output artifact:** `APPLY_READY rows with lane=uae`

**Sample brief message:**
> UAE Discovery: +11 uae roles. No applies.

*(All company names and contacts in examples are fake.)*

## Schedule

`08:56–16:56 / 2h` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | excludes, lane_router |
| Writes | queues/APPLY_READY.json (lane=uae) |

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
