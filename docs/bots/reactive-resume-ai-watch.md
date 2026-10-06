# Reactive Resume AI Watch

## Use case

Probe Reactive Resume AI; write RXRESU_AI_STATUS.json

**Mode:** health-only  
**Schedule (Asia/Dubai example):** folded into Session Guard (optional standalone)  
**Helper script:** `scripts/rxresu_ai_probe.py`

## Worked example

**Input:** RXRESU API key present

**Steps:**
1) Lightweight AI tailor probe
2) Write RXRESU_AI_STATUS.json

**Output artifact:** `status/RXRESU_AI_STATUS.json`

**Sample brief message:**
> RXRESU AI: ok=true latency=1.8s

*(All company names and contacts in examples are fake.)*

## Schedule

`folded into Session Guard (optional standalone)` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | RXRESU API |
| Writes | status/RXRESU_AI_STATUS.json |

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
