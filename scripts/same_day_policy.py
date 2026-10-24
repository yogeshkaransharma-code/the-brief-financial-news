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
        raw=item.get("source_published_at") or item.get("published_at")
        if not raw:
            raise ValueError("Missing original source timestamp")
        day=date_in_uk(raw)
        # A source-reported date may be its local date or UTC date at midnight.
        source_date=dt.date.fromisoformat(str(item["dateISO"])[:10])
        if abs((day-source_date).days)>1:
            raise ValueError("Source timestamp and source calendar date disagree")
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


def published_same_day(item, now=None):
    """Only properly approved articles from TODAY'S actual source-day appear."""
    try:
        uk_pub=date_in_uk(item["published_at"])
        return (uk_pub==clock(now).date()
                and original_date(item)==uk_pub
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
    assert not published_same_day(dict(approved,dateISO="2026-10-23"),london)
    assert not published_same_day(dict(approved,published_at="2026-10-25T13:00:00Z"),london)
    print("PASS: strict same-calendar-day UK original source and approval clock")


if __name__=="__main__":
    self_test()
