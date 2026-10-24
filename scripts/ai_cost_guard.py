#!/usr/bin/env python3
"""Hard-bound AI spending for the unattended financial news desk.

No AI is needed to inspect a headline, URL, date or full primary document.
The ledger is retained in GitHub between runs. Provider billing quotas remain
the final protection: concurrent/failed GitHub writes cannot guarantee exact
dollar or token limits.
"""
from __future__ import annotations
import datetime as dt
from urllib.parse import urlsplit
from publication_scope import source_lane

MAX_REQUESTS_PER_RUN = 6
MAX_REQUESTS_PER_DAY = 16
MAX_SOURCE_CHARS = 30000
MIN_SOURCE_CHARS = 1250

class BudgetExhausted(RuntimeError):
    pass

class CallBudget:
    def __init__(self, ledger, now=None, per_run=MAX_REQUESTS_PER_RUN, per_day=MAX_REQUESTS_PER_DAY):
        self.ledger=ledger
        self.now=now or dt.datetime.now(dt.timezone.utc)
        self.today=self.now.astimezone(dt.timezone.utc).date().isoformat()
        old=ledger.get("api_budget",{})
        prior=old.get("requests",0) if old.get("date")==self.today else 0
        self.daily_used=max(0,int(prior))
        self.run_used=0
        self.per_run=per_run
        self.per_day=per_day
        self._sync()

    def _sync(self):
        self.ledger["api_budget"]={"date":self.today,"requests":self.daily_used,
                                   "limit":self.per_day}

    def remaining(self):
        return max(0,min(self.per_run-self.run_used,self.per_day-self.daily_used))

    def call(self,fn,prompt):
        if self.remaining()<=0:
            raise BudgetExhausted("AI request budget reached; no additional API calls allowed")
        # Count before requesting: failed calls may still be billed by a provider.
        self.daily_used+=1
        self.run_used+=1
        self._sync()
        return fn(prompt)

    def snapshot(self):
        return {"today_utc":self.today,"requests_this_run":self.run_used,
                "requests_today_including_this_run":self.daily_used,
                "run_limit":self.per_run,"daily_limit":self.per_day,
                "remaining_today":max(0,self.per_day-self.daily_used)}

def preflight_source(item,doc):
    """Fail before the paid writer if a primary source could never auto-publish."""
    lane=source_lane(item.get("url",""))
    if not lane:
        raise ValueError("Not a permitted official publication category")
    if item.get("category") not in {"Banking","Insurance","Technology","Regulation"}:
        raise ValueError("Not a supported financial-services category")
    if not doc.complete_capture:
        raise ValueError("Official source is incomplete")
    if doc.notes:
        raise ValueError("Official source has unresolved document or appendix warnings")
    if len(doc.text)<MIN_SOURCE_CHARS:
        raise ValueError("Official source too thin for evidence-backed automated article")
    if len(doc.text)>MAX_SOURCE_CHARS:
        raise ValueError("Full official source too long for cost-bounded verification")
    docs=doc.document_urls
    if doc.url != item.get("url") or not docs or docs[0]!=doc.url:
        raise ValueError("Official source redirected or has uncertain provenance")
    if doc.extraction=="HTML main content" and docs==[doc.url]:
        return True
    if (doc.extraction=="complete HTML and linked official PDF" and
            len(docs)==2 and docs[0]==doc.url and
            urlsplit(docs[1]).path.lower().endswith(".pdf")):
        return True
    raise ValueError("Original source cannot pass the autonomous document gate")

def self_test():
    from types import SimpleNamespace
    t=dt.datetime(2026,10,24,10,tzinfo=dt.timezone.utc)
    ledger={}
    m=CallBudget(ledger,t,per_run=2,per_day=3)
    assert m.remaining()==2
    assert m.call(lambda p:{"ok":p},"first")=={"ok":"first"}
    assert m.call(lambda p:{"ok":p},"second")=={"ok":"second"}
    assert m.remaining()==0
    try:
        m.call(lambda p:{"ok":p},"third")
    except BudgetExhausted:
        pass
    else:
        raise AssertionError("Third request must be blocked")
    other=CallBudget(ledger,t,per_run=2,per_day=3)
    assert other.remaining()==1
    other.call(lambda p:p,"last")
    assert CallBudget(ledger,t).remaining()==0
    assert CallBudget(ledger,t+dt.timedelta(days=1)).remaining()==6
    u="https://www.fca.org.uk/news/press-releases/fca-releases-banking-data"
    doc=SimpleNamespace(url=u,document_urls=[u],text="Verified official information. "*85,
         complete_capture=True,notes=[],extraction="HTML main content")
    assert preflight_source({"url":u,"category":"Banking"},doc)
    doc.notes=["Unknown linked source"]
    try:preflight_source({"url":u,"category":"Banking"},doc)
    except ValueError:pass
    else:raise AssertionError("Complex source must not burn AI tokens")
    print("PASS: one-pass API request budget, UTC daily reset and free source preflight")

if __name__=="__main__":
    self_test()
