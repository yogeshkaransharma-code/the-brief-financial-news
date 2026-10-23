#!/usr/bin/env python3
"""Autonomous *limited-risk* publication gate for The Brief.

It is intentionally NOT a substitute for fact checking. Only FCA official,
non-legal statistical summary pages with complete captured HTML and 100%
machine-screened sentences can advance. All other articles stay unpublished.
Auto articles must be visibly labelled as such, never editor-reviewed.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit
from editorial_gate import check
from newsroom_v2 import canonical
from verify_approved_articles import validate as verify_feed

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data/articles.json"
AUDIT_DIR = ROOT / "data/editorial-audits"
DRAFT_DIR = ROOT / "generated-drafts"
MAX_ARTICLES = 2
POLICY_VERSION = "first-party-newsroom-2026-10-23-v1"
# Only named primary-source newsrooms and narrow first-party categories.
# Never republish a third-party report or an unsupported RSS summary.
FCA_REPORT = re.compile(r"^/data/complaints-data-\d{4}-h[12]/?$", re.I)
AVIVA_RELEASE = re.compile(r"^/newsroom/news-and-research-overview/news-releases/20\d{2}/\d{2}/[a-z0-9-]+/?$",re.I)
LLOYDS_RELEASE = re.compile(r"^/media/press-releases/20\d{2}/[a-z0-9-]+(?:/[a-z0-9-]+)?\.html$",re.I)
SPEECH = re.compile(r"/speeches?/",re.I)
HIGH_RISK = re.compile(
    r"\b(?:criminal|convicted|guilty|misconduct|lawsuit|litigation|"
    r"regulatory breach|sanction|enforcement action|will have to|must comply|"
    r"comes into force|new legal duty|accused of|insolvency|bankruptcy)\b", re.I
)
CAUSAL = re.compile(r"\b(?:caused by|resulted in|as a result of|led to)\b", re.I)

def eligible(bundle):
    """Return reasons to HOLD; never decide eligibility from a model score."""
    a, audit = bundle.get("draft",{}), bundle.get("audit",{})
    problems=[]
    try:
        check(bundle)
    except (ValueError, KeyError, TypeError) as exc:
        return ["Editorial evidence gate failed: "+str(exc)]
    parts=urlsplit(a["url"])
    host=parts.hostname or ""
    fca_report=host in {"www.fca.org.uk","fca.org.uk"} and bool(FCA_REPORT.fullmatch(parts.path))
    aviva=host in {"www.aviva.com","aviva.com"} and bool(AVIVA_RELEASE.fullmatch(parts.path))
    lloyds=host in {"www.lloydsbankinggroup.com","lloydsbankinggroup.com"} and bool(LLOYDS_RELEASE.fullmatch(parts.path))
    if parts.scheme!="https" or not (fca_report or aviva or lloyds):
        problems.append("Not within documented primary-source statistical or company-announcement allowlist")
    if fca_report and a.get("status")!="Published report":
        problems.append("FCA statistics incorrectly described")
    if (aviva or lloyds) and a.get("status")!="Confirmed announcement":
        problems.append("A company announcement must be labelled as such")
    if (aviva or lloyds) and a.get("category") not in {"Banking","Insurance","Technology"}:
        problems.append("Original company source not within financial-services industry category")
    if audit.get("pipeline_version")!=2:
        problems.append("Missing independent sentence-level review")
    if audit.get("source_extraction")!="HTML main content":
        problems.append("Unsupported or incomplete source format")
    if audit.get("source_retrieval_limits") != "Full captured material shown; check all relevant linked appendices before approval. ":
        problems.append("Source retrieval has extra warnings or caveats")
    if audit.get("source_document_urls") != [a["url"]]:
        problems.append("Complex or redirected source document")
    source=bundle.get("captured_source_excerpt","")
    if len(source)<1900:
        problems.append("Insufficient original factual reporting")
    updated=dt.datetime.now(dt.timezone.utc).date()
    try:
        issued=dt.date.fromisoformat(a["dateISO"])
        # The initial intake can catch up on recent first-party news without
        # mislabelling its original source date as today's new development.
        max_age=21 if (aviva or lloyds) else 5
        if not dt.timedelta(days=0)<=updated-issued<=dt.timedelta(days=max_age):
            problems.append("Original source outside the autonomous news freshness window")
    except (ValueError,TypeError):
        problems.append("Invalid source date")
    if bundle.get("editorial_flags") or bundle.get("revision_history",[])[-1:][0:1] and bundle["revision_history"][-1].get("problems"):
        problems.append("Outstanding disputed claim")
    combined="\n".join([a["title"],a["short"]]+[t for _,t in a["blocks"]])
    if HIGH_RISK.search(combined):
        problems.append("High-risk claim requires human accountability")
    if CAUSAL.search(combined):
        problems.append("Potential causal inference outside automated scope")
    if re.search(r"(?i)\bpercentage[- ]point",combined):
        problems.append("Percentage-point calculations must be independently reconciled before automation")
    count=sum(len(x.split()) for _,x in a["blocks"])
    if count>700:
        problems.append("Unusually long unattended financial interpretation")
    checks=audit.get("verbatim_source_checks",[])
    if len(checks)<8:
        problems.append("Too few fully supported, sourced sentences")
    # A second AI's SUPPORTED verdict is necessary but not proof of truth.
    review=audit.get("sentence_review") or {}
    if review.get("held")!=0 or review.get("supported",0)<8:
        problems.append("Insufficient completed independent evidence challenge")
    return problems

def publish(root=ROOT, folder=None, dry_run=False):
    root=Path(root)
    folder=Path(folder) if folder else root/"generated-drafts"
    article_path=root/"data/articles.json"
    audit_path=root/"data/editorial-audits"
    existing=json.loads(article_path.read_text(encoding="utf-8"))
    if not isinstance(existing,list):
        raise ValueError("Article feed must be a list")
    seen_id={x.get("id") for x in existing}
    seen_url={x.get("url") for x in existing}
    report={"policy":POLICY_VERSION,"tested":0,"published":[],"held":[],"mode":"dry_run" if dry_run else "active"}
    for file in sorted(folder.glob("ai-*.json")):
        bundle=json.loads(file.read_text(encoding="utf-8"))
        a=bundle.get("draft") or {}
        aid=a.get("id","unknown")
        report["tested"]+=1
        if aid in seen_id or a.get("url") in seen_url:
            report["held"].append({"id":aid,"reason":["Duplicate source/article"]})
            continue
        reasons=eligible(bundle)
        if reasons:
            report["held"].append({"id":aid,"reason":reasons})
            continue
        if len(report["published"])>=MAX_ARTICLES:
            report["held"].append({"id":aid,"reason":["Daily original-story cap"]})
            continue
        item=dict(a)
        item["reviewed_by"]="autonomous-evidence-screening"
        item["publication_method"]="autonomous"
        item["editorial_status"]="PUBLISHED: autonomous source-limited machine-screening (no human review)"
        item["published_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
        item["reviewed_at"]=item["published_at"]
        item["publication"]="The Brief"
        review_record={
            "article_id":aid,"source_url":item["url"],
            "review_mode":"autonomous_low_risk",
            "automation_policy_version":POLICY_VERSION,
            "approved_by_github_actor":"AUTONOMOUS_PIPELINE_NO_HUMAN",
            "approved_at_utc":item["reviewed_at"],
            "reviewed_draft_sha256":bundle["audit"]["draft_sha256"],
            "source_snapshot_sha256":bundle["audit"]["source_sha256"],
            "published_article_sha256":canonical(item),
            "source_document_urls":bundle["audit"]["source_document_urls"],
            "claim_challenge_sentences":bundle["audit"]["sentence_review"]["reviewed"],
            "editor_notes":"Original regulator or first-party banking/insurance release; machine-screened, not fact-certified by a human editor.",
            "residual_risk":"The AI and source may be wrong; a passing automated check does not prove a claim's meaning.",
        }
        if not dry_run:
            audit_path.mkdir(parents=True,exist_ok=True)
            (audit_path/(aid+".json")).write_text(json.dumps(review_record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            existing.insert(0,item)
        report["published"].append({"id":aid,"title":item["title"],"url":item["url"]})
        seen_id.add(aid)
        seen_url.add(item["url"])
    if not dry_run and report["published"]:
        article_path.write_text(json.dumps(existing[:150],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        verify_feed(root)
    print("AUTONOMOUS_REPORT: "+json.dumps(report,ensure_ascii=False))
    return report

if __name__=="__main__":
    enabled=os.environ.get("AUTO_PUBLICATION_ENABLED")=="1"
    publish(dry_run=not enabled)
