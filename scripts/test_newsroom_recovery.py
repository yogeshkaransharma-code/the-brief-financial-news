"""Real HTML fixtures -> extraction/date checks -> mocked model -> actual publisher.

All articles are synthetic test fixtures written only inside TemporaryDirectory.
This suite does not claim live editorial success and makes no network requests.
"""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError

from newsroom_runtime import run
from newsroom_state import atomic_json, cooling, defer, Checkpoints, restore
from source_retrieval import read_source
from source_dates import verify_announcement
from newsroom_v2 import article_sentences
from publish_autonomous import publish
from newsroom_health import assess
from recover_schedule import decision
from source_fallback import alternatives
from same_day_policy import source_issued_today, clock

FIXTURES=Path(__file__).parent/'fixtures'

def main():
 now=dt.datetime.now(dt.timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0)
 day=clock(now).date().isoformat()
 urls=['https://www.aviva.com/newsroom/news-and-research-overview/news-releases/2026/10/commercial-insurance-distribution-agreement/',
       'https://www.lloydsbankinggroup.com/media/press-releases/2026/business-lending.html']
 names=['Aviva','Lloyds'];titles=['Aviva expands commercial insurance distribution agreement','Lloyds expands lending service for business customers']
 items=[{'url':url,'title':title,'source':name,'category':category,'dateISO':day,'source_time_precision':'date','published_at':day}
        for url,title,name,category in zip(urls,titles,names,['Insurance','Banking'])]
 docs={}
 for item,file in zip(items,['insurer-release.html','bank-release.html']):
  raw=(FIXTURES/file).read_text().replace('__DATE__',day).encode()
  with patch('source_retrieval.retrieve_bytes',return_value=(raw,'text/html',item['url'])):
   doc=read_source(item['url'])
  assert verify_announcement(item,doc,now)['dateISO']==day
  docs[item['url']]=doc
 def draft(i):
  # Faithful fixture paraphrases; separate reviewer results are mocked below.
  name=names[i]
  text=(f'{name} says the expanded service is available to eligible customers through its existing distribution channels. '
        'Applications remain subject to the relevant assessment and acceptance criteria. '
        'The announcement describes a service expansion and does not announce an acquisition. '
        'It does not provide a forecast of future sales or lending volumes. '
        'The contractual terms offered to individual customers determine the cover or finance available. ')
  return {'headline':titles[i],'standfirst':f'{name} says it has expanded a service for eligible customers, with existing assessment criteria and contractual terms continuing to apply.',
          'sections':[{'heading':'The announcement','text':text},{'heading':'Eligibility and terms','text':text}]}
 calls=[];fail_review=[True]
 def ai(prompt):
  calls.append(prompt)
  if 'SOURCE PACKETS:' in prompt:
   return {'articles':[{'id':f'N{i+1:02}','article':draft(i)} for i in range(2)]}
  if fail_review[0]:
   fail_review[0]=False;raise TimeoutError('Temporary model request failure')
  # IDs come from the actual saved article and include EVERY heading/sentence.
  from newsroom_v2 import make_article
  triples=[(items[i],docs[urls[i]]) for i in range(2)]
  rows=[]
  for i,(item,doc) in enumerate(triples):
   article=make_article(draft(i),verify_announcement(item,doc,now),doc)
   rows.append({'id':f'N{i+1:02}','reviews':[{'id':s['id'],'verdict':'SUPPORTED','source_id':'S001' if n%2 else 'S002','issue':''} for n,s in enumerate(article_sentences(article))]})
  return {'articles':rows}
 with tempfile.TemporaryDirectory() as temp,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(temp);(root/'data').mkdir()
  blocked=dict(items[1],url='https://www.finextra.com/newsarticle/50000/a-distinct-payments-development',title='A distinct payments development for central banks',source='Finextra')
  atomic_json(root/'data/live.json',{'items':items+[blocked]});atomic_json(root/'data/articles.json',[])
  def reader(url):
   if url==blocked['url']:raise HTTPError(url,403,'Forbidden',{},None)
   return copy.deepcopy(docs[url])
  kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=reader,ai=ai,search=lambda *a,**k:[])
  first=run(root,now,**kwargs)
  assert first['metrics']['source_failures']==1
  assert first['metrics']['articles_drafted']==2 and first['machine_screened']==0
  assert len(calls)==2,'Writer and failed reviewer reservations must both count'
  assert assess([],first,now,{'published':[]},{'sources_checked':[{}]})['outcome']=='BLOCKED'
  # Next cycle must reuse sources AND drafts, spend only on the review, and
  # preserve the blocked candidate's exact cooldown explanation.
  def no_fetch(url):raise AssertionError('Recovered source was fetched again: '+url)
  kwargs['reader']=no_fetch
  second=run(root,now+dt.timedelta(minutes=20),**kwargs)
  assert second['api_budget']['requests_this_run']==1 and second['machine_screened']==2,second
  assert any(r.get('classification')=='ACCESS_RESTRICTED' and r['result']=='retry deferred' for r in second['items_checked'])
  # A malformed bundle must not prevent valid reviewed stories publishing.
  (root/'generated-drafts/ai-00000000000000000000.json').write_text('{bad JSON')
  result=publish(root)
  assert len(result['published'])==2,result
  assert len(result['held'])==1
  assert {a['category'] for a in json.loads((root/'data/articles.json').read_text())}=={'Insurance','Banking'}
  assert not publish(root)['published'],'Recovery duplicated published articles'
  state=Checkpoints(root/'generated-drafts');record=state.read(urls[0]);assert record['status']=='reviewed'
 # Source failures are bounded and permanent access denials are not hammered.
 ledger={};record=defer(ledger,'https://example.test',HTTPError('x',403,'Forbidden',{},None),now)
 assert record['classification']=='ACCESS_RESTRICTED' and cooling(record,now+dt.timedelta(hours=5))
 assert not cooling(record,now+dt.timedelta(hours=7))
 assert alternatives(items[0],[dict(items[0],url=urls[1])])
 for stamp in ['2026-10-25T00:30:00Z','2026-10-25T01:30:00Z']:
  item={'dateISO':'2026-10-25','source_time_precision':'timestamp','source_published_at':stamp}
  assert source_issued_today(item,dt.datetime(2026,10,25,2,tzinfo=dt.timezone.utc))
 recent={'created_at':now.isoformat(),'status':'completed','conclusion':'failure','event':'schedule'}
 assert decision([recent],now)[0]
 assert not decision([dict(recent,status='in_progress')],now)[0]
 assert not decision([dict(recent,event='workflow_dispatch')]*2,now)[0]
 print('PASS: blocked source isolation, model failure recovery, source/draft reuse, batch reviews, real publisher, malformed-bundle isolation, dedupe, UK DST and schedule recovery')

if __name__=='__main__':main()
