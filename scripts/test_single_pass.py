"""Offline source -> one writing call -> actual publisher, with no review calls."""
import copy
import datetime as dt
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from urllib.error import HTTPError
from newsroom_runtime import run
from newsroom_state import atomic_json,Checkpoints
from source_retrieval import read_source, html_extract
from publish_autonomous import publish
from single_pass import POLICY,article_from,bundle_for,eligible
from same_day_policy import clock
from build_public import standalone_story


def main():
 now=dt.datetime.now(dt.timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0);day=clock(now).date().isoformat()
 urls=['https://www.aviva.com/newsroom/news-and-research-overview/news-releases/2026/10/distribution-agreement/',
       'https://www.lloydsbankinggroup.com/media/press-releases/2026/business-lending.html']
 items=[{'url':url,'title':title,'source':source,'category':category,'dateISO':day,'source_time_precision':'date','published_at':day}
        for url,title,source,category in zip(urls,['Aviva expands insurance distribution','Lloyds expands business lending'],['Aviva','Lloyds'],['Insurance','Banking'])]
 docs={}
 for item,name in zip(items,['insurer-release.html','bank-release.html']):
  raw=(Path(__file__).parent/'fixtures'/name).read_text().replace('__DATE__',day).encode()
  with patch('source_retrieval.retrieve_bytes',return_value=(raw,'text/html',item['url'])):docs[item['url']]=read_source(item['url'])
 calls=[]
 def ai(prompt):
  calls.append(prompt)
  assert prompt.startswith('ONE_PASS_NEWSROOM')
  packets=json.loads(prompt.split('SOURCE PACKETS:\n')[1]);assert len(packets)==2
  for packet in packets:assert packet['source_text']==docs[packet['url']].text
  return {'articles':[{'id':f'N{i+1:02}','article':{'headline':item['title'],'standfirst':'New service available.',
    'sections':[{'heading':'What changes','text':f"{item['source']} says the expanded service is available to eligible customers through its existing distribution channels. Applications remain subject to assessment and acceptance criteria. Existing contractual terms determine the insurance cover or finance available."}]}} for i,item in enumerate(items)]}
 with tempfile.TemporaryDirectory() as temp,patch('ai_cost_guard.time.sleep',lambda _:None),patch('newsroom_batches.review_batch',side_effect=AssertionError('Forbidden reviewer call')),patch('publish_autonomous.check',side_effect=AssertionError('Legacy editorial veto called')):
  root=Path(temp);(root/'data').mkdir();atomic_json(root/'data/articles.json',[])
  blocked=dict(items[1],url='https://www.finextra.com/newsarticle/50000/a-distinct-payments-development',source='Finextra',title='Distinct payments development')
  atomic_json(root/'data/live.json',{'items':items+[blocked]})
  def reader(url):
   if url==blocked['url']:raise HTTPError(url,403,'Forbidden',{},None)
   return copy.deepcopy(docs[url])
  kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=reader,ai=ai,search=lambda *a,**k:[])
  report=run(root,now,**kwargs)
  assert report['policy']==POLICY and report['independent_review'] is False
  assert report['api_budget']['requests_this_run']==1 and len(calls)==1
  assert report['articles_ready_to_publish']==2 and report['machine_screened']==0
  assert report['metrics']['source_failures']==1
  # A later run before publication restores complete drafts with zero API or source requests.
  kwargs['reader']=lambda url:(_ for _ in ()).throw(AssertionError('Source was read twice'))
  again=run(root,now+dt.timedelta(minutes=10),**kwargs)
  assert again['api_budget']['requests_this_run']==0 and len(calls)==1
  result=publish(root);assert len(result['published'])==2,result
  assert not publish(root)['published']
  articles=json.loads((root/'data/articles.json').read_text())
  for article in articles:
   assert len(article['blocks'])==1 and len(article['blocks'][0][1].split())<80
   assert article['independent_review'] is False and 'reviewed_by' not in article
   audit=json.loads((root/'data/editorial-audits'/(article['id']+'.json')).read_text())
   assert audit['review_mode']=='single_pass_source_based' and not audit['independent_claim_checks']
   page=standalone_story(article)
   assert 'no separate AI or human editorial review' in page and 'machine-screened' not in page
  # Date/source integrity remains; no fact, heading or word-count review is called.
  state=Checkpoints(root/'generated-drafts').read(urls[0]);bundle=state['bundle']
  assert not eligible(bundle,now)
  assert eligible(bundle,now+dt.timedelta(days=1))
  tampered=copy.deepcopy(bundle);tampered['captured_source_excerpt']+='changed';assert eligible(tampered,now)
  # Empty output is a technical failure, retained without repeated generation.
 with tempfile.TemporaryDirectory() as temp,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(temp);(root/'data').mkdir();atomic_json(root/'data/articles.json',[]);atomic_json(root/'data/live.json',{'items':[items[0]]})
  count=[]
  def empty(prompt):count.append(prompt);return {'articles':[{'id':'N01','article':{'sections':[]}}]}
  kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=lambda url:docs[url],ai=empty,search=lambda *a,**k:[])
  assert run(root,now,**kwargs)['metrics']['unusable_model_responses']==1
  assert run(root,now+dt.timedelta(hours=1),**kwargs)['api_budget']['requests_this_run']==0
  assert len(count)==1
 # Complete brief releases need not reach the old 850-character floor.
 body='Aviva has expanded its insurance distribution agreement for eligible commercial customers. Applications remain subject to existing underwriting criteria. The company says brokers can access the service through its established channels. Existing policy terms continue to apply.'
 text,_=html_extract('<main><article><h1>Aviva expands insurance distribution</h1><p>'+body+'</p></article></main>',urls[0])
 assert 200<=len(text)<850
 print('PASS: two full source-based articles from one writing request, no review/veto, one short section accepted, source/draft recovery, blocked-source isolation, truthful disclosure, duplicate/date controls and no malformed-output request loop')

if __name__=='__main__':main()
