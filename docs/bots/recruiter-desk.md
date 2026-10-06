# Recruiter Desk

## Use case

Inbound recruiter triage → reply drafts

**Mode:** draft-only  
**Schedule (Asia/Dubai example):** weekdays 09:26 / 13:26 / 17:26  
**Helper script:** `scripts/recruiter_desk.py`

## Worked example

**Input:** Inbound recruiter thread from ExampleCorp

**Steps:**
1) Classify intent
2) Draft reply
3) Write inbox/RECRUITER_DRAFTS.md

**Output artifact:** `inbox/RECRUITER_DRAFTS.md`

**Sample brief message:**
> Recruiter Desk: 1 draft ready (not sent).

*(All company names and contacts in examples are fake.)*

## Schedule

`weekdays 09:26 / 13:26 / 17:26` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | Gmail recruiter threads |
| Writes | inbox/RECRUITER_DRAFTS.md |

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
