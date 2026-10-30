#!/usr/bin/env python3
"""Autonomous evidence and provenance gate for The Financial Edition.

Recognised official and original-journalism sources require complete evidence,
original dates, attribution and a separate review of every claim and heading.
Unresolved disputed reporting remains held. Articles disclose automated review.
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
# Throughput is bounded by the durable Gemini request budget, not an article quota.
POLICY_VERSION = "newsroom-original-reporting-2026-10-25-v6"
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
    if bundle.get('audit',{}).get('pipeline_version')==3:
        from single_pass import eligible as single_pass_eligible
        if edition_date is not None:return ['Single-pass articles use their actual current source date']
        return single_pass_eligible(bundle)
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
        from media_sources import publisher
        reporter=publisher(a['url'])
        combined_lead=(a.get("title","")+" "+a.get("short",""))
        if not reporter:
            problems.append("Unrecognised original publisher")
        if reporter and not re.search(r'(?i)(?<!\w)'+re.escape(reporter)+r'(?!\w)',combined_lead):
            problems.append("Independent reporter must be attributed in the headline or standfirst")
    if lane=='regulatory_proposal' and a.get('status')!='Proposal':
        problems.append('Regulatory consultation or discussion paper must be presented as a proposal')
    if lane=='regulatory_policy' and a.get('status')!='Published policy':
        problems.append('Final policy or guidance must be labelled as published policy, with effective dates preserved')
    if lane=='pra_publication' and a.get('status') not in {'Proposal','Published policy','Published report'}:
        problems.append('PRA publication has an invalid policy/proposal/report status')
    if lane=='regulatory_report' and a.get('status')!='Published report':
        problems.append('Regulatory research must be labelled a published report')
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
    if lane in {"fca_release","company_release","industry_release","official_release","issuer_rns","tpr_release","ombudsman_release","regulatory_finding"} and a.get("status")!="Confirmed announcement":
        problems.append("An official announcement must be labelled as such")
    if lane and a.get("category") not in {"Banking","Insurance","Technology","Regulation","Pensions","Brokers","Wealth"}:
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
    if len(source)<850:
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
        if not re.search(r'(?i)\b(?:says?|said|announced|published|reported|reports|according to|found|proposes?|consulting)\b',a['short']):
            problems.append("Consequential official findings must be explicitly attributed in the standfirst")
    count=sum(len(x.split()) for _,x in a["blocks"])
    if count>700:
        problems.append("Unusually long unattended financial interpretation")
    checks=audit.get("verbatim_source_checks",[])
    if len(checks)<4:
        problems.append("Too few fully supported, sourced sentences")
    # A second AI's SUPPORTED verdict is necessary but not proof of truth.
    review=audit.get("sentence_review") or {}
    if review.get("held")!=0 or review.get("supported",0)<4:
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
    for file in sorted(folder.glob("ai-*.json")):
        try:
            bundle=json.loads(file.read_text(encoding="utf-8"))
            if not isinstance(bundle,dict):raise ValueError('Bundle is not an object')
        except (OSError,ValueError) as error:
            report['held'].append({'id':file.stem,'reason':['Malformed saved bundle: '+str(error)]})
            continue
        a=bundle.get("draft") or {}
        aid=a.get("id","unknown")
        report["tested"]+=1
        if a.get("url") in retired_urls:
            report["held"].append({"id":aid,"reason":["Source belongs to reset legacy edition; publication forbidden"]})
            continue
        if aid in seen_id or a.get("url") in seen_url:
            report["held"].append({"id":aid,"reason":["Duplicate source/article"]})
            continue
        try:reasons=eligible(bundle,edition_date=edition_date)
        except (ValueError,KeyError,TypeError,IndexError) as error:reasons=['Invalid saved evidence bundle: '+str(error)]
        if reasons:
            report["held"].append({"id":aid,"reason":reasons})
            continue
        item=dict(a)
        item["reviewed_by"]="autonomous-evidence-screening"
        item["publication_method"]="autonomous"
        item["editorial_status"]="PUBLISHED: autonomous source-limited machine-screening (no human review)"
        item["published_at"]=dt.datetime.now(dt.timezone.utc).isoformat()
        item["reviewed_at"]=item["published_at"]
        item["publication"]="The Financial Edition"
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
            "independent_claim_checks":bundle["audit"].get("verbatim_source_checks",[]),
            "review_headings":True,
            "workflow_run_url":("https://github.com/"+os.getenv("GITHUB_REPOSITORY","")+"/actions/runs/"+os.getenv("GITHUB_RUN_ID","")),
            "claim_challenge_sentences":bundle["audit"].get("sentence_review",{}).get("reviewed",0),
            "editorial_omissions":bundle['audit'].get('editorial_omissions',[]),
            "editor_notes":"Original regulator or first-party banking/insurance release; machine-screened, not fact-certified by a human editor.",
            "residual_risk":"The AI and source may be wrong; a passing automated check does not prove a claim's meaning.",
        }
        if bundle['audit'].get('pipeline_version')==3:
            from single_pass import POLICY
            item.pop('reviewed_by',None);item.pop('reviewed_at',None)
            item['independent_review']=False
            item['editorial_status']='PUBLISHED: single-pass source-based AI writing; no independent or human review'
            review_record.update(review_mode='single_pass_source_based',automation_policy_version=POLICY,
                independent_review=False,independent_claim_checks=[],review_headings=False,claim_challenge_sentences=0,
                generated_draft_sha256=bundle['audit']['draft_sha256'],published_article_sha256=canonical(item),
                editor_notes='Original writing from a captured current source. Owner-authorised single writing pass; no separate AI or human editorial review.')
            review_record.pop('reviewed_draft_sha256',None)
            review_record['generated_at_utc']=review_record.pop('approved_at_utc')
            review_record['generation_actor']=review_record.pop('approved_by_github_actor')
            report['policy']=POLICY
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



