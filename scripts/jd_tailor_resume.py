#!/usr/bin/env python3
"""Create a JD-specific resume via Reactive Resume AI tailor + strong_emphasis post-align.

Meet locked prefs 2026-09-25:
  depth    = strong_emphasis   (reorder + light rephrase; never invent facts)
  headline = retarget_headline
  fallback = fallback_and_flag (Max-ATS PDF + flags; do not block applies)

Flow:
  1. POST /applications with jobDescription (+ company/role/url)
  2. POST /applications/{id}/ai/tailor-resume  (master Max-ATS)
     - On 502/timeout/empty → Max-ATS PDF + aiDown/fallbackUsed; CONTINUE
  3. GET tailored resume → local strong_emphasis post-align:
       HTML experience description, skills keywords, summary, headline
  4. Quality gate: summary AND experience HTML AND skills each differ from master
     - Fail → Max-ATS PDF + tailorShallow/fallbackUsed; CONTINUE
  5. PUT/PATCH aligned resume → GET PDF
  6. Persist sidecar JSON (flags for Apply Engine)
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import urllib.error
import urllib.request

# Local post-align helper (same scripts dir)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jd_strong_emphasis_align import (  # noqa: E402
    quality_gate,
    sample_diffs,
    strong_emphasis_align,
)

API = "https://rxresu.me/api/openapi"
MASTER = os.environ.get("RXRESU_MASTER_RESUME_ID", "YOUR_MASTER_RESUME_ID")
KEY_PATH = os.environ.get("RXRESU_API_KEY_PATH", os.path.expanduser("~/.config/rxresu_api_key"))
MASTER_PDF_FALLBACK = os.environ.get("HIREMESH_MASTER_PDF", "config/master_resume.pdf")
RETRY_LOG = str(Path(os.environ.get("HIREMESH_HOME", ".")).resolve() / "status" / "TAILOR_FALLBACK_RETRY.jsonl")


def api_key() -> str:
    return open(KEY_PATH).read().strip()


def req(method: str, path: str, payload=None, raw=False, timeout=120):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"x-api-key": api_key()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = resp.read()
            if raw:
                return resp.status, body
            text = body.decode()
            try:
                return resp.status, json.loads(text)
            except Exception:
                return resp.status, text
    except urllib.error.HTTPError as e:
        err = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} {path}: {err[:500]}") from e


def slugify(s: str) -> str:
    import re

    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s[:60] or "role"


def download_master_pdf(dest: str) -> tuple[str, int, str]:
    """Export Max-ATS master PDF (API preferred, local file fallback)."""
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    try:
        _, pdf = req("GET", f"/resumes/{MASTER}/pdf", raw=True, timeout=120)
        if pdf.startswith(b"%PDF"):
            open(dest, "wb").write(pdf)
            return dest, len(pdf), "api"
    except Exception as e:
        api_err = str(e)
    else:
        api_err = "non-PDF response"
    if os.path.isfile(MASTER_PDF_FALLBACK):
        shutil.copyfile(MASTER_PDF_FALLBACK, dest)
        return dest, os.path.getsize(dest), f"local_copy:{api_err}"
    raise RuntimeError(f"Max-ATS PDF unavailable (api={api_err})")


def log_fallback(entry: dict) -> None:
    try:
        os.makedirs(os.path.dirname(RETRY_LOG), exist_ok=True)
        with open(RETRY_LOG, "a") as f:
            f.write(json.dumps({**entry, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}) + "\n")
    except Exception as e:
        print(f"warn: retry log failed: {e}", file=sys.stderr)


def persist_resume_data(resume_id: str, resume_doc: dict, aligned_data: dict, display_name: str | None = None) -> bool:
    last = None
    # Prefer patching data (+ optional display name); fall back to full doc merge
    base = {"data": aligned_data}
    if display_name:
        base["name"] = display_name
    payloads = [base]
    if isinstance(resume_doc, dict):
        merged = {**resume_doc, "data": aligned_data}
        if display_name:
            merged["name"] = display_name
        payloads.append(merged)
    for payload in payloads:
        for method in ("PATCH", "PUT"):
            try:
                req(method, f"/resumes/{resume_id}", payload, timeout=60)
                return True
            except Exception as e:
                last = e
    print(f"warn: resume persist failed: {last}", file=sys.stderr)
    return False


def fetch_master_data() -> dict:
    _, resume = req("GET", f"/resumes/{MASTER}", timeout=60)
    if not isinstance(resume, dict):
        raise RuntimeError("master resume fetch failed")
    data = resume.get("data")
    if not isinstance(data, dict):
        raise RuntimeError("master resume missing data")
    return data


def write_sidecar(out_pdf: str, meta: dict) -> str:
    path = out_pdf.rsplit(".", 1)[0] + ".json"
    open(path, "w").write(json.dumps(meta, indent=2))
    return path


def base_meta(
    *,
    app_id,
    company,
    role,
    url,
    out_pdf,
    pdf_bytes,
    tailored_id=None,
    **flags,
) -> dict:
    meta = {
        "applicationId": app_id,
        "tailoredResumeId": tailored_id,
        "masterResumeId": MASTER,
        "pdf": out_pdf,
        "company": company,
        "role": role,
        "url": url,
        "bytes": pdf_bytes,
        # legacy + new flags (Apply Engine reads these)
        "experienceAligned": bool(flags.get("experienceAligned", False)),
        "tailored": bool(flags.get("tailored", False)),
        "tailorShallow": bool(flags.get("tailorShallow", False)),
        "aiDown": bool(flags.get("aiDown", False)),
        "fallbackUsed": bool(flags.get("fallbackUsed", False)),
        "qualityGate": flags.get("qualityGate"),
        "alignFlags": flags.get("alignFlags"),
        "aiError": flags.get("aiError"),
        "diffs": flags.get("diffs"),
        "depth": "strong_emphasis",
        "headlineMode": "retarget_headline",
        "fallbackMode": "fallback_and_flag",
    }
    return meta


def fallback_max_ats(
    *,
    app_id,
    company,
    role,
    url,
    out_pdf,
    tags,
    ai_down: bool,
    tailor_shallow: bool,
    ai_error: str | None,
    quality: dict | None = None,
    align_flags: dict | None = None,
    diffs=None,
    tailored_id=None,
) -> dict:
    path, nbytes, src = download_master_pdf(out_pdf)
    meta = base_meta(
        app_id=app_id,
        company=company,
        role=role,
        url=url,
        out_pdf=path,
        pdf_bytes=nbytes,
        tailored_id=tailored_id,
        experienceAligned=False,
        tailored=False,
        tailorShallow=tailor_shallow,
        aiDown=ai_down,
        fallbackUsed=True,
        qualityGate=quality,
        alignFlags=align_flags,
        aiError=ai_error,
        diffs=diffs,
    )
    meta["fallbackSource"] = src
    write_sidecar(out_pdf, meta)
    log_fallback(
        {
            "company": company,
            "role": role,
            "url": url,
            "applicationId": app_id,
            "aiDown": ai_down,
            "tailorShallow": tailor_shallow,
            "aiError": ai_error,
            "pdf": path,
        }
    )
    # Annotate application notes when possible
    note = (
        f"FALLBACK Max-ATS (aiDown={ai_down} tailorShallow={tailor_shallow}); "
        f"retry tailor later. PDF {path}"
    )
    try:
        req(
            "PUT",
            f"/applications/{app_id}",
            {
                "resumeId": MASTER,
                "notes": note,
                "tags": list(dict.fromkeys(tags + ["max-ats-fallback", "tailor-retry"])),
            },
        )
    except Exception:
        pass
    return meta


def tailor(
    company: str,
    role: str,
    jd: str,
    url: str | None,
    location: str,
    source: str,
    tags: list[str],
    out_pdf: str,
):
    jd_for_ai = (
        jd[:45000]
        + "\n\n---\nTAILORING INSTRUCTION (strong_emphasis): Rewrite SUMMARY, retarget "
        + "HEADLINE to the target role, reorder/rephrase EXPERIENCE bullets (HTML "
        + "description list items), and reorder SKILLS toward JD keywords. Keep "
        + "employers, titles, dates, and metrics truthful — remap emphasis only. "
        + "Prefer JD keywords that match real background (Cloud, Platform, SRE, "
        + "DevOps, DevSecOps, AIOps, MLOps, LLMOps, multi-cloud, Kubernetes, Terraform).\n"
    )
    _, app = req(
        "POST",
        "/applications",
        {
            "company": company,
            "role": role,
            "location": location,
            "source": source,
            "sourceUrl": url or "",
            "status": "saved",
            "resumeId": MASTER,
            "jobDescription": jd_for_ai,
            "tags": tags,
            "notes": "JD-tailor pipeline (strong_emphasis): awaiting apply",
        },
    )
    app_id = app if isinstance(app, str) else (app.get("id") if isinstance(app, dict) else None)
    if not app_id:
        raise RuntimeError(f"no application id: {app!r}")

    # --- AI tailor with retries ---
    tailored_id = None
    last_err = None
    ai_down = False
    for attempt in range(1, 4):
        try:
            _, tailored = req(
                "POST",
                f"/applications/{app_id}/ai/tailor-resume",
                {"resumeId": MASTER},
                timeout=180,
            )
            tailored_id = tailored.get("resumeId") if isinstance(tailored, dict) else None
            if tailored_id:
                break
            last_err = f"unexpected tailor payload: {tailored!r}"
        except Exception as e:
            last_err = str(e)
            if "502" in last_err or "BAD_GATEWAY" in last_err or "timeout" in last_err.lower():
                ai_down = True
            time.sleep(2 * attempt)

    if not tailored_id:
        ai_down = True
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=True,
            tailor_shallow=False,
            ai_error=last_err,
        )

    # --- Fetch clone + master; post-align ---
    try:
        _, resume_doc = req("GET", f"/resumes/{tailored_id}", timeout=60)
    except Exception as e:
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error=f"GET tailored failed: {e}",
            tailored_id=tailored_id,
        )

    if not isinstance(resume_doc, dict):
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error="tailored resume not a dict",
            tailored_id=tailored_id,
        )

    clone_data = resume_doc.get("data") if isinstance(resume_doc.get("data"), dict) else None
    if not isinstance(clone_data, dict):
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error="tailored resume missing data",
            tailored_id=tailored_id,
        )

    try:
        master_data = fetch_master_data()
    except Exception as e:
        # Still try aligning against the clone-as-baseline is wrong; use clone pre-align snapshot
        master_data = json.loads(json.dumps(clone_data))
        print(f"warn: master fetch failed, gate vs pre-align clone: {e}", file=sys.stderr)

    # Snapshot AI-only clone before local align (for gate: must differ from *master*)
    aligned, align_flags = strong_emphasis_align(clone_data, jd, role)
    gate = quality_gate(master_data, aligned)
    diffs = sample_diffs(master_data, aligned)

    if not gate["passed"]:
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error=None,
            quality=gate,
            align_flags=align_flags,
            diffs=diffs,
            tailored_id=tailored_id,
        )

    # Persist aligned data onto the tailored resume clone (+ display name)
    display_name = f"{role} — {os.environ.get('CANDIDATE_NAME', 'Candidate')}"[:120] if role else None
    persisted = persist_resume_data(tailored_id, resume_doc, aligned, display_name=display_name)
    if not persisted:
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error="persist aligned resume failed",
            quality=gate,
            align_flags=align_flags,
            diffs=diffs,
            tailored_id=tailored_id,
        )

    os.makedirs(os.path.dirname(out_pdf) or ".", exist_ok=True)
    try:
        _, pdf = req("GET", f"/resumes/{tailored_id}/pdf", raw=True, timeout=120)
    except Exception as e:
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error=f"PDF export failed: {e}",
            quality=gate,
            align_flags=align_flags,
            diffs=diffs,
            tailored_id=tailored_id,
        )
    if not pdf.startswith(b"%PDF"):
        return fallback_max_ats(
            app_id=app_id,
            company=company,
            role=role,
            url=url,
            out_pdf=out_pdf,
            tags=tags,
            ai_down=False,
            tailor_shallow=True,
            ai_error="download did not return a PDF",
            quality=gate,
            align_flags=align_flags,
            diffs=diffs,
            tailored_id=tailored_id,
        )
    open(out_pdf, "wb").write(pdf)

    try:
        req(
            "PUT",
            f"/applications/{app_id}",
            {
                "resumeId": tailored_id,
                "notes": (
                    f"JD-tailored strong_emphasis experienceAligned=yes; "
                    f"resume {tailored_id}; PDF {out_pdf}"
                ),
                "tags": list(
                    dict.fromkeys(tags + ["jd-tailored", "experience-aligned", "strong-emphasis"])
                ),
            },
        )
    except Exception:
        pass

    meta = base_meta(
        app_id=app_id,
        company=company,
        role=role,
        url=url,
        out_pdf=out_pdf,
        pdf_bytes=len(pdf),
        tailored_id=tailored_id,
        experienceAligned=True,
        tailored=True,
        tailorShallow=False,
        aiDown=False,
        fallbackUsed=False,
        qualityGate=gate,
        alignFlags=align_flags,
        diffs=diffs,
    )
    write_sidecar(out_pdf, meta)
    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--url", default="")
    p.add_argument("--location", default="UAE")
    p.add_argument("--source", default="ATS")
    p.add_argument("--jd", default="")
    p.add_argument("--jd-file", default="")
    p.add_argument("--out", default="")
    p.add_argument("--tags", default="jd-tailored")
    args = p.parse_args()
    jd = args.jd
    if args.jd_file:
        jd = open(args.jd_file).read()
    if not jd.strip():
        print("JD text required (--jd or --jd-file)", file=sys.stderr)
        sys.exit(2)
    out = args.out or str(
        Path(os.environ.get("HIREMESH_HOME", ".")).resolve()
        / "tailored"
        / f"{slugify(args.company)}-{slugify(args.role)}.pdf"
    )
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    meta = tailor(
        args.company,
        args.role,
        jd,
        args.url or None,
        args.location,
        args.source,
        tags,
        out,
    )
    print(json.dumps(meta, indent=2))
    # Non-zero only on hard failure (no usable PDF). Fallback still exits 0.
    if not meta.get("pdf") or not os.path.isfile(meta["pdf"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
