"""Report editorial output separately from source coverage and deployment evidence."""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import sys
from same_day_policy import published_same_day,clock
ROOT=Path(__file__).resolve().parents[1]

def assess(articles,report,now,publication=None,feeds=None,launch=None):
 publication=publication or {};feeds=feeds or {}
 new=len(publication.get('published',[]))
 checked=report.get('first_party_indexes_checked',0)
 failures=len(report.get('first_party_discovery_errors',[]))
 feed_ok=len(feeds.get('sources_checked',[]));feed_fail=len(feeds.get('errors',[]))
 selection=report.get('editorial_selection',{}).get('result')
 verified=report.get('verified_original_candidates',report.get('fresh_unpublished_source_candidates',0))
 pipeline_error=os.getenv('BRIEF_PIPELINE_ERROR')=='true'
 # A single inaccessible publisher is a coverage warning. Total discovery,
 # model execution, missing reports and deployment failures remain actionable.
 if not report or not publication or pipeline_error:outcome='BLOCKED'
 elif selection in {'BLOCKED','BUDGET_PAUSED'} or report.get('active_quota_pause_until'):outcome='BLOCKED'
 elif new:outcome='PUBLISHED'
 elif verified and selection not in {'NO_WORTHWHILE_NEWS'}:outcome='BLOCKED'
 elif not (checked-failures>0 or feed_ok):outcome='BLOCKED'
 else:outcome='NO_QUALIFYING_NEWS'
 if not new and (launch or {}).get('result') in {'FAILED','HELD','STARTED'}:outcome='BLOCKED'
 errors=report.get('first_party_discovery_errors',[])+feeds.get('errors',[])
 return {'checked_at':now.isoformat(),'uk_date':clock(now).date().isoformat(),
  'outcome':outcome,'editorial_outcome':outcome,'technical_status':'AWAITING_LIVE_VERIFICATION',
  'source_coverage_status':'PARTIAL' if errors else 'COMPLETE','launch_test':launch or {'result':'NOT_RUN'},
  'published_this_run':new,'genuine_same_day_articles':sum(published_same_day(a,now) for a in articles),
  'editorial_selection':report.get('editorial_selection',{'result':'NOT_RECORDED'}),
  'published_total':len(articles),'last_article_at':max((a['published_at'] for a in articles),default=None),
  'fresh_source_candidates':report.get('fresh_unpublished_source_candidates',0),
  'verified_original_candidates':report.get('verified_original_candidates',0),
  'candidates_by_sector':report.get('candidates_by_sector',{}),'verified_by_sector':report.get('verified_by_sector',{}),
  'articles_commissioned':len(report.get('editorial_selection',{}).get('selected',[])),
  'articles_held':len(publication.get('held',[]))+sum(x.get('result') in {'held for review','held back'} for x in report.get('items_checked',[])),
  'machine_screened':report.get('machine_screened',0),'primary_indexes_checked':checked,
  'primary_index_failures':failures,'feeds_working':feed_ok,'feed_failures':feed_fail,
  'ai_budget':report.get('api_budget',{}),'quota_pause_until':report.get('active_quota_pause_until'),
  'candidate_outcomes':report.get('items_checked',[]),'discovery_errors':errors,
  'publication_holds':publication.get('held',[]),
  'run_id':os.getenv('GITHUB_RUN_ID','local'),'event':os.getenv('GITHUB_EVENT_NAME','local'),
  'run_url':'https://github.com/'+os.getenv('GITHUB_REPOSITORY','yogeshkaransharma-code/the-brief-financial-news')+'/actions/runs/'+os.getenv('GITHUB_RUN_ID','')}

def read(path,default):
 try:return json.loads((ROOT/path).read_text())
 except (OSError,ValueError):return default

def main():
 publication=read('generated-drafts/publication-report.json',{})
 state=assess(read('data/articles.json',[]),read('generated-drafts/run-report.json',{}),dt.datetime.now(dt.timezone.utc),publication,read('data/live.json',{}))
 state['publisher_links']=len(read('data/headlines.json',{}).get('items',[]))
 state['publisher_desk_checked_at']=read('data/headlines.json',{}).get('checked_at')
 state['previous_verified_runs']=read('data/run-history.json',[])[-24:]
 from launch_acceptance import evaluate
 state['launch_acceptance']=evaluate(state['previous_verified_runs'])
 ledger=read('data/newsroom-attempts.json',{})
 saved=ledger.get('api_budget',{})
 state['launch_diagnostic_allowance']=ledger.get('launch_diagnostic_allowance',{'limit':2,'requests':0})
 if saved:state['ai_budget'].update(requests_today_including_this_run=saved.get('requests',0),daily_limit=saved.get('limit',30),remaining_today=max(0,saved.get('limit',30)-saved.get('requests',0)))
 (ROOT/'data/status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 if os.getenv('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('outcome='+state['outcome']+'\nnew_articles='+str(state['published_this_run'])+'\n')
 summary='## Editorial result: '+state['outcome']+'\n\nDeployment and full live reading checks follow this assessment.\n\n| Measure | Result |\n|---|---|\n'
 for k in ['published_this_run','publisher_links','primary_indexes_checked','primary_index_failures','feeds_working','feed_failures','fresh_source_candidates','verified_original_candidates','articles_commissioned','articles_held','machine_screened','source_coverage_status']:
  summary+='| '+k.replace('_',' ')+' | '+str(state[k])+' |\n'
 summary+='\nModel requests: '+json.dumps(state['ai_budget'])+'\n'
 for e in state['discovery_errors']:summary+='\n- Coverage warning: '+str(e)
 for e in state['candidate_outcomes']:summary+='\n- '+str(e.get('title','Pipeline'))+': '+str(e.get('result'))+' — '+str(e.get('reason',''))
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary+'\n')
 print('NEWSROOM_OUTCOME: '+json.dumps(state,sort_keys=True))
if __name__=='__main__':
 if '--self-test' in sys.argv:
  assert assess([],{},dt.datetime.now(dt.timezone.utc))['outcome']=='BLOCKED'
  print('PASS: missing run evidence is blocked')
 else:main()
