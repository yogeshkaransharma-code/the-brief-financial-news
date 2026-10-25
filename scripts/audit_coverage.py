"""Compare live publisher homepages with the newsroom queue, without model calls.

This is a bounded diagnostic, not a publication feed. Unknown dates and blocked
pages are coverage gaps, never evidence that nothing happened.
"""
import datetime as dt
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from media_sources import canonical_url,relevant
from publication_scope import source_lane
from source_dates import published_date
from same_day_policy import original_date,clock

ROOT=Path(__file__).resolve().parents[1]
TARGETS=[
 ('Insurance Business UK','Insurance','https://www.insurancebusinessmag.com/uk/'),
 ('Reinsurance News','Insurance','https://www.reinsurancene.ws/'),
 ('Commercial Risk','Insurance','https://www.commercialriskonline.com/'),
 ('Insurance Times','Brokers','https://www.insurancetimes.co.uk/'),
 ('Insurance Age','Brokers','https://www.insuranceage.co.uk/'),
 ('Professional Pensions','Pensions','https://www.professionalpensions.com/'),
 ('Investment Week','Wealth','https://www.investmentweek.co.uk/'),
 ('Money Marketing','Wealth','https://www.moneymarketing.co.uk/'),
 ('Finextra','Technology','https://www.finextra.com/'),
 ('BBC Business','Banking','https://www.bbc.co.uk/news/business'),
 ('The Guardian Business','Banking','https://www.theguardian.com/uk/business'),
]
ALLOW={urlsplit(t[2]).hostname.removeprefix('www.') for t in TARGETS}
HEADERS={'User-Agent':'TheBriefCoverageAudit/1.0 (public newsroom coverage comparison)','Accept':'text/html'}
SKIP=re.compile(r'(?i)\b(?:privacy|cookies?|subscribe|subscription|register|sign in|log in|advertis\w*|contact us|about us|terms|media pack|newsletters?|read more|view all|home|advertorial|sponsored)\b')

class Redirects(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  p=urlsplit(newurl)
  if p.scheme!='https' or p.hostname.removeprefix('www.') not in ALLOW:raise ValueError('Audit redirect left selected public publishers')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def retrieve(url):
 opener=urllib.request.build_opener(Redirects())
 with opener.open(urllib.request.Request(url,headers=HEADERS),timeout=15) as response:
  if 'html' not in response.headers.get('Content-Type','').lower():raise ValueError('Not an HTML page')
  raw=response.read(2000001)
  if len(raw)>2000000:raise ValueError('Audit page exceeds bounded capture')
  return raw,response.geturl()

def list_headlines(raw,base,limit=8):
 soup=BeautifulSoup(raw,'html.parser');out=[];seen=set()
 for a in soup.select('a[href]'):
  url=canonical_url(urljoin(base,a['href']));p=urlsplit(url)
  if p.scheme!='https' or (p.hostname or '').removeprefix('www.')!=urlsplit(base).hostname.removeprefix('www.'):continue
  if p.path in {'/','/uk/','/news','/news/','/news/business','/uk/business'}:continue
  heading=a.find(re.compile(r'^h[1-4]$'))
  title=' '.join((heading or a).get_text(' ',strip=True).split())
  if not 25<=len(title)<=230 or SKIP.search(title):continue
  # Inspect actual story links even if production doesn't recognise their route.
  if not source_lane(url) and not (heading or a.find_parent(['h1','h2','h3','h4','article'])):continue
  if url in seen:continue
  seen.add(url);out.append({'title':title,'url':url,'production_route':source_lane(url),'passes_title_relevance':relevant({'title':title})})
  if len(out)>=limit:break
 return out

def main():
 now=dt.datetime.now(dt.timezone.utc);today=clock(now).date()
 feed=json.loads((ROOT/'data/live.json').read_text())
 known={canonical_url(x['url']) for x in feed.get('items',[])}
 evidence=ROOT/'generated-drafts/coverage-audit';evidence.mkdir(parents=True,exist_ok=True)
 def front(target):
  name,sector,url=target
  row={'publisher':name,'sector':sector,'index_url':url}
  try:
   raw,final=retrieve(url);row['index_result']='READ';row['headlines']=list_headlines(raw,final)
   row['index_sha256']=hashlib.sha256(raw).hexdigest()
   (evidence/(hashlib.sha256(url.encode()).hexdigest()[:16]+'.html')).write_bytes(raw)
  except Exception as exc:row.update(index_result='UNAVAILABLE',error=str(exc)[:180],headlines=[])
  return row
 with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(front,TARGETS))
 def inspect(pair):
  row,lead=pair;lead=dict(lead,publisher=row['publisher'],sector=row['sector'],present_in_feed=lead['url'] in known)
  try:
   raw,final=retrieve(lead['url']);dated=published_date(raw)
   lead['document_sha256']=hashlib.sha256(raw).hexdigest();lead['final_url']=final
   (evidence/(hashlib.sha256(lead['url'].encode()).hexdigest()[:16]+'.html')).write_bytes(raw)
   if dated:
    day,value,precision=dated
    uk=original_date({'dateISO':day,'source_published_at':value,'source_time_precision':precision})
    lead.update(original_date_uk=uk.isoformat(),original_date_value=value,precision=precision)
    if uk==today:
     lead['comparison']='TODAY_ALREADY_DISCOVERED' if lead['present_in_feed'] else 'TODAY_MISSING_FROM_FEED'
    elif uk<today:lead['comparison']='EARLIER_DATED_DEVELOPMENT'
    else:lead['comparison']='FUTURE_DATE_HOLD'
   else:lead['comparison']='ORIGINAL_DATE_UNRESOLVED'
  except Exception as exc:lead.update(comparison='ARTICLE_UNAVAILABLE',error=str(exc)[:180])
  return lead
 pairs=[(r,h) for r in rows for h in r['headlines']]
 with ThreadPoolExecutor(max_workers=8) as pool:articles=list(pool.map(inspect,pairs))
 today_rows=[a for a in articles if a.get('original_date_uk')==today.isoformat()]
 report={'checked_at':now.isoformat(),'uk_date':today.isoformat(),'model_requests':0,
  'method':'Independent publisher homepage inventory; read up to eight visible story links per publisher, without production title/date filtering. Original dates checked on article pages.',
  'limits':'A bounded homepage sample does not establish exhaustive coverage. Blocked pages and missing original dates remain unresolved gaps. A metadata date is not an article claim verification.',
  'publisher_checks':rows,'articles':articles,
  'today_found':today_rows,
  'today_missing_from_feed':[a for a in today_rows if not a['present_in_feed']],
  'today_blocked_by_route':[a for a in today_rows if not a['production_route']],
  'today_blocked_by_title_filter':[a for a in today_rows if not a['passes_title_relevance']],
  'summary':{'publishers_read':sum(r['index_result']=='READ' for r in rows),'publishers_unavailable':sum(r['index_result']!='READ' for r in rows),'articles_inspected':len(articles),'today_dated':len(today_rows),'article_dates_unresolved':sum(a['comparison'] in {'ARTICLE_UNAVAILABLE','ORIGINAL_DATE_UNRESOLVED'} for a in articles)}}
 (ROOT/'data/coverage-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('COVERAGE_AUDIT_SUMMARY:',json.dumps(report['summary']))
 for a in articles:print('COVERAGE_AUDIT_ARTICLE:',json.dumps(a,ensure_ascii=False))
if __name__=='__main__':main()
