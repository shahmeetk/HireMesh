#!/usr/bin/env python3
"""Create a JD-specific cover letter PDF via Reactive Resume.

Uses Generic Cover Letter resume as template:
  1. Duplicate resume YOUR_COVER_TEMPLATE_ID
  2. PUT tailored HTML summary content
  3. GET PDF
Also creates/updates an RPC coverLetters entry linked to applicationId when provided.
"""
from __future__ import annotations

import os
import argparse, json, os, re, sys, urllib.request, urllib.error

API = "https://rxresu.me/api/openapi"
RPC = "https://rxresu.me/api/rpc"
KEY_PATH = os.environ.get("RXRESU_API_KEY_PATH", os.path.expanduser("~/.config/rxresu_api_key"))
COVER_TEMPLATE = os.environ.get("RXRESU_COVER_TEMPLATE_ID", "YOUR_COVER_TEMPLATE_ID")


def key():
    return open(KEY_PATH).read().strip()


def openapi(method, path, payload=None, raw=False, timeout=90):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"x-api-key": key()}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        return body if raw else body.decode()


def rpc(path, payload, timeout=90):
    data = json.dumps({"json": payload}).encode()
    req = urllib.request.Request(
        RPC + path, data=data, method="POST",
        headers={"x-api-key": key(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode()).get("json")


def slugify(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")[:50] or "role"


def letter_html(company: str, role: str, jd: str) -> str:
    jd_l = jd.lower()
    highlights = []
    for needle, line in [
        ("kubernetes", "Kubernetes / container platform leadership"),
        ("terraform", "Terraform / IaC at scale"),
        ("llm", "LLMOps / GenAI platform delivery"),
        ("aiops", "AIOps and observability"),
        ("finops", "FinOps and cloud TCO reduction (~43% at NI)"),
        ("security", "DevSecOps / zero-trust CI/CD / PCI-DSS"),
        ("architect", "solution & cloud architecture ownership"),
        ("platform", "multi-cloud platform engineering (Azure/AWS/OCI/GCP)"),
    ]:
        if needle in jd_l:
            highlights.append(line)
    if not highlights:
        highlights = [
            "multi-cloud platform engineering (Azure/AWS/OCI/GCP)",
            "DevSecOps, AIOps and LLMOps in regulated fintech",
            "architecture leadership with measurable delivery outcomes",
        ]
    bullets = "".join(f"<li>{h}</li>" for h in highlights[:5])
    return (
        f"<p>Dear Hiring Manager,</p>"
        f"<p>I am applying for the <strong>{role}</strong> role at <strong>{company}</strong>. "
        f"As AVP Cloud Platform &amp; AI Engineering (Head of Cloud &amp; AI Engineering) in Dubai, "
        f"I lead secure multi-cloud platforms and AI infrastructure for regulated payments at Network International.</p>"
        f"<p>Closest fit to this JD:</p><ul>{bullets}</ul>"
        f"<p>Recent outcomes include ~43% cloud TCO reduction, faster delivery on a 55+ microservice platform, "
        f"and sustained compliance controls. I am UAE work-authorized (no sponsorship) and open to UAE or fully remote roles.</p>"
        f"<p>I would welcome a conversation about how I can help {company}.</p>"
        f"<p>Best regards,<br/>{os.environ.get('CANDIDATE_NAME','Candidate')}<br/>{os.environ.get('CANDIDATE_EMAIL','candidate@example.com')} | {os.environ.get('CANDIDATE_PHONE','+1-555-0100')} | {os.environ.get('CANDIDATE_LINKEDIN','linkedin.com/in/candidate')}</p>"
    )


def letter_text(company: str, role: str, jd: str) -> str:
    # plain text twin of HTML
    import re as _re
    t = letter_html(company, role, jd)
    t = _re.sub(r"<li>", "- ", t)
    t = _re.sub(r"</li>", "\n", t)
    t = _re.sub(r"<br\s*/?>", "\n", t)
    t = _re.sub(r"</p>", "\n\n", t)
    t = _re.sub(r"<[^>]+>", "", t)
    return _re.sub(r"\n{3,}", "\n\n", t).strip()


def create(company, role, jd, url, out_pdf, application_id=None):
    html = letter_html(company, role, jd)
    text = letter_text(company, role, jd)
    slug = f"cover-{slugify(company)}-{slugify(role)}"
    name = f"Cover — {company} · {role}"[:80]
    # duplicate template
    new_id = json.loads(openapi("POST", f"/resumes/{COVER_TEMPLATE}/duplicate", {
        "name": name, "slug": slug, "tags": ["cover-letter", "jd-tailored"]
    }))
    doc = json.loads(openapi("GET", f"/resumes/{new_id}"))
    doc["data"]["summary"]["content"] = html
    openapi("PUT", f"/resumes/{new_id}", {
        "name": name, "slug": slug, "tags": ["cover-letter", "jd-tailored"], "data": doc["data"]
    })
    os.makedirs(os.path.dirname(out_pdf) or ".", exist_ok=True)
    pdf = openapi("GET", f"/resumes/{new_id}/pdf", raw=True)
    if not pdf.startswith(b"%PDF"):
        raise RuntimeError("cover letter PDF download failed")
    open(out_pdf, "wb").write(pdf)

    cl_id = None
    try:
        created = rpc("/coverLetters/create", {
            "name": name,
            "company": company,
            "role": role,
            "resumeId": "YOUR_MASTER_RESUME_ID",
            "applicationId": application_id,
            "jobDescription": jd[:20000],
            "sourceUrl": url or "",
        })
        # created may be full object without easy id in truncated form — list and match
        items = rpc("/coverLetters/list", {}).get("items", [])
        for it in items:
            if it.get("name") == name:
                cl_id = it.get("id")
                rev = it.get("revision", 1)
                rpc("/coverLetters/update", {
                    "id": cl_id,
                    "expectedRevision": rev,
                    "name": name,
                    "recipient": "Hiring Manager",
                    "content": text,
                })
                break
    except Exception as e:
        cl_id = f"error:{e}"

    meta = {
        "coverResumeId": new_id,
        "coverLetterId": cl_id,
        "pdf": out_pdf,
        "company": company,
        "role": role,
        "bytes": len(pdf),
    }
    open(out_pdf.rsplit(".", 1)[0] + ".json", "w").write(json.dumps(meta, indent=2))
    return meta


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--company", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--url", default="")
    p.add_argument("--jd", default="")
    p.add_argument("--jd-file", default="")
    p.add_argument("--out", required=True)
    p.add_argument("--application-id", default="")
    args = p.parse_args()
    jd = args.jd or (open(args.jd_file).read() if args.jd_file else "")
    if not jd.strip():
        print("JD required", file=sys.stderr); sys.exit(2)
    meta = create(args.company, args.role, jd, args.url, args.out, args.application_id or None)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
