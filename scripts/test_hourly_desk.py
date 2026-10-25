"""Offline invariants: hourly refresh is not a new story or invented original date."""
import datetime as dt
from hourly_desk import make,page
from zoneinfo import ZoneInfo
now=dt.datetime(2026,10,25,14,20,tzinfo=dt.timezone.utc)
base={"id":"ai-12345678901234567890","title":"Approved insurance development",
"short":"A fully reviewed, original publication with a clear original date.","category":"Insurance",
"source":"Original source","url":"https://example.org/news/source",
"publication_method":"autonomous","editorial_status":"PUBLISHED: machine-screened",
"published_at":"2026-10-24T13:20:00+00:00","dateISO":"2026-10-24"}
historical=make([base],now)
assert historical["mode"]=="DATED_CONTEXT"
assert historical["today_count"]==0 and historical["items"][0]["original_date"]=="2026-10-24"
assert "background, not today's news" in page(historical)
today=dict(base,id="ai-aaaaaaaaaaaaaaaaaaaa",dateISO="2026-10-25",published_at="2026-10-25T09:00:00+00:00")
fresh=make([base,today],now)
assert fresh["mode"]=="TODAY_VERIFIED" and fresh["today_count"]==1
assert len(fresh["items"])==1 and fresh["items"][0]["id"]==today["id"]
assert "2026-10-25" in page(fresh)
print("PASS: hourly desk preserves original dates and clearly labels recycled context")
