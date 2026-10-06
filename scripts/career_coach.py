#!/usr/bin/env python3
"""Career Coach — weekly quality/quantity + conversion digest (read-only)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
STATUS = ROOT / "status"


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for l in path.read_text(errors="ignore").splitlines() if l.strip() and not l.startswith("#"))


def main() -> None:
    STATUS.mkdir(parents=True, exist_ok=True)
    funnel = {}
    fp = STATUS / "FUNNEL.json"
    if fp.exists():
        try:
            funnel = json.loads(fp.read_text())
        except json.JSONDecodeError:
            pass
    stages = funnel.get("stages", {})
    applied = count_lines(ROOT / "APPLIED_COMPANIES.txt")
    md = [
        "# Weekly Career Coach digest\n",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_\n",
        "## Volume\n",
        f"- Companies applied (ledger): **{applied}**\n",
        "## Funnel\n",
    ]
    for s in ("applied", "replied", "screen", "interview", "offer", "rejected"):
        md.append(f"- {s}: {len(stages.get(s, []))}\n")
    md += [
        "\n## Recommendations\n",
        "- Protect fit-first: raise Fit Gate min score if APPLY_READY is noisy.\n",
        "- Send outstanding drafts in inbox/FOLLOWUPS.md and inbox/WARM_PATH.md.\n",
        "- Clear blocker backlog asynchronously; do not pause Scout/Engine.\n",
        "- Review TAILOR_FALLBACK_RETRY.jsonl and re-tailor when Reactive Resume AI is healthy.\n",
    ]
    (STATUS / "WEEKLY_COACH.md").write_text("".join(md))
    print(json.dumps({"ok": True, "applied_ledger": applied}))


if __name__ == "__main__":
    main()
