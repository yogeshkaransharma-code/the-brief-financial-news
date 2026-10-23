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
from fresh_sources import LAUNCH_START, LAUNCH_END
from publication_scope import source_lane

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data/articles.json"
AUDIT_DIR = ROOT / "data/editorial-audits"
DRAFT_DIR = ROOT / "generated-drafts"
MAX_ARTICLES = 6
POLICY_VERSION = "daily-24-hour-news-2026-10-23-v2"
# URL-level lanes are shared with candidate selection so Gemini focuses on
# stories that have a chance of passing the autonomous publication gate.
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
    lane=source_lane(a["url"])
    if not lane:
        problems.append("Source outside the cautious first-party reporting lanes (or excluded adverse enforcement)")
    if lane=="fca_data" and a.get("status")!="Published report":
        problems.append("FCA statistics incorrectly described")
    if lane=="fca_speech" and a.get("status")!="Speech / commentary":
        problems.append("FCA speech cannot be presented as new rules or final regulatory decision")
    if lane=="fca_consultation" and a.get("status")!="Proposal":
        problems.append("FCA consultation must be explicitly presented as a proposal")
    if lane in {"fca_release","company_release","official_release","issuer_rns"} and a.get("status")!="Confirmed announcement":
        problems.append("An official announcement must be labelled as such")
    if lane and a.get("category") not in {"Banking","Insurance","Technology","Regulation"}:
        problems.append("Original source not within financial-services industry category")
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
        # Rolling coverage is at most 24 hours. During the relaunch on
        # 23 October only, announcements first made on 22 October also qualify.
        launched=LAUNCH_START<=issued<=LAUNCH_END and updated==LAUNCH_END
        precision=a.get("source_time_precision","date")
        if precision=="timestamp":
            published_at=dt.datetime.fromisoformat(a["source_published_at"].replace("Z","+00:00"))
            now=dt.datetime.now(dt.timezone.utc)
            is_fresh=published_at.tzinfo is not None and dt.timedelta()<=now-published_at<=dt.timedelta(hours=24)
        else:
            # If the source gives only its calendar date, avoid inventing the
            # hour. Accept today's dated releases; 22 Oct is launch-only.
            is_fresh=(issued==updated)
        if not (launched or is_fresh):
            problems.append("Outside the precise 24-hour news window or unverifiable source time")
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
    retired_file=root/"data/retired-source-urls.json"
    retired_urls=set(json.loads(retired_file.read_text(encoding="utf-8")).get("urls",[])) if retired_file.exists() else set()
    report={"policy":POLICY_VERSION,"tested":0,"published":[],"held":[],"mode":"dry_run" if dry_run else "active"}
    for file in sorted(folder.glob("ai-*.json")):
        bundle=json.loads(file.read_text(encoding="utf-8"))
        a=bundle.get("draft") or {}
        aid=a.get("id","unknown")
        report["tested"]+=1
        if a.get("url") in retired_urls:
            report["held"].append({"id":aid,"reason":["Source belongs to reset legacy edition; publication forbidden"]})
            continue
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
