"""Durable operational outcome. Deployment success is not publication success."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys
from same_day_policy import published_same_day,clock
ROOT=Path(__file__).resolve().parents[1]

def assess(articles,report,now,publication=None,feeds=None):
    publication=publication or {};feeds=feeds or {}
    new=len(publication.get('published',[]))
    checked=report.get('first_party_indexes_checked',0)
    failures=len(report.get('first_party_discovery_errors',[]))
    feed_ok=len(feeds.get('sources_checked',[]));feed_fail=len(feeds.get('errors',[]))
    if not report or not publication or os.getenv('BRIEF_PIPELINE_ERROR')=='true':outcome='BLOCKED'
    elif new:outcome='PUBLISHED'
    elif report.get('fresh_unpublished_source_candidates',0):outcome='BLOCKED'
    elif failures or feed_fail:outcome='DEGRADED'
    elif not checked or not feed_ok:outcome='BLOCKED'
    else:outcome='NO_QUALIFYING_NEWS'
    return {'checked_at':now.isoformat(),'uk_date':clock(now).date().isoformat(),'outcome':outcome,
      'published_this_run':new,'genuine_same_day_articles':sum(published_same_day(a,now) for a in articles),
      'published_total':len(articles),'last_article_at':max((a['published_at'] for a in articles),default=None),
      'fresh_source_candidates':report.get('fresh_unpublished_source_candidates',0),
      'machine_screened':report.get('machine_screened',0),'primary_indexes_checked':checked,
      'primary_index_failures':failures,'feeds_working':feed_ok,'feed_failures':feed_fail,
      'ai_budget':report.get('api_budget',{}),'quota_pause_until':report.get('active_quota_pause_until'),
      'candidate_outcomes':report.get('items_checked',[]),'discovery_errors':report.get('first_party_discovery_errors',[])+feeds.get('errors',[]),
      'publication_holds':publication.get('held',[]),
      'run_url':'https://github.com/'+os.getenv('GITHUB_REPOSITORY','yogeshkaransharma-code/the-brief-financial-news')+'/actions/runs/'+os.getenv('GITHUB_RUN_ID','')}

def read(path,default):
    try:return json.loads((ROOT/path).read_text())
    except (OSError,ValueError):return default

def main():
    state=assess(read('data/articles.json',[]),read('generated-drafts/run-report.json',{}),dt.datetime.now(dt.timezone.utc),read('generated-drafts/publication-report.json',{}),read('data/live.json',{}))
    state['launch_test']=read('data/launch-test.json',{'result':'NOT_RUN'})
    ledger=read('data/newsroom-attempts.json',{})
    saved_budget=ledger.get('api_budget',{})
    state['launch_diagnostic_allowance']=ledger.get('launch_diagnostic_allowance',{'limit':2,'requests':0})
    if saved_budget:
        state['ai_budget'].update(requests_today_including_this_run=saved_budget.get('requests',0),daily_limit=saved_budget.get('limit',20),remaining_today=max(0,saved_budget.get('limit',20)-saved_budget.get('requests',0)))
    from zoneinfo import ZoneInfo
    quota_day=saved_budget.get('date')
    diagnostic_today=0
    for call in ledger.get('api_calls',[]):
        if call.get('purpose')!='one-time launch diagnostic':continue
        try:
            day=dt.datetime.fromisoformat(call['at']).astimezone(ZoneInfo('America/Los_Angeles')).date().isoformat()
            if day==quota_day:diagnostic_today+=1
        except (ValueError,KeyError):pass
    state['ai_budget']['diagnostic_requests_today']=diagnostic_today
    state['ai_budget']['production_requests_today']=max(0,saved_budget.get('requests',0)-diagnostic_today)
    if state['launch_test'].get('run_id')==os.getenv('GITHUB_RUN_ID','local'):
        state['ai_budget']['requests_this_run']=state['ai_budget'].get('requests_this_run',0)+state['launch_test'].get('requests_this_attempt',0)
    (ROOT/'data/status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    out=os.getenv('GITHUB_OUTPUT')
    if out:
        with open(out,'a') as f:f.write('outcome='+state['outcome']+'\nnew_articles='+str(state['published_this_run'])+'\n')
    summary='## Newsroom result: '+state['outcome']+'\n\nNew articles actually published: **'+str(state['published_this_run'])+'**. Today’s edition: **'+str(state['genuine_same_day_articles'])+'**.\n\n'
    summary+='| Measure | Result |\n|---|---|\n'
    for k in ['primary_indexes_checked','primary_index_failures','feeds_working','feed_failures','fresh_source_candidates','machine_screened','last_article_at']:
        summary+='| '+k.replace('_',' ')+' | '+str(state[k])+' |\n'
    summary+='\nUnpublished real-model test: **'+state['launch_test'].get('result','NOT_RUN')+'**. This never counts as publication.\n'
    summary+='\nNo new article means no successful news publication. Discovery gaps mean coverage is incomplete, not proof nothing happened.\n'
    for e in state['discovery_errors']:summary+='\n- Discovery issue: '+str(e)
    for e in state['candidate_outcomes']:summary+='\n- '+str(e.get('title','Pipeline'))+': '+str(e.get('result'))+' — '+str(e.get('reason',''))
    path=os.getenv('GITHUB_STEP_SUMMARY')
    if path:
        with open(path,'a') as f:f.write(summary+'\n')
    print('NEWSROOM_OUTCOME: '+json.dumps(state,sort_keys=True))

if __name__=='__main__':
    if '--self-test' in sys.argv:
        n=dt.datetime(2026,10,25,tzinfo=dt.timezone.utc)
        assert assess([],{},n)['outcome']=='BLOCKED'
        print('PASS: missing run evidence cannot become publication success')
    else:main()
