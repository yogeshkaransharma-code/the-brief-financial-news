"""Select clearly dated existing reports for the homepage and sector desks.

These are display windows only: they never change the newsroom's eligibility,
source-date rules, or the complete permanent archive.
"""
from __future__ import annotations
import datetime as dt
from same_day_policy import clock, original_date, published_same_day, date_in_uk

HOME_DAYS = 7
DESK_DAYS = 14


def homepage_articles(archive, now=None, limit=15, days=HOME_DAYS):
    """Published within the last 'days' UK calendar dates, newest first.

    'days=7' means today plus six preceding UK dates. Keep the original
    source date independent from our actual publication timestamp.
    """
    if days < 1 or limit < 1:
        raise ValueError("Display days and limit must be positive")
    uk_now = clock(now)
    current = uk_now.date()
    items = []
    for a in archive:
        try:
            publication = dt.datetime.fromisoformat(str(a["published_at"]).replace("Z", "+00:00"))
            if publication.tzinfo is None or publication > uk_now:
                continue
            published_date = date_in_uk(a["published_at"])
            age = (current - published_date).days
            if 0 <= age < days and original_date(a) <= published_date:
                items.append(a)
        except (KeyError, ValueError, TypeError, OverflowError):
            continue
    items.sort(key=lambda a: dt.datetime.fromisoformat(
        str(a["published_at"]).replace("Z", "+00:00")
    ), reverse=True)
    selected = items[:limit]
    # This flag affects only the honest label on a quiet-day lead.
    showing_earlier = bool(selected) and not any(
        published_same_day(a, now) for a in selected
    )
    return selected, showing_earlier


def self_test():
    now = dt.datetime(2026, 11, 2, 11, tzinfo=dt.timezone.utc)
    base = {"id": "old", "source_time_precision": "date",
            "dateISO": "2026-10-30", "published_at": "2026-10-30T17:20:00Z",
            "publication_method": "autonomous", "ai_assisted": True,
            "editorial_status": "PUBLISHED: test"}
    today = dict(base, id="today", dateISO="2026-11-02",
                 published_at="2026-11-02T09:00:00Z")
    catchup = dict(base, id="catchup", dateISO="2026-11-01",
                   published_at="2026-11-02T09:30:00Z")
    week_edge = dict(base, id="week_edge", dateISO="2026-10-27",
                     published_at="2026-10-27T11:00:00Z")
    week_expired = dict(base, id="week_expired", dateISO="2026-10-26",
                        published_at="2026-10-26T11:00:00Z")
    selected, earlier = homepage_articles(
        [week_edge, base, today, week_expired, catchup], now)
    assert [a["id"] for a in selected] == ["catchup", "today", "old", "week_edge"]
    assert not earlier, "A new report was wrongly hidden by older source dating"
    assert {a["id"] for a in homepage_articles([base, week_edge], now)[0]} == {"old", "week_edge"}
    assert homepage_articles([base, week_edge], now)[1], "Older cover must say earlier report"
    assert {a["id"] for a in homepage_articles([week_expired, week_edge], now, days=DESK_DAYS)[0]} == {
        "week_expired", "week_edge"
    }
    desk_edge = dict(base, id="desk_edge", dateISO="2026-10-20",
                     published_at="2026-10-20T12:00:00Z")
    desk_expired = dict(base, id="desk_expired", dateISO="2026-10-19",
                        published_at="2026-10-19T12:00:00Z")
    desk, _ = homepage_articles([desk_edge, desk_expired], now, days=DESK_DAYS)
    assert [a["id"] for a in desk] == ["desk_edge"], "14-day desk boundary incorrect"
    assert [a["id"] for a in homepage_articles([today, catchup], now, limit=1)[0]] == ["catchup"]
    future = dict(base, id="future", published_at="2026-11-02T15:00:00Z")
    assert not homepage_articles([future], now)[0], "Future-dated publication escaped"
    future_source = dict(base, id="future_source", dateISO="2026-11-03",
                         published_at="2026-11-02T09:00:00Z")
    assert not homepage_articles([future_source], now)[0], "Future source date escaped"
    assert not homepage_articles([desk_expired], now)[0]
    print("PASS: rolling 7-day home, 14-day desks, dated carry-over, publication limits and future-date safety")


if __name__ == "__main__":
    self_test()
