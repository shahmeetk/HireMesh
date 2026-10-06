# Follow-Up Writer

## Use case

D+3/D+7/D+14 nudge drafts after applies

**Mode:** draft-only  
**Schedule (Asia/Dubai example):** daily 10:53  
**Helper script:** `scripts/follow_up_writer.py`

## Worked example

**Input:** Applies aged ≥3/7/14 days

**Steps:**
1) Scan ledger ages
2) Draft D+3/D+7/D+14 notes

**Output artifact:** `inbox/FOLLOWUPS.md`

**Sample brief message:**
> Follow-Ups: 5 drafts written (human send).

*(All company names and contacts in examples are fake.)*

## Schedule

`daily 10:53` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | APPLY_LOG, FUNNEL |
| Writes | inbox/FOLLOWUPS.md |

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
