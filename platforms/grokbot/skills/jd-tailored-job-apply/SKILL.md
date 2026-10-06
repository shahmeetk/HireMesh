---
name: JD-tailored job apply
description: >-
  use when applying to a job — JD-tailor resume (strong_emphasis: summary +
  HTML experience + skills + retarget_headline) via Reactive Resume,
  fallback_and_flag Max-ATS on AI/gate fail, never re-apply same company/URL
---

## Tailor prefs
1. Depth = `strong_emphasis` (no invented facts)
2. Headline = `retarget_headline`
3. Fallback = `fallback_and_flag` (continue apply)

## Quality gate
summary AND experience HTML AND skills must each differ from master.

## Scripts
`scripts/jd_tailor_resume.py`, `scripts/jd_strong_emphasis_align.py`, `scripts/jd_cover_letter.py`
