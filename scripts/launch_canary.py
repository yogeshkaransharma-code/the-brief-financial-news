"""Real Gemini launch test, strictly isolated from the public news feed.

An old, verifiably dated primary release tests writing and review. It must be
rejected by the unchanged same-day publication gate. No fixture is published,
no date is refreshed, and two requests are reserved within existing limits.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from ai_cost_guard import CallBudget,MAX_REQUESTS_PER_RUN
from model_providers import fetch_ai,ACTIVE_MODEL
from newsroom_v2 import draft_with_source_repair,review_until_resolved,next_quota_check
from source_retrieval import read_source
from ai_cost_guard import preflight_source
from same_day_policy import clock,original_date
from publish_autonomous import eligible
from ai_newsroom import GeminiAPIError

ROOT=Path(__file__).resolve().parents[1]
VERSION=1
# Previously inspected public FCA release. Its actual publication date is
# recovered from the document; the date of this test never replaces it.
SOURCE='https://www.fca.org.uk/news/press-releases/fca-calls-private-market-firms-manage-conflicts-interest-line-rapid-growth'


def exercise(item,doc,ai):
    article=draft_with_source_repair(item,doc,gemini=ai)
    bundle,passed=review_until_resolved(item,doc,article,gemini=ai)
    reasons=eligible(bundle)
    date_rejected=any('not from TODAY' in reason for reason in reasons)
    if passed and not date_rejected:
        raise ValueError('Canary did not demonstrate stale-source rejection; no publication attempted')
    return bundle,{'result':'PASSED' if passed else 'HELD',
        'writer_and_review_passed':passed,'old_source_publication_rejected':date_rejected,
        'reviewed_sentences':bundle['audit']['sentence_review']['reviewed'],
        'editorial_flags':bundle.get('editorial_flags',[]),'publication_gate_holds':reasons}


def save_report(root,report):
    path=root/'data/launch-test.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    out=root/'generated-drafts/canary';out.mkdir(parents=True,exist_ok=True)
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('UNPUBLISHED_LAUNCH_TEST: '+json.dumps(report,sort_keys=True))
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write('\n## Unpublished real-model launch test: '+report['result']+'\n\n')
            f.write('This test does not publish an article or refresh an old source date.\n\n')
            f.write('Requests this attempt: '+str(report.get('requests_this_attempt',0))+'\n\n')
            if report.get('reason'):f.write(report['reason']+'\n')


def run(root=ROOT,diagnostic=False):
    root=Path(root);now=dt.datetime.now(dt.timezone.utc)
    ledger_path=root/'data/newsroom-attempts.json'
    ledger=json.loads(ledger_path.read_text())
    previous=ledger.get('launch_test',{})
    if previous.get('version')==VERSION and previous.get('result')=='PASSED':
        print('Real-model launch test already passed; zero extra requests');return previous
    try:production=json.loads((root/'generated-drafts/publication-report.json').read_text())
    except (OSError,ValueError):production={}
    if production.get('published'):
        result={'version':VERSION,'result':'SUPERSEDED_BY_REAL_PUBLICATION','checked_at':now.isoformat(),'requests_this_attempt':0}
        save_report(root,result);return result
    try:writer_report=json.loads((root/'generated-drafts/run-report.json').read_text())
    except (OSError,ValueError):writer_report={}
    writer_used=writer_report.get('api_budget',{}).get('requests_this_run',0)
    meter=CallBudget(ledger,now,per_run=max(0,min(2,MAX_REQUESTS_PER_RUN-int(writer_used))),path=ledger_path)
    report={'version':VERSION,'result':'WAITING','checked_at':now.isoformat(),'model':ACTIVE_MODEL,
            'source_url':SOURCE,'requests_this_attempt':0,'published_articles':0,'unpublished_test':True,'run_id':os.getenv('GITHUB_RUN_ID','local')}
    quota_day=meter.today
    # One attempt per quota day/version. Held drafts do not trigger an hourly
    # rewrite loop. A code/version change is needed to retry a semantic failure.
    if previous.get('version')==VERSION and previous.get('result') in {'STARTED','FAILED','HELD'}:
        print('Launch test already attempted this quota day; no repeated model calls');return previous
    pause=ledger.get('quota_pause_until')
    try:paused=pause and dt.datetime.fromisoformat(pause)>now
    except (TypeError,ValueError):paused=False
    allowance=ledger.get('launch_diagnostic_allowance',{'requests':0})
    diagnostic_available=diagnostic and 2-int(allowance.get('requests',0))>=2 and meter.per_run>=2
    if (meter.remaining()<2 and not diagnostic_available) or paused:
        local=now.astimezone(ZoneInfo('America/Los_Angeles'))
        next_reset=dt.datetime.combine(local.date()+dt.timedelta(days=1),dt.time(0,5),local.tzinfo)
        report.update(reason='Waiting for existing request allowance or provider cooldown; no cap reset or model request',next_quota_reset_utc=next_reset.astimezone(dt.timezone.utc).isoformat())
        save_report(root,report);return report
    stage='source'
    try:
        doc=read_source(SOURCE)
        if not doc.publication_date:raise ValueError('Original source publication date is ambiguous')
        day,stamp,precision=doc.publication_date
        item={'url':doc.url,'title':'FCA calls on private market firms to manage conflicts of interest in line with rapid growth',
              'source':'Financial Conduct Authority','category':'Regulation','dateISO':day,
              'source_published_at':stamp,'published_at':stamp,'source_time_precision':precision,
              'date_evidence':{'url':doc.url,'value':stamp,'precision':precision,'method':'original-document metadata; unpublished test'}}
        if original_date(item)>=clock(now).date():raise ValueError('Canary requires a genuinely historical source; no date substitutions')
        preflight_source(item,doc)
        stage='model'
        report.update(quota_date=quota_day,original_source_date=day,one_time_diagnostic=diagnostic)
        # Persist before the first network request, including a possible crash.
        ledger['launch_test']={**report,'result':'STARTED'};meter._sync()
        bundle,outcome=exercise(item,doc,lambda prompt:meter.call(fetch_ai,prompt,diagnostic=diagnostic))
        report.update(outcome)
        out=root/'generated-drafts/canary';out.mkdir(parents=True,exist_ok=True)
        (out/'UNPUBLISHED-bundle.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
    except Exception as error:
        report.update(result='FAILED',stage=stage,reason=str(error)[:600])
        if isinstance(error,GeminiAPIError):
            until=next_quota_check('daily limit' if error.daily else str(error),now)
            if error.retry_seconds and not error.daily:until=now+dt.timedelta(seconds=max(60,min(error.retry_seconds,86400)))
            ledger['quota_pause_until']=until.isoformat()
    report['requests_this_attempt']=meter.run_used
    report['api_budget']=meter.snapshot()
    # A source-only error consumes no AI requests and may retry next run.
    if meter.run_used or report['result']=='PASSED':ledger['launch_test']=report
    meter._sync();save_report(root,report)
    return report

if __name__=='__main__':run(diagnostic=os.getenv('BRIEF_LAUNCH_DIAGNOSTIC')=='1')
