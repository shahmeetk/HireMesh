# Warm Outreach

## Use case

HM/recruiter note drafts for strong fits

**Mode:** draft-only  
**Schedule (Asia/Dubai example):** weekdays 12:26  
**Helper script:** `scripts/warm_outreach.py`

## Worked example

**Input:** Top-fit recent applies

**Steps:**
1) Pick top fit_score
2) Draft HM/recruiter notes

**Output artifact:** `inbox/WARM_PATH.md`

**Sample brief message:**
> Warm Outreach: 3 drafts (not sent).

*(All company names and contacts in examples are fake.)*

## Schedule

`weekdays 12:26` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | APPLY_LOG, APPLY_READY |
| Writes | inbox/WARM_PATH.md |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **draft-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
