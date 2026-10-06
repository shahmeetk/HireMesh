---
name: Hire Mesh pipeline
description: >-
  use when running or changing the HireMesh multi-worker job pipeline
  (Scout, Fit Gate, Apply Engine, ATS Hunter, Mail Guard, Recruiter Desk,
  Career Coach, UAE Discovery, Follow-Up, Reply Radar, Warm Outreach,
  Story Bank, Session Guard, Health Retry)
---

## Lane rule
UAE-based OR fully remote (exclusive). Day → UAE queue; night → remote queue.

## Principle
Independent scheduled workers share `$HIREMESH_HOME/{queues,status,inbox}`. They never wait on each other.

## Always
- Read `docs/architecture.md` / `HIREMESH_HOME` config
- Update `status/MESH_STATUS.json`
- No remote salary floor; published emails only; company/URL dedupe
- Applies use skill `jd-tailored-job-apply`
