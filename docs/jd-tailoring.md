# JD tailoring

Owned by **Apply Engine** on every confirmable apply.

## Pipeline

1. Pull JD → score fit
2. Call Reactive Resume API (`scripts/jd_tailor_resume.py`) with depth **`strong_emphasis`**
3. Post-align via `scripts/jd_strong_emphasis_align.py`
4. Quality gate
5. Export tailored PDF **or** Max-ATS fallback
6. Submit ATS / published-email PDF
7. Log application

## `strong_emphasis` depth

- Keep facts true — **no invented** employers, titles, dates, or metrics
- Rewrite summary toward JD keywords
- Reorder + lightly rephrase experience bullets (HTML `description` `<ul><li><p>…`, not only `highlights`)
- Reorder / prioritize skills toward JD

## `retarget_headline`

Change `basics.headline` (and resume display name) to match the target role, e.g. `Platform Engineering Lead — {{CANDIDATE_NAME}}`.

## Quality gate

Before `tailored: true` / `experienceAligned: true`, require that **summary AND experience HTML AND skills** each differ from the Max-ATS master. If any is byte-identical → treat as shallow.

## `fallback_and_flag`

If Reactive Resume AI is down (502/timeout) **or** the quality gate fails:

1. Use Max-ATS master PDF (`HIREMESH_MASTER_PDF`)
2. Set flags: `aiDown` / `tailorShallow` / `fallbackUsed` in the tailor sidecar JSON
3. Append a line to `status/TAILOR_FALLBACK_RETRY.jsonl`
4. **Continue** the apply — do not block the cycle

### Retry log (example)

```json
{"ts":"2026-09-25T08:26:11+04:00","company":"ExampleCorp","role":"AI Platform Lead","reason":"quality_gate","flags":{"tailorShallow":true,"fallbackUsed":true}}
{"ts":"2026-09-25T10:26:04+04:00","company":"DemoAI","role":"Staff SRE","reason":"ai_502","flags":{"aiDown":true,"fallbackUsed":true}}
```

Re-tailor later when Session Guard / Reactive Resume AI Watch reports healthy.
