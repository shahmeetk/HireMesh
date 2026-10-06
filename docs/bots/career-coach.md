# Career Coach

## Use case

Weekly quality/quantity + conversion digest

**Mode:** read-only  
**Schedule (Asia/Dubai example):** Mondays 08:26  
**Helper script:** `scripts/career_coach.py`

## Worked example

**Input:** Week of APPLY_LOG + FUNNEL

**Steps:**
1) Tally volume + funnel
2) Recommend fit/follow-up actions

**Output artifact:** `status/WEEKLY_COACH.md`

**Sample brief message:**
> Coach: 37 applies, 4 replies, 1 screen. Send 6 follow-up drafts.

*(All company names and contacts in examples are fake.)*

## Schedule

`Mondays 08:26` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | APPLY_LOG, FUNNEL, blockers |
| Writes | status/WEEKLY_COACH.md |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **read-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
