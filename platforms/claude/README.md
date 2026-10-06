# Claude port

## Layout

- `.claude/agents/*.md` — Claude Code subagents (YAML frontmatter + system prompt)
- `skills/<bot>/SKILL.md` — Agent Skills for core workflows
- `.claude/commands/*.md` — slash commands (`/hiremesh-scout`, `/hiremesh-apply`, `/hiremesh-status`)

## Setup

1. Copy `.claude/` into your Claude Code project root.
2. Copy `skills/` into your Agent Skills path (or project skills dir).
3. Export env from repo `.env.example`.
4. MCP servers (describe generically — use whatever you already trust):
   - **Filesystem** — read/write `$HIREMESH_HOME`
   - **Browser automation** — e.g. Playwright MCP for ATS forms / careers pages
   - **Gmail** — for Mail Guard, Reply Radar, Recruiter Desk drafts

### Grok-Bot-only → Claude mapping

| Grok capability | Claude approach |
|-----------------|-----------------|
| Computer Use | Playwright MCP / browser tools |
| Gmail connector | Gmail MCP or API scripts |
| Routines | `claude -p` headless + cron/launchd |
| Skills | Agent Skills (`SKILL.md`) |
| Subagents | `.claude/agents/` |

## Scheduling example (cron)

```cron
HIREMESH_HOME=/data/hiremesh
TZ=Asia/Dubai
11 */2 * * * cd /opt/HireMesh && claude -p "/hiremesh-scout" --allowedTools "Read,Write,Bash,Agent"
26 */2 * * * cd /opt/HireMesh && claude -p "/hiremesh-apply" --allowedTools "Read,Write,Bash,Agent,mcp__playwright__*,mcp__gmail__*"
36 8,14,20 * * * cd /opt/HireMesh && claude -p "/hiremesh-status"
```

Use headless `claude -p` only in environments you control; keep human-in-the-loop for sends.
