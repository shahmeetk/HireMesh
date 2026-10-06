# Getting started

## Prerequisites

- Python 3.10+ (stdlib is enough for most scripts; `urllib` only)
- A writable data dir (`HIREMESH_HOME`) for queues/status/inbox/ledgers
- Optional: Reactive Resume (self-hosted or cloud) for JD tailoring
- Optional: Gmail + browser session for Mail Guard / Reply Radar / Recruiter Desk
- Optional: LinkedIn signed-in browser session for discovery (never Easy Apply)

## Configure the candidate

```bash
export HIREMESH_HOME=~/hiremesh-data
mkdir -p "$HIREMESH_HOME"/{queues,status,inbox,tailored,scripts}
cp config/candidate.example.yaml "$HIREMESH_HOME/config/candidate.yaml"
cp config/roles.example.yaml "$HIREMESH_HOME/config/roles.yaml"
cp config/lanes.example.yaml "$HIREMESH_HOME/config/lanes.yaml"
cp config/exclude_companies.example.txt "$HIREMESH_HOME/exclude_companies.txt"
cp .env.example "$HIREMESH_HOME/.env"
# place your master resume PDF
cp /path/to/master.pdf "$HIREMESH_HOME/config/master_resume.pdf"
```

Edit `candidate.yaml`: name, email, phone, LinkedIn, target cities, work authorization notes.

### Master resume

Point `RXRESU_MASTER_RESUME_ID` / `HIREMESH_MASTER_PDF` at your Max-ATS (or equivalent) master. Apply Engine clones + JD-tailors per role; on AI/gate failure it falls back to this PDF and flags the run.

### Target role families

Default families (edit `roles.yaml`):

1. Cloud / Solutions / multi-cloud / FinOps
2. Platform / SRE / DevOps / DevSecOps
3. AIOps / Observability / Cloud Ops
4. AI / MLOps / LLMOps / AI Infra
5. Leadership overlays (EM / Head / Director / AVP / Principal / Staff)

### Geo lanes

See `lanes.example.yaml`. Day = UAE queue; night = remote queue. Soft-geo EMEA remote counts as remote.

### Exclude lists

`exclude_companies.example.txt` + runtime `APPLIED_COMPANIES.txt` / `APPLIED_URLS.txt` (gitignored).

### Environment

See [`.env.example`](../.env.example). Never commit real keys.

## Run on each platform

### (a) Grok Bot routines

Import skills + routines from `platforms/grokbot/`. Schedule per `docs/architecture.md`. Routines are **reconstructed** from the live mesh (original scheduler prompts were platform-private).

### (b) Claude

See `platforms/claude/README.md`. Use subagents under `.claude/agents/`, skills under `skills/`, and slash commands. Schedule with:

```bash
claude -p "/hiremesh-scout" --allowedTools "Read,Write,Bash,mcp__filesystem__*,mcp__playwright__*"
```

### (c) ChatGPT / OpenAI

- Custom GPT: `platforms/chatgpt/custom-gpt/instructions.md`
- Agents SDK: `platforms/chatgpt/agents-sdk/` (`pip install openai-agents`)

### (d) Plain cron + Python

```cron
HIREMESH_HOME=/data/hiremesh
TZ=Asia/Dubai
11 */2 * * * cd /opt/HireMesh && python3 scripts/job_scout_hire_mesh.py
18 */2 * * * cd /opt/HireMesh && python3 scripts/fit_gate_hire_mesh.py
26 */2 * * * cd /opt/HireMesh && python3 scripts/mesh_status.py --worker apply_engine --ok --notes "drive via agent"
```

Browser/Gmail steps still need an agent or your own automation; scripts handle ranking, tailoring API calls, and file handoffs.
