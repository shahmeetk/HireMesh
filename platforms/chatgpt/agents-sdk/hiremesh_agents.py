#!/usr/bin/env python3
"""HireMesh — OpenAI Agents SDK sketch (scout → fit_gate → tailor → apply_drafter)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

try:
    from agents import Agent, Runner, function_tool
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install openai-agents: pip install openai-agents") from e

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
HOME = Path(os.environ.get("HIREMESH_HOME", ROOT / "examples")).resolve()


def _run(script: str, *args: str) -> str:
    env = os.environ.copy()
    env["HIREMESH_HOME"] = str(HOME)
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.stdout or p.stderr or f"exit={p.returncode}"


@function_tool
def run_scout() -> str:
    """Run Discovery Scout helper to refresh APPLY_READY."""
    return _run("job_scout_hire_mesh.py")


@function_tool
def run_fit_gate() -> str:
    """Re-rank APPLY_READY via Fit Gate."""
    return _run("fit_gate_hire_mesh.py")


@function_tool
def run_tailor(company: str, role: str, jd_text: str) -> str:
    """JD-tailor resume for a role (writes tailored PDF / sidecar under HIREMESH_HOME)."""
    jd_path = HOME / "status" / "_tmp_jd.txt"
    jd_path.parent.mkdir(parents=True, exist_ok=True)
    jd_path.write_text(jd_text)
    return _run("jd_tailor_resume.py", "--company", company, "--role", role, "--jd-file", str(jd_path))


@function_tool
def draft_followups() -> str:
    """Draft follow-up emails into inbox/FOLLOWUPS.md (never sends)."""
    return _run("follow_up_writer.py")


@function_tool
def read_apply_ready() -> str:
    """Read current APPLY_READY.json."""
    path = HOME / "queues" / "APPLY_READY.json"
    if not path.exists():
        return "[]"
    return path.read_text()


scout = Agent(
    name="scout",
    instructions="You are HireMesh Discovery Scout. Discover/rank only; never apply. Use run_scout and read_apply_ready.",
    tools=[run_scout, read_apply_ready],
)

fit_gate = Agent(
    name="fit_gate",
    instructions="You are HireMesh Fit Gate. Trim APPLY_READY; never apply.",
    tools=[run_fit_gate, read_apply_ready],
)

tailor = Agent(
    name="tailor",
    instructions="You are HireMesh tailor. Use strong_emphasis via run_tailor; no invented facts.",
    tools=[run_tailor],
)

apply_drafter = Agent(
    name="apply_drafter",
    instructions=(
        "You prepare apply packets and follow-ups. Prefer confirmable ATS notes; "
        "draft emails only to published addresses; never claim you sent mail. Use draft_followups."
    ),
    tools=[draft_followups, read_apply_ready],
)

orchestrator = Agent(
    name="hiremesh_triage",
    instructions=(
        "You are HireMesh triage. Route: discovery→scout, ranking→fit_gate, "
        "resume tailoring→tailor, apply/follow-up drafts→apply_drafter. "
        "Enforce lane rule, dedupe, published-email-only, draft-only outreach."
    ),
    handoffs=[scout, fit_gate, tailor, apply_drafter],
)


def main() -> None:
    worker = (sys.argv[sys.argv.index("--worker") + 1] if "--worker" in sys.argv else "triage")
    prompt = {
        "scout": "Run a discovery cycle and summarize APPLY_READY.",
        "fit_gate": "Run fit gate and summarize keeps/drops.",
        "tailor": "Wait for user JD; otherwise explain how to tailor.",
        "apply": "Prepare follow-up drafts for aged applies.",
        "triage": "Check queues and route to the right HireMesh worker.",
    }.get(worker, "Check queues and route to the right HireMesh worker.")
    target = {
        "scout": scout,
        "fit_gate": fit_gate,
        "tailor": tailor,
        "apply": apply_drafter,
    }.get(worker, orchestrator)
    result = Runner.run_sync(target, prompt)
    print(result.final_output)


if __name__ == "__main__":
    main()
