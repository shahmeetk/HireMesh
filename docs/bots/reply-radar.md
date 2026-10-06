# Reply Radar

## Use case

Gmail replies → FUNNEL stages; alert on screens

**Mode:** classify-only  
**Schedule (Asia/Dubai example):** 11:53 / 16:53 / 20:53  
**Helper script:** `scripts/reply_radar.py`

## Worked example

**Input:** Gmail inbox harvest

**Steps:**
1) Classify stage
2) Update FUNNEL
3) Alert on screen/interview

**Output artifact:** `status/FUNNEL.json`

**Sample brief message:**
> Reply Radar: 1 screen alert — ExampleCorp.

*(All company names and contacts in examples are fake.)*

## Schedule

`11:53 / 16:53 / 20:53` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | Gmail |
| Writes | status/FUNNEL.json |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **classify-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
