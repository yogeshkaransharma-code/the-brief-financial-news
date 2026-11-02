"""Show all reports published today, with their real original source dates."""
from __future__ import annotations
import datetime as dt
from same_day_policy import clock, original_date, published_same_day, date_in_uk

RECENT_DAYS = 3

def homepage_articles(archive, now=None, limit=15):
    """Show reports published today, including dated catch-up; otherwise show recent work."""
    current = clock(now).date()
    # A report published today must not disappear solely because the
    # underlying source was published yesterday. The public card and article
    # display the original source date separately from our publication date.
    today = [
        a for a in archive
        if published_same_day(a, now)
        and 0 <= (current - original_date(a)).days <= RECENT_DAYS
    ]
    if today:
        return today[:limit], False
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
    catchup=dict(base,id="catchup",dateISO="2026-10-31",
                 published_at="2026-11-01T10:00:00Z")
    got,earlier=homepage_articles([today,catchup,base],now)
    assert {a["id"] for a in got}=={"today","catchup"} and not earlier, (
        "Reports published today must remain visible with their actual original dates"
    )
    same_day_old_source=dict(base,id="newly_written",published_at="2026-11-01T09:15:00Z")
    got,earlier=homepage_articles([same_day_old_source],now)
    assert earlier and len(got)==1
    print("PASS: recent dated coverage stays visible without being called today's news")

if __name__=="__main__":
    self_test()
