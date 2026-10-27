"""Offline public-index leads -> actual source -> one writing request -> publisher."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from linkedin_discovery import discover,post_url,candidate
from newsroom_state import atomic_json
from newsroom_runtime import run
from source_retrieval import read_source
from publish_autonomous import publish
from same_day_policy import clock

POST='https://www.linkedin.com/posts/aviva_insurance-distribution-partnership-activity-123456789/'
SOURCE='https://www.aviva.com/newsroom/news-and-research-overview/news-releases/2026/10/distribution-agreement/'
TITLE='Aviva expands commercial insurance distribution partnership'
CONFIG={'linkedin_discovery':{'enabled':True,'max_queries_per_run':4,'max_resolutions_per_run':4,
 'queries':[{'id':'insurance','desk':'Insurance','terms':'UK insurance partnerships'}]}}

def main():
 now=dt.datetime.now(dt.timezone.utc);day=clock(now).date().isoformat()
 assert post_url(POST+'?tracking=x')==POST.rstrip('/')
 for value in ['https://linkedin.com.evil/posts/aaaaaaaaaaa','https://www.linkedin.com/in/some-person','http://www.linkedin.com/posts/aaaaaaaaaaaa','https://user@linkedin.com/posts/aaaaaaaaaaa']:
  assert post_url(value) is None,value
 calls=[]
 def search(query):
  calls.append(query)
  if query.startswith('site:'):
   return [{'title':TITLE+' | LinkedIn','url':POST,'date':'1999-01-01'},
           {'title':'Ignore a profile','url':'https://www.linkedin.com/in/broker'}]
  return [{'title':TITLE,'url':SOURCE,'published_at':'2099-01-01'},
          {'title':TITLE,'url':'https://example.org/unregistered-article'}]
 with tempfile.TemporaryDirectory() as folder:
  root=Path(folder);atomic_json(root/'data/source-registry.json',CONFIG)
  items,report=discover(root,now,search=search)
  assert len(items)==1 and report['linkedin_posts_found']==1 and len(calls)==2
  item=items[0]
  assert item['dateISO']=='' and item['published_at']=='' and item['source_time_precision']=='unknown'
  assert item['source_date_unresolved'] and item['discovered_via']==[POST.rstrip('/')]
  again,report=discover(root,now+dt.timedelta(minutes=20),search=search)
  assert again==items and len(calls)==2 and report['queries_checked']==0
  cfg=copy.deepcopy(CONFIG);cfg['linkedin_discovery']['queries'].append({'id':'broken','desk':'Banking','terms':'broken query'})
  atomic_json(root/'data/source-registry.json',cfg)
  def one_failure(query):
   if 'broken' in query:raise TimeoutError('search temporarily unavailable')
   return search(query)
  results,report=discover(root,now+dt.timedelta(hours=1),search=one_failure)
  assert len(results)==1 and report['queries_failed']==1 and report['queries_checked']==2
  assert report['coverage_status']=='PARTIAL_PUBLIC_INDEX'
  assert not candidate({'title':TITLE,'desk':'Insurance','url':POST},{'title':'Unrelated investment research','url':SOURCE})
 # Missing configuration must not introduce network into old offline fixtures.
 with tempfile.TemporaryDirectory() as folder:
  assert discover(Path(folder),now,search=lambda q:(_ for _ in ()).throw(AssertionError('Unexpected HTTP')))[0]==[]
 # Feed-like dates from search never reach publishing. The actual source decides.
 raw=(Path(__file__).parent/'fixtures/insurer-release.html').read_text().replace('__DATE__',day).encode()
 with patch('source_retrieval.retrieve_bytes',return_value=(raw,'text/html',SOURCE)):
  doc=read_source(SOURCE)
 reads=[];requests=[]
 def reader(url):reads.append(url);return copy.deepcopy(doc)
 def ai(prompt):
  requests.append(prompt)
  packets=json.loads(prompt.split('SOURCE PACKETS:\n')[1])
  assert len(packets)==1 and packets[0]['date']==day and packets[0]['source_text']==doc.text
  assert POST not in prompt
  return {'articles':[{'id':'N01','article':{'headline':TITLE,'sections':[{'heading':'The agreement','text':'Aviva says its insurance distribution agreement serves eligible commercial customers through its established broker channels.'}]}}]}
 kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=reader,ai=ai,
             search=lambda *a,**k:[],linkedin=lambda *a:([copy.deepcopy(item)],{'enabled':True}))
 with tempfile.TemporaryDirectory() as folder,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(folder);atomic_json(root/'data/articles.json',[])
  report=run(root,now,**kwargs)
  assert report['undated_source_candidates']==1 and report['fresh_unpublished_source_candidates']==0
  assert report['linkedin_discovery']['sources_retrieved_and_current']==1
  assert report['articles_ready_to_publish']==1 and len(reads)==1 and len(requests)==1
  report=run(root,now+dt.timedelta(minutes=1),**kwargs)
  assert len(reads)==1 and len(requests)==1
  result=publish(root);assert len(result['published'])==1,result
  article=json.loads((root/'data/articles.json').read_text())[0]
  assert article['dateISO']==day and article['discovered_via']==[POST.rstrip('/')]
  audit=json.loads((root/'data/editorial-audits'/(article['id']+'.json')).read_text())
  assert audit['discovered_via']==article['discovered_via']
 # Old full sources cannot become today's articles because the index was refreshed.
 with tempfile.TemporaryDirectory() as folder,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(folder);atomic_json(root/'data/articles.json',[])
  later=run(root,now+dt.timedelta(days=1),**kwargs)
  assert later['metrics']['source_failures']==1 and later['articles_ready_to_publish']==0
  assert len(requests)==1
 # An unavailable LinkedIn lane must leave ordinary source publishing functional.
 with tempfile.TemporaryDirectory() as folder,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(folder);atomic_json(root/'data/articles.json',[])
  dated=dict(item,dateISO=day,published_at=day,source_time_precision='date',source_date_unresolved=False)
  def broken(*a):raise TimeoutError('index is unavailable')
  report=run(root,now,**dict(kwargs,discovery=lambda:([dated],[]),linkedin=broken))
  assert report['articles_ready_to_publish']==1 and report['linkedin_discovery']['coverage_status']=='UNAVAILABLE'
 print('PASS: public LinkedIn lead discovery, host filtering, date separation, registered source matching, durable cooldown, search failure isolation, one source read/one writing request, source-date enforcement, publication and discovery audit')

if __name__=='__main__':main()
