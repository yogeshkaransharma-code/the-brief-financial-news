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
from single_pass import POLICY,article_from,bundle_for,eligible,preserve_source_name_case,prompt
from same_day_policy import clock
from build_public import standalone_story


from ai_cost_guard import CallBudget

def test_editorial_voice():
    # Selected sources are unchanged: only writing and safe presentation change.
    fake=type('Document',(),{'url':'https://www.insurancebusinessmag.com/uk/news/breaking-news/test.aspx'})()
    insurer={'url':fake.url,'source':'Insurance Business UK','title':'AXIS Capital reports underwriting results',
             'category':'Insurance','dateISO':'2026-10-29'}
    written={'headline':'AXIS Capital reports underwriting results',
             'standfirst':'axis capital increased premiums, while acquisition costs rose.',
             'reader_takeaway':'Higher acquisition costs affected the reported underwriting result.',
             'sections':[{'heading':'Premiums and costs',
                          'text':'axis capital reported higher insurance premiums. It also disclosed higher acquisition costs.'}]}
    article=article_from(written,insurer,fake)
    assert article['short']=='AXIS Capital increased premiums, while acquisition costs rose.',article['short']
    assert article['blocks'][0][1].startswith('AXIS Capital'),article['blocks']
    assert 'According to' not in article['short'] and article['source']=='Insurance Business UK'
    assert article['reader_takeaway']==written['reader_takeaway']
    assert preserve_source_name_case('allianz UK launched cover.', 'Allianz UK adds cover')=='Allianz UK launched cover.'
    assert preserve_source_name_case('axis capital did not comment.', 'UK market responds to results')=='axis capital did not comment.'
    one_prompt=prompt([(insurer,type('Captured',(),{'url':fake.url,'text':'A complete captured source.'})())])
    for phrase in ['Make every paragraph earn its place','Do not mechanically begin every standfirst',
                   'Keep company names, acronyms','Do not force a UK market impact',
                   'The reader must leave knowing']:
        assert phrase.casefold() in one_prompt.casefold(),phrase
    assert 'SOURCE PACKETS:' in one_prompt


@patch('newsroom_runtime.CallBudget',side_effect=lambda ledger,now,**kwargs:CallBudget(ledger,now,now_fn=lambda:now,**kwargs))
def main(_budget):
 test_editorial_voice()
 now=dt.datetime.now(dt.timezone.utc).replace(hour=12,minute=0,second=0,microsecond=0);day=clock(now).date().isoformat()
 urls=['https://www.aviva.com/newsroom/news-and-research-overview/news-releases/2026/10/distribution-agreement/',
       'https://www.lloydsbankinggroup.com/media/press-releases/2026/business-lending.html']
 items=[{'url':url,'title':title,'source':source,'category':category,'dateISO':day,'source_time_precision':'date','published_at':day}
        for url,title,source,category in zip(urls,['Aviva expands UK insurance distribution','Lloyds expands UK business lending'],['Aviva','Lloyds'],['Insurance','Banking'])]
 docs={}
 for item,name in zip(items,['insurer-release.html','bank-release.html']):
  raw=(Path(__file__).parent/'fixtures'/name).read_text().replace('__DATE__',day).encode()
  with patch('source_retrieval.retrieve_bytes',return_value=(raw,'text/html',item['url'])):docs[item['url']]=read_source(item['url'])
 calls=[]
 def ai(prompt):
  calls.append(prompt)
  assert prompt.startswith('ONE_PASS_NEWSROOM')
  # These are safeguards against prompt drift, not proof of the model's factual accuracy.
  for required in (
   'source-grounded UK financial news', 'knowledgeable, considerate British reporter',
   'commercially aware', 'Human means clarity and judgement',
   'no clickbait', 'never invent an impact', 'ONLY where the source',
   'proposals from final rules', 'do not represent a single source',
   'Do not invent unsupported assertions', 'reader_takeaway',
  ):
   assert required.casefold() in prompt.casefold(),required
  packets=json.loads(prompt.split('SOURCE PACKETS:\n')[1]);assert len(packets)==2
  for packet in packets:assert packet['source_text']==docs[packet['url']].text
  return {'articles':[{'id':f'N{i+1:02}','article':{'headline':item['title'],'standfirst':'New service available.',
    'reader_takeaway':'Eligible customers can access the service through existing distribution channels.',
    'sections':[{'heading':'What changes','text':f"{item['source']} says the expanded UK service is available to eligible customers through existing distribution channels in the United Kingdom. Applications remain subject to assessment and acceptance criteria. Existing contractual terms determine the UK insurance cover or finance available."}]}} for i,item in enumerate(items)]}
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
   assert article['reader_takeaway'].startswith('Eligible customers can access'), 'Grounded reader takeaway lost'
   audit=json.loads((root/'data/editorial-audits'/(article['id']+'.json')).read_text())
   assert audit['review_mode']=='single_pass_source_based' and not audit['independent_claim_checks']
   page=standalone_story(article)
   assert 'No separate editorial fact-check has been carried out.' in page
   assert 'machine-screened' not in page and 'Written automatically' not in page
   assert '<h3>Why it matters</h3>' in page, 'Grounded reader context missing from article'
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
 # Provider 429 stops this cycle and subsequent cycles during its cooldown.
 # The removed local 30-call limit must not masquerade as provider exhaustion.
 from ai_newsroom import GeminiAPIError
 from ai_cost_guard import PACIFIC
 with tempfile.TemporaryDirectory() as temp,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(temp);(root/'data').mkdir();atomic_json(root/'data/articles.json',[]);atomic_json(root/'data/live.json',{'items':items})
  atomic_json(root/'data/newsroom-attempts.json',{'api_budget':{'date':now.astimezone(PACIFIC).date().isoformat(),'requests':30,'limit':30}})
  attempts=[]
  def limited(prompt):
   attempts.append(prompt);raise GeminiAPIError(429,'Rate limit this minute',retry_seconds=60)
  kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=lambda url:docs[url],ai=limited,search=lambda *a,**k:[])
  first=run(root,now,**kwargs)
  assert len(attempts)==1 and first['api_budget']['requests_today_including_this_run']==31
  assert first['api_budget']['daily_limit'] is None and first['active_quota_pause_until']
  second=run(root,now+dt.timedelta(minutes=20),**kwargs)
  assert len(attempts)==1 and second['api_budget']['requests_this_run']==0
  atomic_json(root/'generated-drafts/publication-report.json',{'published':[],'held':[]})
  import newsroom_health,io,contextlib
  with patch('newsroom_health.ROOT',root),contextlib.redirect_stdout(io.StringIO()):
   newsroom_health.main()
  status=json.loads((root/'data/status.json').read_text())
  assert status['ai_budget']['daily_limit'] is None and status['ai_budget']['remaining_today'] is None
  assert status['ai_budget']['requests_today_including_this_run']==31
 # Scope decisions retain the full source, and a newly eligible cached
 # source resumes without another download or a second model review.
 with tempfile.TemporaryDirectory() as temp,patch('ai_cost_guard.time.sleep',lambda _:None):
  root=Path(temp);(root/'data').mkdir();atomic_json(root/'data/articles.json',[])
  atomic_json(root/'data/live.json',{'items':items})
  reads=[]
  def cached_reader(url):reads.append(url);return copy.deepcopy(docs[url])
  kwargs=dict(discovery=lambda:([],[]),trace=lambda *a,**k:([],[]),reader=cached_reader,ai=ai,search=lambda *a,**k:[])
  with patch('uk_market_scope.uk_market_reason',return_value=''):
   held=run(root,now,**kwargs)
  assert held['metrics']['outside_uk_market']==2 and held['api_budget']['requests_this_run']==0
  resumed=run(root,now+dt.timedelta(minutes=1),**kwargs)
  assert len(reads)==2 and resumed['metrics']['source_checkpoints_reused']==2
  assert resumed['articles_ready_to_publish']==2 and resumed['api_budget']['requests_this_run']==1
 # Complete brief releases need not reach the old 850-character floor.
 body='Aviva has expanded its insurance distribution agreement for eligible commercial customers. Applications remain subject to existing underwriting criteria. The company says brokers can access the service through its established channels. Existing policy terms continue to apply.'
 text,_=html_extract('<main><article><h1>Aviva expands insurance distribution</h1><p>'+body+'</p></article></main>',urls[0])
 assert 200<=len(text)<850
 print('PASS: two full source-based articles from one writing request, no review/veto, one short section accepted, source/draft recovery, blocked-source isolation, truthful disclosure, duplicate/date controls and no malformed-output request loop')

if __name__=='__main__':main()
