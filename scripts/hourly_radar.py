#!/usr/bin/env python3
"""The Brief's hourly source-linked reading desk.

A SOURCE LINK is NOT an AI-authored or independently verified full article.
Show an accurately attributed publisher headline and original link, with the
publisher's RSS timestamp. This lane spends no Gemini calls, never treats
syndicated search links as originals and never backdates older feeds.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from same_day_policy import source_issued_today, clock

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"data"/"hourly-radar.json"

PUBLISHERS={
 "BBC Business":("www.bbc.co.uk","bbc.co.uk","www.bbc.com","bbc.com"),
 "Sky Business":("news.sky.com",),
 "The Guardian Business":("www.theguardian.com","theguardian.com"),
 "The Guardian Money":("www.theguardian.com","theguardian.com"),
 "The Guardian Insurance":("www.theguardian.com","theguardian.com"),
 "The Guardian Banking":("www.theguardian.com","theguardian.com"),
 "Financial Times":("www.ft.com","ft.com"),
 "Bloomberg Markets":("www.bloomberg.com","bloomberg.com"),
 "Wall Street Journal Markets":("www.wsj.com","wsj.com"),
 "MarketWatch":("www.marketwatch.com","marketwatch.com"),
 "Finextra":("www.finextra.com","finextra.com"),
 "Finextra payments":("www.finextra.com","finextra.com"),
 "Insurance Business UK":("www.insurancebusinessmag.com","insurancebusinessmag.com"),
 "Commercial Risk":("www.commercialriskonline.com","commercialriskonline.com"),
 "Reinsurance News":("www.reinsurancene.ws","reinsurancene.ws"),
 "Insurance Journal":("www.insurancejournal.com","insurancejournal.com"),
 "Insurance Times":("www.insurancetimes.co.uk","insurancetimes.co.uk"),
 "Professional Pensions":("www.professionalpensions.com","professionalpensions.com"),
 "Money Marketing":("www.moneymarketing.co.uk","moneymarketing.co.uk"),
 "Mortgage Solutions":("www.mortgagesolutions.co.uk","mortgagesolutions.co.uk"),
 "FCA":("www.fca.org.uk","fca.org.uk"),
 "FCA publications":("www.fca.org.uk","fca.org.uk"),
 "Bank of England":("www.bankofengland.co.uk","bankofengland.co.uk"),
 "PRA":("www.bankofengland.co.uk","bankofengland.co.uk"),
 "HM Treasury":("www.gov.uk","gov.uk"),
 "HM Revenue & Customs":("www.gov.uk","gov.uk"),
 "Office for National Statistics":("www.gov.uk","gov.uk"),
 "Competition and Markets Authority":("www.gov.uk","gov.uk"),
 "Department for Work and Pensions":("www.gov.uk","gov.uk"),
}
# Sector stories, not generic lifestyle, world politics or crypto opinion.
FOCUS=re.compile(
 r"(?i)\b(?:insur\w*|reinsur\w*|underwrit\w*|broker\w*|"
 r"mga|lloyd'?s|commercial risk|pension\w*|retirement|"
 r"nationwide|virgin money|barclays|natwest|hsbc|santander|"
 r"lloyds banking|monzo|starling bank|revolut|"
 r"bank\w*|mortgage\w*|lending|loan\w*|credit|payments?|"
 r"financial services|fintech|financial conduct authority|"
 r"fca|pra|bank of england|financial ombudsman|"
 r"ftse|interest rates?|inflation|investment\w*|"
 r"chancellor|budget|taxation|savings?|capital market\w*)\b"
)
EXCLUDE=re.compile(r"(?i)\b(?:opinion|podcast|quiz|horoscope|fashion|recipes?|travel tips|gift guide)\b")

def safe_publisher(item):
    expected=PUBLISHERS.get(item.get("source"))
    try:p=urlsplit(item.get("url",""))
    except ValueError:return False
    return bool(expected and p.scheme=="https" and p.hostname in expected and
                not p.username and not p.password and p.port in (None,443)
                and p.path not in ("","/") and not p.path.endswith("/rss"))

def select(items,articles,now=None,limit=18):
    now=now or dt.datetime.now(dt.timezone.utc)
    urls={a.get("url") for a in articles}
    seen=set();output=[]
    for item in items:
        title=str(item.get("title","")).strip()
        if (not (24<=len(title)<=230) or not safe_publisher(item)
                or not FOCUS.search(title) or EXCLUDE.search(title)
                or item.get("url") in urls or not source_issued_today(item,now)):
            continue
        key=re.sub(r"[^a-z0-9]","",title.lower())[:110]
        if key in seen:continue
        seen.add(key)
        try:
            raw=item.get("source_published_at") or item.get("published_at")
            t=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
            if t.tzinfo is None or t>now:continue
        except (ValueError,TypeError):continue
        output.append({
            "title":title,"url":item["url"],"source":item["source"],
            "category":item.get("category","Banking"),"source_published_at":t.isoformat(),
            "dateISO":clock(now).date().isoformat(),
            "kind":"publisher_headline_not_independently_verified",
        })
    output.sort(key=lambda a:a["source_published_at"],reverse=True)
    return output[:limit]

def write(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    try:feeds=json.loads((ROOT/"data"/"live.json").read_text())
    except (OSError,ValueError):feeds={"items":[]}
    try:articles=json.loads((ROOT/"data"/"articles.json").read_text())
    except (OSError,ValueError):articles=[]
    items=select(feeds.get("items",[]),articles,now)
    state={"uk_date":clock(now).date().isoformat(),"checked_at":now.isoformat(),
           "kind":"publisher_headlines_only","items":items,
           "sources_checked":len(feeds.get("sources_checked",[]))}
    DEST.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n")
    print("HOURLY_SOURCE_DESK: "+json.dumps({"uk_date":state["uk_date"],"headlines":len(items),
         "checked_at":state["checked_at"],"feeds_working":state["sources_checked"]}))
    return state

def self_test():
    n=dt.datetime(2026,10,25,12,tzinfo=dt.timezone.utc)
    x={"title":"Nationwide to cut 275 jobs in latest round following Virgin Money takeover",
       "url":"https://www.theguardian.com/business/2026/oct/25/nationwide-to-cut-275-jobs-in-latest-round-since-takeover-of-virgin-money",
       "source":"The Guardian Business","category":"Banking","dateISO":"2026-10-25",
       "published_at":"2026-10-25T07:00:00+00:00",
       "source_published_at":"2026-10-25T07:00:00+00:00","source_time_precision":"timestamp"}
    assert len(select([x],[],n))==1
    assert select([x],[{"url":x["url"]}],n)==[]
    assert select([dict(x,dateISO="2026-10-24",published_at="2026-10-24T07:00:00+00:00",source_published_at="2026-10-24T07:00:00+00:00")],[],n)==[]
    assert not select([dict(x,url="https://theguardian.com.evil.org/business/2026/oct/25/test")],[],n)
    assert not select([dict(x,source="Google News",url="https://news.google.com/rss/articles/foo")],[],n)
    assert not select([dict(x,title="Travel tips for autumn breaks")],[],n)
    assert not select([dict(x,source_published_at="2026-10-25T13:00:00+00:00")],[],n)
    assert not select([dict(x,url="http://www.theguardian.com/business/2026/oct/25/article")],[],n)
    print("PASS: hourly source desk same-day attribution, known-host, future-date and duplicate controls")
if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv:self_test()
    else:write()
