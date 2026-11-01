#!/usr/bin/env python3
"""The Brief's non-negotiable UK same-calendar-day news rule.

The original first-party source must be dated on the UK date of publication.
No catch-up, weekend carry-over, false "published today" relabelling or
yesterday's press releases disguised as a new development.
"""
from __future__ import annotations
import datetime as dt
from zoneinfo import ZoneInfo

UK = ZoneInfo("Europe/London")
SOURCE_WINDOW_DAYS = 2  # Today and the two previous UK calendar days.


def clock(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Naive current time forbidden")
    return now.astimezone(UK)


def date_in_uk(value):
    parsed = dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Publication timestamp must carry timezone")
    return parsed.astimezone(UK).date()


def original_date(item):
    """Only first-party source timestamps and explicit source dates count."""
    precision=item.get("source_time_precision")
    if precision=="timestamp":
        raw=item.get("source_published_at")
        if not raw:
            raise ValueError("Missing original source timestamp")
        day=date_in_uk(raw)
        # A source-reported date may be its local date or UTC date at midnight.
        source_date=dt.date.fromisoformat(str(item["dateISO"])[:10])
        utc_day=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00")).astimezone(dt.timezone.utc).date()
        if source_date not in {day,utc_day}:
            raise ValueError("Source date conflicts with both the UK and UTC original timestamp")
        return day
    if precision in (None,"date"):
        return dt.date.fromisoformat(str(item["dateISO"])[:10])
    raise ValueError("Unknown source timestamp precision")


def source_issued_today(item, now=None):
    current=clock(now)
    try:
        if original_date(item)!=current.date():
            return False
        if item.get("source_time_precision")=="timestamp":
            raw=item.get("source_published_at") or item.get("published_at")
            issue=dt.datetime.fromisoformat(str(raw).replace("Z","+00:00"))
            return issue.tzinfo is not None and issue<=current
        # Date-only source: never infer/fabricate an hour.
        return True
    except (KeyError,ValueError,TypeError,OverflowError):
        return False


def source_recent(item, now=None, max_age_days=SOURCE_WINDOW_DAYS):
    """A verified, genuinely dated source from today or two previous UK days.

    The original source date never changes, and future-dated material fails.
    """
    current = clock(now)
    try:
        age = (current.date() - original_date(item)).days
        if not 0 <= age <= max_age_days:
            return False
        if item.get("source_time_precision") == "timestamp":
            published = dt.datetime.fromisoformat(str(item.get("source_published_at")).replace("Z", "+00:00"))
            return published.tzinfo is not None and published <= current
        return True
    except (KeyError, ValueError, TypeError, OverflowError):
        return False


def published_same_day(item, now=None):
    """An article ACTUALLY published today from an accurately dated recent source."""
    try:
        if item.get('retrospective_launch'):return False
        uk_pub=date_in_uk(item["published_at"])
        return (source_recent(item,dt.datetime.fromisoformat(str(item["published_at"]).replace("Z","+00:00")))
                and dt.datetime.fromisoformat(str(item["published_at"]).replace("Z","+00:00"))<=clock(now)
                and uk_pub==clock(now).date()
                and item.get("publication_method")=="autonomous"
                and item.get("ai_assisted") is True
                and str(item.get("editorial_status","")).startswith("PUBLISHED:"))
    except (KeyError,ValueError,TypeError,OverflowError):
        return False


def self_test():
    london=dt.datetime(2026,10,24,19,30,tzinfo=dt.timezone.utc)
    current={"dateISO":"2026-10-24","source_time_precision":"date"}
    yesterday=dict(current,dateISO="2026-10-23")
    tomorrow=dict(current,dateISO="2026-10-25")
    assert source_issued_today(current,london)
    assert not source_issued_today(yesterday,london)
    assert not source_issued_today(tomorrow,london)
    exact=dict(current,source_time_precision="timestamp",source_published_at="2026-10-23T23:30:00Z",dateISO="2026-10-23")
    assert source_issued_today(exact,london), "UK day begins before UTC midnight during BST"
    exact["source_published_at"]="2026-10-25T10:00:00Z"
    assert not source_issued_today(exact,london)
    approved=dict(current,published_at="2026-10-24T18:30:00Z",
                  ai_assisted=True,publication_method="autonomous",editorial_status="PUBLISHED: tested")
    assert published_same_day(approved,london)
    assert published_same_day(dict(approved,dateISO="2026-10-23"),london)
    assert not published_same_day(dict(approved,published_at="2026-10-25T13:00:00Z"),london)
    assert source_recent(yesterday, london)
    assert source_recent(dict(current,dateISO="2026-10-22"), london)
    assert not source_recent(dict(current,dateISO="2026-10-21"), london)
    assert not source_recent(dict(current,dateISO="2026-10-25"), london)
    sourced_yesterday=dict(approved,dateISO="2026-10-23")
    assert published_same_day(sourced_yesterday,london)
    print("PASS: original dates, two-day catch-up, no future articles, honest publication clock")


if __name__=="__main__":
    self_test()

