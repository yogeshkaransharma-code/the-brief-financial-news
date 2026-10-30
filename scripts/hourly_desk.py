#!/usr/bin/env python3
"""Publish a genuinely refreshed hourly desk edition from already approved, source-dated reports.

This is a continuously updated guide to existing reporting, NOT 24 fabricated
new articles a day. It must never relabel historical developments as today's news.
No network, model requests or unsupported interpretation.
"""
from __future__ import annotations
import datetime as dt
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
LONDON=ZoneInfo("Europe/London")

def make(articles, now=None, *, newly_published=0):
    now=now or dt.datetime.now(dt.timezone.utc)
    today=now.astimezone(LONDON).date().isoformat()
    approved=[a for a in articles
              if a.get("publication_method")=="autonomous"
              and str(a.get("editorial_status","")).startswith("PUBLISHED:")
              and a.get("id","").startswith("ai-")
              and a.get("title") and a.get("short")]
    def as_date(a):
        return str(a.get("dateISO") or "")[:10]
    # Actual source dates, not rerun/deploy dates.
    today_items=[a for a in approved if as_date(a)==today
                 and a.get("published_at","") and
                 dt.datetime.fromisoformat(a["published_at"]).astimezone(LONDON).date().isoformat()==today]
    older=[a for a in approved if as_date(a)<today]
    today_items.sort(key=lambda x:x.get("published_at",""),reverse=True)
    older.sort(key=lambda x:x.get("dateISO",""),reverse=True)
    take=today_items[:6] if today_items else older[:6]
    def entry(a):
        return {"id":a["id"],"title":a["title"],"summary":a["short"][:330],
                "category":a.get("category","Financial services"),
                "source":a.get("source","Original source"),"original_date":as_date(a),
                "published_at":a.get("published_at"),"source_url":a.get("url")}
    return {"checked_at":now.astimezone(dt.timezone.utc).isoformat(),
            "edition_date":today, "mode":"TODAY_VERIFIED" if today_items else ("DATED_CONTEXT" if older else "EMPTY"),
            "today_count":len(today_items),"new_original_articles_this_run":int(newly_published),
            "items":[entry(a) for a in take],
            "editorial_note":("This hour's briefing links to previously approved complete reports; it does not claim a new development each hour. "
                              "Original source dates remain visible. Older reporting is identified as background.")}

def page(data):
    e=lambda x:html.escape(str(x or ""),quote=True)
    stamp=dt.datetime.fromisoformat(data["checked_at"]).astimezone(LONDON).strftime("%-d %B %Y, %H:%M %Z")
    date=e(data["edition_date"])
    historical=data["mode"]=="DATED_CONTEXT"
    label="Earlier reporting — background, not today's news" if historical else "Reports verified for this UK date"
    if data["mode"]=="EMPTY":label="No previously approved reports available"
    rows=[]
    for item in data["items"]:
        url="../" if False else "story/"+e(item["id"])+".html"
        rows.append('<article class="item"><div class="eyebrow">'+e(item["category"])+' · Original source: '+e(item["original_date"])+
                    '</div><h2><a href="'+url+'">'+e(item["title"])+'</a></h2><p>'+e(item["summary"])+
                    '</p><small>Reported from '+e(item["source"])+' · <a href="'+url+'">Read The Financial Edition article</a></small></article>')
    body="".join(rows) if rows else '<p>There is no verified reporting to recap. <a href="archive.html">Visit the archive</a>.</p>'
    return """<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hourly desk · The Financial Edition</title><meta name="description" content="The Financial Edition newsroom edition, refreshed hourly and accurately dated.">
<style>:root{color-scheme:light}*{box-sizing:border-box}body{margin:0;background:#f6f4ee;color:#102639;font:15px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}a{color:inherit}a:hover{color:#156b70}
nav{background:#102639;color:white;padding:16px max(22px,calc((100vw - 1120px)/2))}nav a{text-decoration:none;margin-right:22px}.brand{font:bold 27px Georgia,serif}
main{max-width:1120px;margin:auto;padding:48px 25px 100px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;color:#23737a}
h1{font:normal clamp(42px,6vw,70px)/1 Georgia,serif;letter-spacing:-.04em;max-width:760px}h2{font:normal 28px/1.2 Georgia,serif;margin:12px 0}
.subtitle{font-size:17px;color:#546475;max-width:700px}.stamp{font-size:13px;background:#e1eceb;display:inline-block;padding:9px 16px;border-radius:24px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:28px}.item{padding:27px;background:white;border:1px solid #dce3e4;border-top:3px solid #246d72}.item p{color:#526270}.item small{color:#64737e}aside{border-top:1px solid #cad6d7;margin-top:38px;padding-top:20px;color:#526270;font-size:13px}@media(max-width:690px){.grid{grid-template-columns:1fr}main{padding-top:30px}}</style></head><body>
<nav><a class="brand" href="index.html">THE FINANCIAL EDITION.</a><a href="index.html">Today's edition</a><a href="archive.html">Archive</a></nav>
<main><div class="eyebrow">The Financial Edition / news intelligence</div><h1>The hourly desk.</h1><p class="subtitle">A current guide to our complete financial-services reporting, without recycling old events as breaking developments.</p>
<div class="stamp">Last newsroom refresh: """+e(stamp)+"""</div><p><strong>"""+e(label)+"""</strong></p>
<section class="grid" aria-label="Sourced article briefings">"""+body+"""</section>
<aside>"""+e(data["editorial_note"])+""" Sources and original dates appear with each article. This is a briefing of previously reviewed material, not a claim of new reporting this hour.</aside>
</main></body></html>"""

def refresh(root=ROOT,now=None):
    root=Path(root)
    articles=json.loads((root/"data/articles.json").read_text(encoding="utf-8"))
    path=root/"generated-drafts/publication-report.json"
    try:report=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):report={}
    data=make(articles,now,newly_published=len(report.get("published",[])))
    dest=root/"data/hourly-desk.json";dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("HOURLY_DESK:",json.dumps({"mode":data["mode"],"as_of":data["checked_at"],"items":len(data["items"]),"new_full_articles":data["new_original_articles_this_run"]}))
    return data

if __name__=="__main__":refresh()
