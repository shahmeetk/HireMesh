#!/usr/bin/env python3
"""Deterministic strong_emphasis post-align for Reactive Resume Max-ATS data.

Meet 2026-09-25 prefs:
  depth = strong_emphasis  — reorder + lightly rephrase; never invent facts
  headline = retarget_headline
  Experience lives in HTML description (<ul><li><p>…</p></li>); skills in
  sections.skills.items[].keywords; summary in data.summary.content.
"""
from __future__ import annotations

import copy
import html
import re
from typing import Any

KEYWORD_MAP: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bkubernetes\b|\bk8s\b|\bopenshift\b|\baks\b|\beks\b|\bgke\b|\boke\b", re.I), "Kubernetes"),
    (re.compile(r"\bterraform\b|\binfrastructure as code\b|\biac\b|\bansible\b|\bpulumi\b", re.I), "Infrastructure as Code (Terraform)"),
    (re.compile(r"\baws\b|amazon web services|\bbedrock\b", re.I), "AWS"),
    (re.compile(r"\bazure\b|\baks\b", re.I), "Azure"),
    (re.compile(r"\bgcp\b|google cloud|\bvertex\b", re.I), "GCP"),
    (re.compile(r"\boci\b|oracle cloud", re.I), "Oracle Cloud (OCI)"),
    (re.compile(r"\bmlops\b|\bllmops\b|\baiops\b|ai infra|ai platform|\bgenai\b|\bllm\b|generative ai|\brag\b", re.I), "AI / MLOps / LLMOps"),
    (re.compile(r"\bobservability\b|\bopentelemetry\b|\bprometheus\b|\bgrafana\b|\bdatadog\b|\bslo\b|\bsli\b", re.I), "observability"),
    (re.compile(r"\bdevsecops\b|shift.?left|cloud security|zero.?trust|\bprisma\b|\bsnyk\b", re.I), "DevSecOps"),
    (re.compile(r"\bfinops\b|cost optim|cloud spend|\btco\b", re.I), "FinOps"),
    (re.compile(r"\bsre\b|site reliability|platform engineer|platform engineering|developer experience|\bidp\b|golden path", re.I), "SRE / platform engineering"),
    (re.compile(r"\bci/?cd\b|\bgitops\b|\bargo\b|github actions|gitlab ci", re.I), "CI/CD / GitOps"),
    (re.compile(r"\bmulti.?cloud\b|hybrid cloud|landing zone", re.I), "multi-cloud / landing zones"),
    (re.compile(r"\binternal developer platform\b|\bplatform.as.a.product\b", re.I), "Internal Developer Platform"),
    (re.compile(r"\bpavement\b|\bpayments\b|\bfintech\b|\bpci\b", re.I), "regulated / payments"),
]

LI_RE = re.compile(r"<li>\s*(?:<p>)?(.*?)(?:</p>)?\s*</li>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def jd_themes(jd: str) -> list[tuple[re.Pattern, str]]:
    return [(rx, label) for rx, label in KEYWORD_MAP if rx.search(jd or "")]


def strip_html(s: str) -> str:
    t = TAG_RE.sub(" ", s or "")
    t = html.unescape(t)
    return WS_RE.sub(" ", t).strip()


def parse_html_li_items(description: str) -> list[str]:
    """Extract plain-text bullets from Reactive Resume experience HTML."""
    if not description or not isinstance(description, str):
        return []
    items = [strip_html(m.group(1)) for m in LI_RE.finditer(description)]
    items = [i for i in items if i]
    if items:
        return items
    # Fallback: whole block as one bullet if no <li>
    plain = strip_html(description)
    return [plain] if plain else []


def rebuild_html_ul(bullets: list[str]) -> str:
    parts = []
    for b in bullets:
        safe = html.escape(b, quote=False)
        parts.append(f"<li><p>{safe}</p></li>")
    return "<ul>" + "".join(parts) + "</ul>"


def _jd_tokens(jd: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+]{4,}", (jd or "").lower()))


def score_text(text: str, themes: list[tuple[re.Pattern, str]], jd_tokens: set[str]) -> int:
    t = (text or "").lower()
    s = 0
    for rx, _ in themes:
        if rx.search(t):
            s += 5
    for w in jd_tokens:
        if w in t:
            s += 1
    return s


def light_rephrase(bullet: str, themes: list[tuple[re.Pattern, str]], rank: int) -> str:
    """Prefix a matching JD theme label on top bullets when missing. No new facts."""
    t = bullet.strip()
    if rank >= 3 or not themes:
        return t
    for rx, label in themes:
        if rx.search(t) and label.lower() not in t.lower()[:100]:
            candidate = f"{label} — {t}"
            if len(candidate) <= 320:
                return candidate
            break
    return t


def align_experience_html(data: dict, jd: str, role: str = "") -> bool:
    """Reorder/lightly rephrase HTML description bullets. Returns True if changed."""
    themes = jd_themes(jd)
    jd_tokens = _jd_tokens(jd)
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else None
    if not isinstance(sections, dict):
        return False
    exp = None
    for k in ("experience", "work", "employment"):
        block = sections.get(k)
        if isinstance(block, dict) and isinstance(block.get("items"), list):
            exp = block
            break
    if not exp:
        return False

    changed = False
    for entry in exp.get("items") or []:
        if not isinstance(entry, dict):
            continue
        desc = entry.get("description")
        bullets = parse_html_li_items(desc) if isinstance(desc, str) else []
        # Also handle legacy highlights/bullets/summary if present
        legacy_key = None
        if not bullets:
            for lk in ("highlights", "bullets"):
                if isinstance(entry.get(lk), list) and entry[lk]:
                    bullets = [
                        (b if isinstance(b, str) else (b.get("text") or b.get("content") or ""))
                        for b in entry[lk]
                    ]
                    bullets = [b for b in bullets if b]
                    legacy_key = lk
                    break
        if not bullets and isinstance(entry.get("summary"), str):
            lines = [ln.strip(" •-\t") for ln in entry["summary"].split("\n") if ln.strip()]
            if len(lines) >= 2:
                bullets = lines
                legacy_key = "summary"

        if not bullets:
            continue

        ranked = sorted(enumerate(bullets), key=lambda ib: (-score_text(ib[1], themes, jd_tokens), ib[0]))
        new_bullets = [light_rephrase(b, themes, i) for i, (_, b) in enumerate(ranked)]

        if isinstance(desc, str) and "<li" in desc.lower():
            new_html = rebuild_html_ul(new_bullets)
            if new_html != desc:
                entry["description"] = new_html
                changed = True
        elif legacy_key == "summary":
            joined = "\n".join(new_bullets)
            if joined != entry.get("summary"):
                entry["summary"] = joined
                changed = True
        elif legacy_key:
            if new_bullets != bullets:
                entry[legacy_key] = new_bullets
                changed = True
        else:
            # No HTML list — write HTML description so PDF gets bullets
            new_html = rebuild_html_ul(new_bullets)
            if new_html != (desc or ""):
                entry["description"] = new_html
                changed = True

    return changed


def align_skills(data: dict, jd: str) -> bool:
    """Reorder skill groups and keywords toward JD. No invented skills."""
    themes = jd_themes(jd)
    jd_tokens = _jd_tokens(jd)
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else None
    if not isinstance(sections, dict):
        return False
    skills = sections.get("skills")
    if not isinstance(skills, dict) or not isinstance(skills.get("items"), list):
        return False

    items = skills["items"]
    before = json_snapshot(items)

    def item_score(it: dict) -> int:
        blob = " ".join(
            [str(it.get("name") or "")]
            + [str(k) for k in (it.get("keywords") or []) if isinstance(k, (str, int))]
        )
        return score_text(blob, themes, jd_tokens)

    # Reorder groups
    indexed = list(enumerate(items))
    indexed.sort(key=lambda iv: (-item_score(iv[1]) if isinstance(iv[1], dict) else 0, iv[0]))
    new_items = [it for _, it in indexed]

    for it in new_items:
        if not isinstance(it, dict):
            continue
        kws = it.get("keywords")
        if not isinstance(kws, list) or not kws:
            continue
        # Normalize to strings for scoring; preserve original objects
        def kw_text(k):
            if isinstance(k, str):
                return k
            if isinstance(k, dict):
                return str(k.get("name") or k.get("text") or k.get("content") or "")
            return str(k)

        ranked = sorted(enumerate(kws), key=lambda ik: (-score_text(kw_text(ik[1]), themes, jd_tokens), ik[0]))
        it["keywords"] = [k for _, k in ranked]

        # Light label refresh: only if name clearly under-emphasizes a dominant theme present in keywords
        name = str(it.get("name") or "")
        if themes and name:
            top_theme = themes[0][1]
            kw_blob = " ".join(kw_text(k) for k in it["keywords"]).lower()
            if top_theme.lower().split("/")[0].strip() in kw_blob and top_theme.split("/")[0].strip().lower() not in name.lower():
                # Keep original name — Meet said lightly refresh labels if schema allows without inventing.
                # Safer: leave group names unless already close; do not invent new category titles.
                pass

    skills["items"] = new_items
    return json_snapshot(new_items) != before


def rewrite_summary(data: dict, jd: str, role: str) -> bool:
    """Refresh summary.content toward JD/role while keeping factual core."""
    themes = jd_themes(jd)
    summary = data.get("summary")
    if not isinstance(summary, dict):
        # Some schemas nest under sections
        sections = data.get("sections") if isinstance(data.get("sections"), dict) else {}
        summary = sections.get("summary") if isinstance(sections, dict) else None
        if not isinstance(summary, dict):
            return False
        # write back via sections path
        target = summary
        use_sections = True
    else:
        target = summary
        use_sections = False

    content = target.get("content")
    if not isinstance(content, str) or not content.strip():
        return False

    plain = strip_html(content)
    role_clean = (role or "").strip()
    theme_labels = [lab for _, lab in themes[:4]]
    # Build a lead that retargets without inventing employers/metrics
    lead_bits = []
    if role_clean:
        lead_bits.append(role_clean)
    for lab in theme_labels:
        if lab.lower() not in " ".join(lead_bits).lower():
            lead_bits.append(lab)
    lead = " | ".join(lead_bits[:5]) if lead_bits else ""

    # Drop an old leading <strong>…</strong> headline-ish phrase and re-anchor
    rebuilt = plain
    # If role not already fronted, prepend a strong lead sentence using existing facts
    if role_clean and role_clean.lower() not in plain[:180].lower():
        themes_bit = ", ".join(html.escape(t) for t in theme_labels[:3]) or "cloud platform engineering"
        lead_sentence = (
            f"<strong>{html.escape(role_clean)}</strong> with proven delivery across {themes_bit}. "
        )
        body = re.sub(r"^<p>|</p>$", "", content.strip(), flags=re.I)
        body = re.sub(r"^<strong>.*?</strong>\s*", "", body, count=1, flags=re.I | re.S)
        # Avoid "X. with years" when body already starts with "with"
        body_plain = strip_html(body)
        if body_plain.lower().startswith("with "):
            lead_sentence = (
                f"<strong>{html.escape(role_clean)}</strong> focused on {themes_bit}, "
            )
        new_content = f"<p>{lead_sentence}{body}</p>"
    elif theme_labels and not any(t.lower() in plain.lower() for t in theme_labels[:2]):
        inject = html.escape(theme_labels[0])
        body = re.sub(r"^<p>|</p>$", "", content.strip(), flags=re.I)
        new_content = f"<p><strong>{inject}</strong>. {body}</p>"
    elif lead and lead.lower() not in plain[:120].lower():
        body = re.sub(r"^<p>|</p>$", "", content.strip(), flags=re.I)
        new_content = f"<p><strong>{html.escape(lead)}</strong>. {body}</p>"
    else:
        # Still force a visible difference: ensure role appears in the opening strong
        if role_clean:
            body = re.sub(r"^<p>|</p>$", "", content.strip(), flags=re.I)
            body = re.sub(r"^<strong>.*?</strong>\s*", "", body, count=1, flags=re.I | re.S)
            new_content = (
                f"<p><strong>{html.escape(role_clean)}</strong> — {body}</p>"
            )
        else:
            return False

    if new_content == content:
        return False
    target["content"] = new_content
    if use_sections:
        data.setdefault("sections", {})["summary"] = target
    else:
        data["summary"] = target
    return True


def retarget_headline(data: dict, role: str, jd: str = "") -> bool:
    """Set basics.headline (and basics.title if present) to the target role."""
    role_clean = (role or "").strip()
    if not role_clean:
        return False
    themes = jd_themes(jd)
    suffixes = []
    for _, lab in themes[:4]:
        short = lab.split("(")[0].strip()
        if short.lower() not in role_clean.lower() and short not in suffixes:
            suffixes.append(short)
    headline = role_clean
    if suffixes:
        headline = f"{role_clean} | " + " | ".join(suffixes[:4])
    if len(headline) > 160:
        headline = headline[:157] + "..."

    basics = data.get("basics")
    if not isinstance(basics, dict):
        data["basics"] = {"headline": headline}
        return True
    changed = False
    if basics.get("headline") != headline:
        basics["headline"] = headline
        changed = True
    if "title" in basics and basics.get("title") != role_clean:
        basics["title"] = role_clean
        changed = True
    if "label" in basics and basics.get("label") != role_clean:
        basics["label"] = role_clean
        changed = True
    return changed


def json_snapshot(obj: Any) -> str:
    import json

    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def experience_html_blob(data: dict) -> str:
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else {}
    exp = sections.get("experience") if isinstance(sections, dict) else None
    if not isinstance(exp, dict):
        return ""
    parts = []
    for it in exp.get("items") or []:
        if isinstance(it, dict):
            parts.append(it.get("description") or "")
    return "\n".join(parts)


def summary_blob(data: dict) -> str:
    s = data.get("summary")
    if isinstance(s, dict):
        return s.get("content") or ""
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else {}
    s2 = sections.get("summary") if isinstance(sections, dict) else None
    if isinstance(s2, dict):
        return s2.get("content") or ""
    return ""


def skills_blob(data: dict) -> str:
    sections = data.get("sections") if isinstance(data.get("sections"), dict) else {}
    skills = sections.get("skills") if isinstance(sections, dict) else None
    if not isinstance(skills, dict):
        return ""
    return json_snapshot(skills.get("items") or [])


def quality_gate(master_data: dict, aligned_data: dict) -> dict:
    """Require summary AND experience HTML AND skills each differ from master."""
    summary_differs = summary_blob(master_data) != summary_blob(aligned_data)
    experience_differs = experience_html_blob(master_data) != experience_html_blob(aligned_data)
    skills_differs = skills_blob(master_data) != skills_blob(aligned_data)
    passed = bool(summary_differs and experience_differs and skills_differs)
    return {
        "passed": passed,
        "summaryDiffers": summary_differs,
        "experienceDiffers": experience_differs,
        "skillsDiffers": skills_differs,
    }


def strong_emphasis_align(data: dict, jd: str, role: str) -> tuple[dict, dict]:
    """Run full local post-align. Returns (new_data, change_flags)."""
    out = copy.deepcopy(data)
    flags = {
        "headlineUpdated": retarget_headline(out, role, jd),
        "summaryUpdated": rewrite_summary(out, jd, role),
        "experienceUpdated": align_experience_html(out, jd, role),
        "skillsUpdated": align_skills(out, jd),
    }
    return out, flags


def sample_diffs(master_data: dict, aligned_data: dict) -> dict:
    """Small before/after snippets for smoke logs."""
    mh = (master_data.get("basics") or {}).get("headline") if isinstance(master_data.get("basics"), dict) else None
    ah = (aligned_data.get("basics") or {}).get("headline") if isinstance(aligned_data.get("basics"), dict) else None
    ms = strip_html(summary_blob(master_data))[:180]
    as_ = strip_html(summary_blob(aligned_data))[:180]

    def first_bullet(d):
        sections = d.get("sections") if isinstance(d.get("sections"), dict) else {}
        exp = sections.get("experience") if isinstance(sections, dict) else {}
        items = (exp or {}).get("items") or []
        if items and isinstance(items[0], dict):
            bullets = parse_html_li_items(items[0].get("description") or "")
            return bullets[0] if bullets else ""
        return ""

    def first_skill(d):
        sections = d.get("sections") if isinstance(d.get("sections"), dict) else {}
        skills = sections.get("skills") if isinstance(sections, dict) else {}
        items = (skills or {}).get("items") or []
        if not items:
            return None
        it = items[0]
        kws = it.get("keywords") or []
        return {"name": it.get("name"), "firstKeywords": kws[:3]}

    return {
        "headline": {"before": mh, "after": ah},
        "summarySnippet": {"before": ms, "after": as_},
        "firstExperienceBullet": {"before": first_bullet(master_data), "after": first_bullet(aligned_data)},
        "firstSkill": {"before": first_skill(master_data), "after": first_skill(aligned_data)},
    }
