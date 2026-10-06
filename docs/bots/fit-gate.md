# Fit Gate

## Use case

Local BM25+seniority+lane re-rank; drop weak rows

**Mode:** rank-only  
**Schedule (Asia/Dubai example):** :18 every 2h  
**Helper script:** `scripts/fit_gate_hire_mesh.py`

## Worked example

**Input:** SCOUT_QUEUE / noisy APPLY_READY

**Steps:**
1) BM25 + title family + seniority
2) Exclusive lane check
3) Drop below min score

**Output artifact:** `trimmed APPLY_READY + FIT_GATE_DROPPED_LAST.json`

**Sample brief message:**
> Fit Gate: kept 86 / dropped 54 (inquiry spam, junior).

*(All company names and contacts in examples are fake.)*

## Schedule

`:18 every 2h` — override via your platform scheduler / cron. Timezone: `HIREMESH_TZ` (default `Asia/Dubai`).

## Reads / writes

| Direction | Artifacts |
|-----------|-----------|
| Reads | SCOUT_QUEUE / APPLY_READY, FIT_GATE.json |
| Writes | APPLY_READY.json, status/FIT_GATE_DROPPED_LAST.json |

## Safety rules

- Respect site ToS and rate limits
- No invented emails or resume facts
- Update MESH_STATUS heartbeat every run
- Never pause sibling workers on blockers
- Mode enforcement: **rank-only** — do not exceed this lane

## Failure modes & recovery

| Failure | Recovery |
|---------|----------|
| Empty upstream queue | Heartbeat + exit quiet |
| Auth / SSO / CAPTCHA | Log `status/BLOCKER_BACKLOG.md`; continue other jobs |
| API 5xx / timeout | Retry once; flag and move on |
| Deduped company/URL | Skip silently |
| Downstream consumer missing | Still write artifacts; siblings pick up next tick |
