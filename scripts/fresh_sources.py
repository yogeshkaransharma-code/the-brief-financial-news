#!/usr/bin/env python3
"""One-off 22 October 2026 launch intake, sourced from identifiable first-party releases.

Never treats a news aggregator's reporting as original evidence. Investegate
entries below are reprints of issuer-authored Regulatory News Service (RNS)
announcements, not articles written by Investegate.
After launch, the rolling 24-hour rule applies to every discovery channel.
"""
from __future__ import annotations
import datetime as dt
from urllib.parse import urlsplit

LAUNCH_START=dt.date(2026,10,22)
LAUNCH_END=dt.date(2026,10,23)

RELEASES=[
    {
        "title":"Financial Services Regulation Committee publishes report on home and travel insurance regulation",
        "url":"https://publications.parliament.uk/pa/ld5902/ldselect/ldfsrc/64/6403.htm",
        "dateISO":"2026-10-23","source":"UK Parliament","category":"Insurance",
        "kind":"first_party_announcement",
        "priority":100,
    },
    {
        "title":"Major Standard Life study finds friction can stop customers understanding pension decisions",
        "url":"https://www.standardlifeplc.com/news-and-views/press-releases/article-page/major-standard-life-study-finds-friction",
        "dateISO":"2026-10-22","source":"Standard Life","category":"Insurance",
        "kind":"first_party_announcement","priority":99,
    },
    {
        "title":"Complaints data: 2026 H1",
        "url":"https://www.fca.org.uk/data/complaints-data-2026-h1",
        "dateISO":"2026-10-22","source":"Financial Conduct Authority","category":"Regulation",
        "kind":"official_statistics","priority":98,
    },
    {
        "title":"Secure Trust Bank reports its third-quarter 2026 trading update",
        "url":"https://www.investegate.co.uk/announcement/rns/secure-trust-bank--stb/q3-2026-trading-update/9835238",
        "dateISO":"2026-10-22","source":"Secure Trust Bank (issuer RNS)","category":"Banking",
        "kind":"issuer_regulatory_release","priority":97,
    },
    {
        "title":"Arbuthnot Banking Group reports third-quarter lending and deposit growth",
        "url":"https://www.investegate.co.uk/announcement/rns/arbuthnot-banking-group--arbb/third-quarter-2026-trading-update/9835245",
        "dateISO":"2026-10-22","source":"Arbuthnot Banking Group (issuer RNS)","category":"Banking",
        "kind":"issuer_regulatory_release","priority":96,
    },
    {
        "title":"Barclays announces third-quarter 2026 financial results",
        "url":"https://www.investegate.co.uk/announcement/rns/barclays--barc/3rd-quarter-results/9835199",
        "dateISO":"2026-10-22","source":"Barclays PLC (issuer RNS)","category":"Banking",
        "kind":"issuer_regulatory_release","priority":96,
    },
    {
        "title":"Lloyds Banking Group announces board appointments following ring-fencing changes",
        "url":"https://www.investegate.co.uk/announcement/rns/lloyds-banking-group--lloy/board-change/9836547",
        "dateISO":"2026-10-22","source":"Lloyds Banking Group (issuer RNS)","category":"Banking",
        "kind":"issuer_regulatory_release","priority":85,
    },
    {
        "title":"Lloyds Banking Group appoints Chris Rhodes to its board",
        "url":"https://www.investegate.co.uk/announcement/rns/lloyds-banking-group--lloy/board-change/9836457",
        "dateISO":"2026-10-22","source":"Lloyds Banking Group (issuer RNS)","category":"Banking",
        "kind":"issuer_regulatory_release","priority":80,
    }
]

def launch_items(today=None):
    today=today or dt.datetime.now(dt.timezone.utc).date()
    # This is a bounded launch exception, not a daily backfill permission.
    if today>LAUNCH_END or today<LAUNCH_START:
        return []
    result=[]
    for item in RELEASES:
        # No future-dated content, even within the one-off launch window.
        issued=dt.date.fromisoformat(item["dateISO"])
        if issued>today:continue
        entry=dict(item)
        entry["published_at"]=entry["dateISO"]+"T00:00:00+00:00"
        entry["source_time_precision"]="date"
        result.append(entry)
    return result

def eligible_today(item,today=None,launch=False):
    today=today or dt.datetime.now(dt.timezone.utc)
    try:
        stamp=dt.datetime.fromisoformat(item["published_at"].replace("Z","+00:00"))
        if stamp.tzinfo is None:return False
        age=today-stamp
        # A newsroom listing that supplies only a calendar date cannot justify
        # claiming the release was within an exact rolling 24-hour interval.
        if item.get("source_time_precision")=="date":
            if today.date()==dt.date.fromisoformat(item["dateISO"]):
                return True
        elif dt.timedelta(0)<=age<=dt.timedelta(hours=24):
            return True
        if launch and today.date()<=LAUNCH_END and LAUNCH_START<=dt.date.fromisoformat(item["dateISO"])<=today.date():
            return True
    except (ValueError,KeyError,TypeError):
        pass
    return False

def self_test():
    now=dt.datetime(2026,10,23,10,tzinfo=dt.timezone.utc)
    assert len(launch_items(dt.date(2026,10,23)))>=5
    assert launch_items(dt.date(2026,10,24))==[]
    fixture={"published_at":"2026-10-22T08:00:00+00:00","dateISO":"2026-10-22"}
    assert not eligible_today(fixture,now)
    assert eligible_today(fixture,now,launch=True)
    fixture["published_at"]="2026-10-23T08:00:00+00:00"
    assert eligible_today(fixture,now)
    print("PASS: one-off 22 October launch and permanent 24-hour fresh-news cutoff")

if __name__=="__main__":
    self_test()
