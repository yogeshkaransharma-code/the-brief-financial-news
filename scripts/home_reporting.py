"""Show recently published, honestly dated sector stories on a quiet news day."""
from __future__ import annotations
import datetime as dt
from same_day_policy import clock, original_date, published_same_day, date_in_uk, source_issued_today

RECENT_DAYS = 3

def homepage_articles(archive, now=None, limit=15):
    """Prefer original news from today; otherwise show clearly dated recent reports."""
    current = clock(now).date()
    today = [a for a in archive if published_same_day(a, now) and source_issued_today(a, now)]
    if today:
        return today, False
    recent = [
        a for a in archive
        if 0 <= (current - original_date(a)).days <= RECENT_DAYS
        and date_in_uk(a["published_at"]) <= current
    ]
    return recent[:limit], bool(recent)

def self_test():
    now=dt.datetime(2026,11,1,11,tzinfo=dt.timezone.utc)
    base={"id":"test","source_time_precision":"date","dateISO":"2026-10-30",
          "published_at":"2026-10-30T17:20:00Z","publication_method":"autonomous",
          "ai_assisted":True,"editorial_status":"PUBLISHED: test"}
    got,earlier=homepage_articles([base],now)
    assert len(got)==1 and earlier
    assert homepage_articles([dict(base,dateISO="2026-10-27")],now)==([],False)
    today=dict(base,id="today",dateISO="2026-11-01",published_at="2026-11-01T09:00:00Z")
    got,earlier=homepage_articles([today,base],now)
    assert len(got)==1 and got[0]["id"]=="today" and not earlier
    same_day_old_source=dict(base,id="newly_written",published_at="2026-11-01T09:15:00Z")
    got,earlier=homepage_articles([same_day_old_source],now)
    assert earlier and len(got)==1
    print("PASS: recent dated coverage stays visible without being called today's news")

if __name__=="__main__":
    self_test()
