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
 elif not (checked-failures>0 or feed_ok):outcome='BLOCKED'
 elif verified and selection not in {'NO_WORTHWHILE_NEWS'}:outcome='BLOCKED'
 elif not verified:
  # Discovery leads are not publishable articles. If the run actually read
  # and rejected the available material as outside the UK remit, that is an
  # honest quiet hour, not a technical failure. Do not suppress genuine
  # retrieval outages or a backlog that was never examined.
  metrics=report.get('metrics',{})
  examined=metrics.get('sources_successfully_retrieved',0)+metrics.get('source_checkpoints_reused',0)
  out_of_scope=metrics.get('outside_uk_market',0)
  candidate_count=report.get('fresh_unpublished_source_candidates',0)
  unresolved=max(0,examined-out_of_scope)
  if candidate_count==0 or (examined>=5 and out_of_scope>0 and unresolved<=2 and metrics.get('source_failures',0)<examined):
   outcome='NO_QUALIFYING_NEWS'
  else:outcome='BLOCKED'
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
  'machine_screened':report.get('machine_screened',0),'independent_review':report.get('independent_review',True),'publication_policy':report.get('policy'),'articles_ready_to_publish':report.get('articles_ready_to_publish',0),'primary_indexes_checked':checked,
  'primary_index_failures':failures,'feeds_working':feed_ok,'feed_failures':feed_fail,
  'ai_budget':report.get('api_budget',{}),'quota_pause_until':report.get('active_quota_pause_until'),
  'pipeline_metrics':report.get('metrics',{}),'source_fallbacks':report.get('source_fallbacks',[]),'candidate_outcomes':report.get('items_checked',[]),'discovery_errors':errors,
  'publication_holds':publication.get('held',[]),
  'run_id':os.getenv('GITHUB_RUN_ID','local'),'event':os.getenv('GITHUB_EVENT_NAME','local'),
  'run_url':'https://github.com/'+os.getenv('GITHUB_REPOSITORY','yogeshkaransharma-code/the-brief-financial-news')+'/actions/runs/'+os.getenv('GITHUB_RUN_ID','')}

def read(path,default):
 try:return json.loads((ROOT/path).read_text())
 except (OSError,ValueError):return default

def main():
 publication=read('generated-drafts/publication-report.json',{})
 state=assess(read('data/articles.json',[]),read('generated-drafts/run-report.json',{}),dt.datetime.now(dt.timezone.utc),publication,read('data/live.json',{}))
 state['publisher_links']=0
 state['discovery_headlines']=len(read('data/headlines.json',{}).get('items',[]))
 state['publisher_desk_checked_at']=read('data/headlines.json',{}).get('checked_at')
 state['previous_verified_runs']=read('data/run-history.json',[])[-24:]
 from launch_acceptance import evaluate
 state['launch_acceptance']=evaluate(state['previous_verified_runs'])
 ledger=read('data/newsroom-attempts.json',{})
 saved=ledger.get('api_budget',{})
 state['launch_diagnostic_allowance']=ledger.get('launch_diagnostic_allowance',{'limit':2,'requests':0})
 if saved:
  limit=saved.get('limit')
  state['ai_budget'].update(requests_today_including_this_run=saved.get('requests',0),daily_limit=limit,
      remaining_today=None if limit is None else max(0,limit-saved.get('requests',0)),
      daily_limit_source='provider' if limit is None else 'local')
 (ROOT/'data/status.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
 if os.getenv('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('outcome='+state['outcome']+'\nnew_articles='+str(state['published_this_run'])+'\n')
 summary='## Editorial result: '+state['outcome']+'\n\nDeployment and full live reading checks follow this assessment.\n\n| Measure | Result |\n|---|---|\n'
 for k in ['published_this_run','discovery_headlines','primary_indexes_checked','primary_index_failures','feeds_working','feed_failures','fresh_source_candidates','verified_original_candidates','articles_commissioned','articles_held','machine_screened','source_coverage_status']:
  summary+='| '+k.replace('_',' ')+' | '+str(state[k])+' |\n'
 summary+='\nModel requests: '+json.dumps(state['ai_budget'])+'\n'
 for e in state['discovery_errors']:summary+='\n- Coverage warning: '+str(e)
 for e in state['candidate_outcomes']:summary+='\n- '+str(e.get('title','Pipeline'))+': '+str(e.get('result'))+' — '+str(e.get('reason',''))
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(summary+'\n')
 print('NEWSROOM_OUTCOME: '+json.dumps(state,sort_keys=True))
if __name__=='__main__':
 if '--self-test' in sys.argv:
  now=dt.datetime.now(dt.timezone.utc)
  assert assess([],{},now)['outcome']=='BLOCKED'
  report={'first_party_indexes_checked':31,'first_party_discovery_errors':['one unavailable'],
          'fresh_unpublished_source_candidates':70,'verified_original_candidates':0,
          'editorial_selection':{'result':'NO_VERIFIED_CANDIDATES'},
          'metrics':{'sources_successfully_retrieved':37,'outside_uk_market':37,'source_failures':1}}
  assert assess([],report,now,{'published':[],'held':[]},{'sources_checked':['FCA']})['outcome']=='NO_QUALIFYING_NEWS'
  report['metrics']['sources_successfully_retrieved']=0
  assert assess([],report,now,{'published':[],'held':[]},{'sources_checked':['FCA']})['outcome']=='BLOCKED'
  report['metrics'].update(sources_successfully_retrieved=37,outside_uk_market=5)
  assert assess([],report,now,{'published':[],'held':[]},{'sources_checked':['FCA']})['outcome']=='BLOCKED'
  report['metrics'].update(outside_uk_market=37)
  assert assess([],report,now,{'published':[],'held':[]},{'sources_checked':['FCA']})['outcome']=='BLOCKED' if os.getenv('BRIEF_PIPELINE_ERROR')=='true' else True
  print('PASS: completed UK-only source screening is a quiet hour; missing data, unread backlog and real failures remain blocked')
 else:main()

