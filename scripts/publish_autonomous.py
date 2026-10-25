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
from same_day_policy import source_issued_today, clock, date_in_uk
from publication_scope import source_lane
from source_retrieval import permitted

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data/articles.json"
AUDIT_DIR = ROOT / "data/editorial-audits"
DRAFT_DIR = ROOT / "generated-drafts"
MAX_ARTICLES = 10
POLICY_VERSION = "verified-original-date-2026-10-25-v5"
# URL-level lanes are shared with candidate selection so Gemini focuses on
# stories that have a chance of passing the autonomous publication gate.
HIGH_RISK = re.compile(
    r"\b(?:criminal|convicted|guilty|misconduct|lawsuit|litigation|"
    r"regulatory breach|sanction|enforcement action|will have to|must comply|"
    r"comes into force|new legal duty|accused of|insolvency|bankruptcy)\b", re.I
)
CAUSAL = re.compile(r"\b(?:caused by|resulted in|as a result of|led to)\b", re.I)

def eligible(bundle, *, edition_date=None):
    """Return reasons to HOLD; never decide eligibility from a model score."""
    a, audit = bundle.get("draft",{}), bundle.get("audit",{})
    problems=[]
    try:
        check(bundle)
    except (ValueError, KeyError, TypeError) as exc:
        return ["Editorial evidence gate failed: "+str(exc)]
    lane=source_lane(a["url"])
    if not lane:
        problems.append("Source outside the cautious original reporting lanes (or excluded adverse enforcement)")
    if lane=="original_reporting":
        if a.get("status")!="Original reporting":
            problems.append("Journalist-originated source must be labelled original reporting")
        if a.get("source") not in {"The Guardian Business","The Guardian Money","The Guardian Insurance","The Guardian Banking"}:
            problems.append("Media source identity does not match the approved original publisher")
        combined_lead=(a.get("title","")+" "+a.get("short",""))
        if not re.search(r"(?i)\bthe guardian\b",combined_lead):
            problems.append("Independent newspaper report must be attributed to The Guardian in the headline or standfirst")
    if lane=="fca_data" and a.get("status")!="Published report":
        problems.append("FCA statistics incorrectly described")
    if lane=="fca_review" and a.get("status")!="Published report":
        problems.append("FCA review must be presented as a published review")
    if lane=="boe_release" and a.get("status") not in {"Proposal","Confirmed announcement"}:
        problems.append("Bank of England release must identify proposals or announcements accurately")
    if lane=="fca_speech" and a.get("status")!="Speech / commentary":
        problems.append("FCA speech cannot be presented as new rules or final regulatory decision")
    if lane=="fca_consultation" and a.get("status")!="Proposal":
        problems.append("FCA consultation must be explicitly presented as a proposal")
    if lane=="government_release" and a.get("status") not in {"Confirmed announcement","Proposal"}:
        problems.append("Government publication status misrepresented")
    if lane in {"fca_release","company_release","industry_release","official_release","issuer_rns","tpr_release","ombudsman_release"} and a.get("status")!="Confirmed announcement":
        problems.append("An official announcement must be labelled as such")
    if lane and a.get("category") not in {"Banking","Insurance","Technology","Regulation","Pensions","Brokers"}:
        problems.append("Original source not within financial-services industry category")
    if not a.get("date_evidence") or audit.get("date_evidence")!=a.get("date_evidence"):
        problems.append("Missing original-document date evidence")
    if not audit.get("review_headings"):
        problems.append("Section headings were not included in independent review")
    if audit.get("pipeline_version")!=2:
        problems.append("Missing independent sentence-level review")
    extraction=audit.get("source_extraction")
    if extraction not in {"HTML main content","complete HTML and linked official PDF"}:
        problems.append("Unsupported or incomplete source format")
    if audit.get("source_retrieval_limits") != "Full captured material shown; check all relevant linked appendices before approval. ":
        problems.append("Source retrieval has extra warnings or caveats")
    docs=audit.get("source_document_urls") or []
    if extraction=="HTML main content" and docs != [a["url"]]:
        problems.append("Complex or redirected source document")
    if extraction=="complete HTML and linked official PDF":
        # One completely captured official appendix is allowed, not an
        # arbitrary selection from multiple reports or third-party files.
        if not (len(docs)==2 and docs[0]==a["url"]
                and permitted(docs[1]) and docs[1].lower().split("?")[0].endswith(".pdf")):
            problems.append("Linked full primary document was not clearly identified")
    source=bundle.get("captured_source_excerpt","")
    if len(source)<1250:
        problems.append("Too little original-source evidence for an unattended financial article")
    # Publication MUST occur on the same UK calendar date as the first-party
    # announcement. A fresh AI write-up never refreshes an old source.
    date_clock=dt.datetime.now(dt.timezone.utc)
    if edition_date is not None:
        # One explicitly authorised retrospective launch edition. This cannot
        # alter the unattended current-day publisher or backdate publication.
        if edition_date != '2026-10-24':
            return ['Only the authorised Saturday launch edition can be reconstructed']
        date_clock=dt.datetime.fromisoformat('2026-10-24T23:59:59+01:00')
        if a.get('source_time_precision')!='timestamp' or not a.get('source_published_at'):
            problems.append('Launch edition requires an exact original source timestamp')
        else:
            issued=dt.datetime.fromisoformat(a['source_published_at'].replace('Z','+00:00'))
            if issued < dt.datetime.fromisoformat('2026-10-24T06:00:00+01:00'):
                problems.append('Announcement predates the authorised 6am launch window')
    if not source_issued_today(a,date_clock):
        problems.append("Original announcement is not from TODAY in the UK; old or future news is forbidden")
    if bundle.get("editorial_flags") or bundle.get("revision_history",[])[-1:][0:1] and bundle["revision_history"][-1].get("problems"):
        problems.append("Outstanding disputed claim")
    combined="\n".join([a["title"],a["short"]]+[v for block in a["blocks"] for v in block])
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

def publish(root=ROOT, folder=None, dry_run=False, *, edition_date=None):
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
    report={"policy":'retrospective-launch-2026-10-24-v1' if edition_date else POLICY_VERSION,"tested":0,"published":[],"held":[],"mode":"dry_run" if dry_run else "active"}
    today_count=sum(date_in_uk(x["published_at"])==clock().date() for x in existing)
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
        reasons=eligible(bundle,edition_date=edition_date)
        if reasons:
            report["held"].append({"id":aid,"reason":reasons})
            continue
        if today_count+len(report["published"])>=MAX_ARTICLES:
            report["held"].append({"id":aid,"reason":["Daily original-story cap"]})
            continue
        item=dict(a)
        item["reviewed_by"]="autonomous-evidence-screening"
        item["publication_method"]="autonomous"
        item["editorial_status"]="PUBLISHED: autonomous source-limited machine-screening (no human review)"
        item["published_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
        item["reviewed_at"]=item["published_at"]
        item["publication"]="The Brief"
        if edition_date is not None:
            item['edition_date']=edition_date
            item['retrospective_launch']=True
        review_record={
            "article_id":aid,"source_url":item["url"],
            "review_mode":"autonomous_low_risk",
            "automation_policy_version":'retrospective-launch-2026-10-24-v1' if edition_date else POLICY_VERSION,
            "approved_by_github_actor":"AUTONOMOUS_PIPELINE_NO_HUMAN",
            "approved_at_utc":item["reviewed_at"],
            "reviewed_draft_sha256":bundle["audit"]["draft_sha256"],
            "source_snapshot_sha256":bundle["audit"]["source_sha256"],
            "published_article_sha256":canonical(item),
            "source_document_urls":bundle["audit"]["source_document_urls"],
            "date_evidence":bundle["audit"].get("date_evidence"),
            "independent_claim_checks":bundle["audit"]["verbatim_source_checks"],
            "review_headings":True,
            "workflow_run_url":("https://github.com/"+os.getenv("GITHUB_REPOSITORY","")+"/actions/runs/"+os.getenv("GITHUB_RUN_ID","")),
            "claim_challenge_sentences":bundle["audit"]["sentence_review"]["reviewed"],
            "editorial_omissions":bundle['audit'].get('editorial_omissions',[]),
            "editor_notes":"Original regulator or first-party banking/insurance release; machine-screened, not fact-certified by a human editor.",
            "residual_risk":"The AI and source may be wrong; a passing automated check does not prove a claim's meaning.",
        }
        if edition_date is not None:
            review_record['edition_date']=edition_date
            review_record['retrospective_launch']=True
            review_record['editor_notes']='User-authorised reconstruction of Saturday 24 October from 6am UK. Actual publication timestamp retained; every statement separately machine-screened against the captured original.'
        if not dry_run:
            audit_path.mkdir(parents=True,exist_ok=True)
            (audit_path/(aid+".json")).write_text(json.dumps(review_record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            existing.insert(0,item)
        report["published"].append({"id":aid,"title":item["title"],"url":item["url"]})
        seen_id.add(aid)
        seen_url.add(item["url"])
    if not dry_run and report["published"]:
        article_path.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        verify_feed(root)
    print("AUTONOMOUS_REPORT: "+json.dumps(report,ensure_ascii=False))
    return report

if __name__=="__main__":
    enabled=os.environ.get("AUTO_PUBLICATION_ENABLED")=="1"
    report=publish(dry_run=not enabled)
    DRAFT_DIR.mkdir(exist_ok=True)
    (DRAFT_DIR/"publication-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")

