# Contributing

Thanks for improving HireMesh.

## Guidelines

1. Keep the mesh **sanitized** — no real emails, API keys, resume IDs, phone numbers, or applied-company lists in commits.
2. Prefer additive workers and shared-file handoffs over tight coupling.
3. Draft-only outreach stays draft-only.
4. Document new bots under `docs/bots/<slug>.md` and add a row to the README table.
5. Run `python3 -m py_compile scripts/*.py` before opening a PR.

## PR checklist

- [ ] Placeholders / env vars for secrets
- [ ] Bot mode (discover / draft / acting) stated
- [ ] Schedule + reads/writes updated
- [ ] Scripts compile
