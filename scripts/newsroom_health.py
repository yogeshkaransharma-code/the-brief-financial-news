#!/usr/bin/env python3
"""Make newsroom failures visible without mistaking a successful job for news."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]

def assess(article_list,report,now):
    published=[]
    for item in article_list:
        try:
            stamp=dt.datetime.fromisoformat(str(item["published_at"]).replace("Z","+00:00"))
            if stamp.tzinfo:published.append(stamp.astimezone(dt.timezone.utc))
        except (KeyError,ValueError,TypeError):
            pass
    published.sort(reverse=True)
    recent=sum(dt.timedelta()<=now-x<=dt.timedelta(hours=24) for x in published)
    fresh=report.get("fresh_unpublished_source_candidates",0)
    available=report.get("available_after_retry_cooldowns",0)
    screened=report.get("machine_screened",0)
    quota=report.get("active_quota_pause_until")
    spend=report.get("api_budget") or {}
    if quota:
        state="API capacity paused"
    elif spend and spend.get("remaining_today")==0:
        state="Daily AI request budget exhausted; no more paid calls"
    elif fresh and not available:
        state="Source retry holds are excluding all fresh candidates"
    elif report.get("eligible_for_this_run",0)==0:
        state="No source eligible for writing in this run"
    elif screened==0:
        state="Source reading or independent verification blocked publication"
    else:
        state="At least one draft passed machine screening"
    return {"published_total":len(article_list),"published_last_24h":recent,
            "last_article_at":published[0].isoformat() if published else None,
            "fresh_source_candidates":fresh,"candidates_after_cooldowns":available,
            "machine_screened":screened,"traced_originals":report.get("traced_originals",0),
            "status":state,"quota_pause_until":quota,"ai_budget":spend}

def main():
    now=dt.datetime.now(dt.timezone.utc)
    try:articles=json.loads((ROOT/"data/articles.json").read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError):articles=[]
    try:report=json.loads((ROOT/"generated-drafts/run-report.json").read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError):report={}
    state=assess(articles,report,now)
    print("NEWSROOM_HEALTH: "+json.dumps(state,sort_keys=True))
    lines=[
        "## The Brief newsroom health",
        "",
        "| Measure | Status |",
        "| --- | --- |",
        f"| Published articles | {state['published_total']} |",
        f"| Published in last 24 hours | {state['published_last_24h']} |",
        f"| Most recent publication UTC | {state['last_article_at'] or 'None'} |",
        f"| Fresh original candidates | {state['fresh_source_candidates']} |",
        f"| Official sources traced from news links | {state['traced_originals']} |",
        f"| After retry holds | {state['candidates_after_cooldowns']} |",
        f"| Machine-screened new drafts | {state['machine_screened']} |",
        f"| AI requests in this run | {state['ai_budget'].get('requests_this_run','unknown')} |",
        f"| AI requests used today / cap | {state['ai_budget'].get('requests_today_including_this_run','unknown')} / {state['ai_budget'].get('daily_limit','unknown')} |",
        f"| Operational state | {state['status']} |",
        "",
        "A green GitHub job alone does not mean an article was published.",
        "Held drafts stay unpublished until their evidence checks pass.",
    ]
    if report.get("original_source_trace"):
        lines.append("")
        lines.append("### Source tracing")
        for item in report["original_source_trace"][:12]:
            lines.append("- "+str(item.get("result","unresolved"))+": "+str(item.get("headline","source"))[:115])
    path=os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path,"a",encoding="utf-8") as fh:fh.write("\n".join(lines)+"\n")
    if state["published_last_24h"]==0:
        print("::warning::No article has been published in the last 24 hours. The successful workflow only confirms the checks completed.")
    if state["quota_pause_until"]:
        print("::warning::Gemini usage capacity is paused until "+str(state["quota_pause_until"]))

if __name__=="__main__":
    if "--self-test" in sys.argv:
        n=dt.datetime(2026,10,24,tzinfo=dt.timezone.utc)
        a=assess([{"published_at":"2026-10-23T18:18:00+00:00"}],
                 {"fresh_unpublished_source_candidates":4,"available_after_retry_cooldowns":0},n)
        assert a["published_last_24h"]==1
        assert a["status"]=="Source retry holds are excluding all fresh candidates"
        print("PASS: no-new-article status and bounded publication clock")
    else:main()
