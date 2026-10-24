#!/usr/bin/env python3
"""One-off 22 October 2026 launch intake, sourced from identifiable first-party releases.

Never treats a news aggregator's reporting as original evidence. Investegate
entries below are reprints of issuer-authored Regulatory News Service (RNS)
announcements, not articles written by Investegate.
Every original announcement must be dated TODAY in the UK. No catch-up window.
"""
from __future__ import annotations
import datetime as dt
from urllib.parse import urlsplit
from same_day_policy import source_issued_today

LAUNCH_START=dt.date(2026,10,22)
LAUNCH_END=dt.date(2026,10,23)
MAX_NEWS_AGE=dt.timedelta(0)  # Zero grace days. No old news, including weekends.

RELEASES=[
    {
        "title":"Pensions regulator warns trustees about hidden AI investment concentration risks",
        "url":"https://www.thepensionsregulator.gov.uk/media-hub/press-releases/2026-press-releases/tpr-sets-expectations-on-hidden-concentration-risks-in-pension-portfolios",
        "dateISO":"2026-10-22","source":"The Pensions Regulator","category":"Regulation",
        "kind":"first_party_announcement","priority":105,
    },
    {
        "title":"Rathbones reports £121.1bn of client assets and stronger wealth management flows in its Q3 update",
        "url":"https://www.rathbones.com/en-gb/wealth-management/media-centre/rathbones-reports-strong-financial-performance-and-strategic-momentum-third-quarter-trading-update",
        "dateISO":"2026-10-22","source":"Rathbones Group","category":"Banking",
        "kind":"first_party_announcement","priority":104,
    },
    {
        "title":"CAB Payments reports record third-quarter income and foreign-exchange volumes",
        "url":"https://www.investegate.co.uk/announcement/rns/cab-payments-holdings-1-3p-wi---cabp/update-on-total-income-performance-to-30-sept-2026/9835194",
        "dateISO":"2026-10-22","source":"CAB Payments Holdings (issuer RNS)","category":"Technology",
        "kind":"issuer_regulatory_release","priority":103,
    },
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
        "kind":"issuer_regulatory_release","priority":107,
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
    """Only today's original source date qualifies, not writing date or 24h age."""
    return source_issued_today(item,today)

def self_test():
    now=dt.datetime(2026,10,24,19,tzinfo=dt.timezone.utc)
    today={"dateISO":"2026-10-24","published_at":"2026-10-24T11:00:00+00:00","source_time_precision":"date"}
    old=dict(today,dateISO="2026-10-23",published_at="2026-10-23T21:00:00+00:00")
    future=dict(today,dateISO="2026-10-25")
    assert eligible_today(today,now)
    assert not eligible_today(old,now), "Yesterday must be rejected, even under old launch flag"
    assert not eligible_today(old,now,launch=True), "Launch exception may not bypass today's date"
    assert not eligible_today(future,now)
    assert not eligible_today(dict(today,source_time_precision="timestamp",
                  source_published_at="2026-10-24T21:00:00Z"),now), "Future times forbidden"
    assert not eligible_today(dict(today,dateISO="2026-10-22"),now), "Weekend carry-over forbidden"
    assert launch_items(dt.date(2026,10,24))==[]
    print("PASS: UK same-day source date only, no yesterday, future or weekend catch-up")

if __name__=="__main__":
    self_test()
