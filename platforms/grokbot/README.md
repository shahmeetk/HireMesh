# Grok Bot port

Original HireMesh workers ran as **scheduled routines** on the Grok Bot desktop-assistant platform, with shared skills for orchestration and JD-tailored apply.

> **Note:** Routine prompt text here is **reconstructed** from the live mesh design docs and helper scripts. Platform-private scheduler metadata is not included.

## Import

1. Copy `skills/hire-mesh-pipeline/SKILL.md` and `skills/jd-tailored-job-apply/SKILL.md` into your Grok Bot skills library.
2. For each folder under `routines/`, create a scheduled routine with the `prompt.md` body and the cron hint in `schedule.txt`.
3. Set env `HIREMESH_HOME`, `HIREMESH_TZ`, and Reactive Resume vars from `.env.example`.
4. Ensure the box/browser has Gmail + LinkedIn sessions if you use those lanes.

## Tool mapping (Grok-specific → generic)

| Grok Bot capability | Generic equivalent |
|---------------------|--------------------|
| Computer Use / browser | Playwright / Puppeteer / Chrome CDP |
| Gmail connector | Gmail API / IMAP + SMTP |
| File tools | Local filesystem under HIREMESH_HOME |
| Workflow skills | SKILL.md playbooks |
| Routines scheduler | cron / launchd / platform schedules |
