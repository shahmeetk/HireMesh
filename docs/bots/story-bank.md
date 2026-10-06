# Story Bank

## Use case

Weekly STAR bank refresh from resume + JD themes

**Mode:** prep-only  
**Schedule (Asia/Dubai example):** Sundays 18:26  
**Helper script:** `scripts/story_bank.py`

## Worked example

**Input:** Master resume themes + recent JD titles

**Steps:**
1) Refresh STAR stubs
2) List JD themes

**Output artifact:** `status/STORY_BANK.md`

**Sample brief message:**
> Story Bank refreshed (5 core stories).

*(All company names and contacts in examples are fake.)*

## Schedule

`Sundays 18:26` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | master resume, recent JDs |
| Writes | status/STORY_BANK.md |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **prep-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
