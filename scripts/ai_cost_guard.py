"""Request limits and durable accounting. This does not enable provider billing."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import time
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from publication_scope import source_lane

MAX_REQUESTS_PER_RUN=7  # One selection plus at most three writer/reviewer pairs.
MAX_REQUESTS_PER_DAY=30  # Local ceiling, not a claim about Google's project quota.
MAX_SOURCE_CHARS=43000  # Matches the full-capture reader; never truncate a document.
MIN_SOURCE_CHARS=200
PACIFIC=ZoneInfo('America/Los_Angeles')

class BudgetExhausted(RuntimeError):pass

class CallBudget:
    def __init__(self,ledger,now=None,per_run=MAX_REQUESTS_PER_RUN,per_day=MAX_REQUESTS_PER_DAY,path=None,now_fn=None):
        self.ledger=ledger
        self._clock=now_fn or (lambda:dt.datetime.now(dt.timezone.utc))
        self.now=now or self._clock()
        self.today=self.now.astimezone(PACIFIC).date().isoformat()
        old=ledger.get('api_budget',{})
        # Retain old counts conservatively during reset-zone migration.
        prior=old.get('requests',0) if old.get('date')==self.today else 0
        self.daily_used=max(0,int(prior));self.run_used=0
        self.per_run=per_run;self.per_day=per_day;self.path=Path(path) if path else None
        self.last_call=0
        self._sync()
    def _sync(self):
        self.ledger['api_budget']={'date':self.today,'timezone':'America/Los_Angeles','requests':self.daily_used,'limit':self.per_day}
        if self.path:
            temp=self.path.with_suffix('.tmp')
            temp.write_text(json.dumps(self.ledger,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
            temp.replace(self.path)
    def remaining(self):return max(0,min(self.per_run-self.run_used,self.per_day-self.daily_used))
    def call(self,fn,prompt,*,diagnostic=False,purpose='production'):
        if self.path:
            quota_day=self._clock().astimezone(PACIFIC).date().isoformat()
            if quota_day!=self.today:
                self.today=quota_day;self.daily_used=0;self._sync()
        if diagnostic:
            allowance=self.ledger.setdefault('launch_diagnostic_allowance',{'limit':2,'requests':0})
            if allowance['requests']>=2 or self.run_used>=self.per_run:
                raise BudgetExhausted('One-time two-request launch diagnostic allowance exhausted')
            allowance['requests']+=1
        elif not self.remaining():raise BudgetExhausted('Daily/run AI request cap reached')
        if self.path:
            # One serial workflow, conservatively below common free RPM limits.
            delay=15-(time.monotonic()-self.last_call)
            if delay>0:time.sleep(delay)
        self.daily_used+=1;self.run_used+=1
        journal=self.ledger.setdefault('api_calls',[])
        entry={'at':dt.datetime.now(dt.timezone.utc).isoformat(),'result':'reserved','prompt_characters':len(prompt),'purpose':'one-time launch diagnostic' if diagnostic else purpose}
        journal.append(entry);self.ledger['api_calls']=journal[-100:]
        self._sync()  # reservation survives an exception or interrupted call
        self.last_call=time.monotonic()
        try:
            result=fn(prompt)
            entry['result']='response_received'
            if isinstance(result,dict):entry['usage']=result.pop('_brief_usage',{})
            return result
        except Exception as error:
            entry['result']='failed';entry['error_type']=type(error).__name__
            raise
        finally:self._sync()
    def snapshot(self):
        return {'quota_date':self.today,'quota_timezone':'America/Los_Angeles','requests_this_run':self.run_used,
                'requests_today_including_this_run':self.daily_used,'run_limit':self.per_run,'daily_limit':self.per_day,
                'remaining_today':max(0,self.per_day-self.daily_used)}

def preflight_source(item,doc):
    if not source_lane(item.get('url','')):raise ValueError('Not a permitted original publication category')
    if item.get('category') not in {'Banking','Insurance','Technology','Regulation','Pensions','Brokers','Wealth'}:raise ValueError('Unsupported financial-services category')
    if not doc.complete_capture or doc.notes:raise ValueError('Official source is incomplete or has unresolved attachments')
    if not MIN_SOURCE_CHARS<=len(doc.text)<=MAX_SOURCE_CHARS:raise ValueError('Source length outside full-reading limits')
    if doc.url!=item.get('url') or not doc.document_urls or doc.document_urls[0]!=doc.url:raise ValueError('Source redirected; provenance must be re-established')
    if doc.extraction=='HTML main content' and doc.document_urls==[doc.url]:return True
    if doc.extraction=='complete HTML and linked official PDF' and len(doc.document_urls)==2 and urlsplit(doc.document_urls[1]).path.lower().endswith('.pdf'):return True
    raise ValueError('Unsupported source capture')

def self_test():
    import tempfile
    # Pacific reset is distinct from UTC and UK midnight.
    t=dt.datetime(2026,10,25,1,tzinfo=dt.timezone.utc);ledger={}
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'ledger.json'
        m=CallBudget(ledger,t,per_run=2,per_day=3,path=path,now_fn=lambda:t)
        assert m.today=='2026-10-24'
        assert m.call(lambda p:p,'ok')=='ok'
        m.last_call=0
        try:m.call(lambda p:(_ for _ in ()).throw(RuntimeError('failed')),'fail')
        except RuntimeError:pass
        assert json.loads(path.read_text())['api_budget']['requests']==2
        assert m.remaining()==0
        assert CallBudget(ledger,t,per_run=2,per_day=3).remaining()==1
        assert CallBudget(ledger,t+dt.timedelta(hours=8),per_run=2,per_day=3).remaining()==2
    print('PASS: durable reservations, failure accounting, hard caps and Pacific reset')
if __name__=='__main__':self_test()


